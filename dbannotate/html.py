#
# Copyright(C) 2015 Romain Bignon, Laurent Defert
#
# db_annotate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# db_annotate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import os
import re

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers.sql import MySqlLexer, PlPgsqlLexer, PostgresConsoleLexer, PostgresLexer, SqlLexer, SqliteConsoleLexer

from .db_size import humanize
from .output_file import OutputFile, OUTPUT_DIR

HTML_BODY = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
%s
<title>%s</title>
</head>
<body>
"""
HTML_FOOTER = """
</body>
</html>
"""


class HTMLFile(OutputFile):
    CSS = []
    BACK_BUTTON = True

    def render(self, *args, **kw):
        css = ['<link rel="stylesheet" type="text/css" href="%s">' % css for css in self.CSS]
        css = '\n'.join(css)
        if self.BACK_BUTTON:
            self.write('<a href="index.html">Back...</a><br/>')
        self.write(HTML_BODY % (css, self.filename))
        self._render(*args, **kw)
        self.write(HTML_FOOTER)

class DBSizeFile(HTMLFile):
    def __init__(self, filename, dbsize_no):
        HTMLFile.__init__(self, '%s%i.html' % (filename, dbsize_no))
        self.dbsize_no = dbsize_no

    def _render(self, objects):
        for obj in objects:
            self.write('''<figure style="display: inline"><embed type="image/svg+xml" src="%s" width="40%%" height="40%%"/>
            </figure>''' % (obj['url']))
        self.write(HTML_FOOTER)


class TableFile(HTMLFile):
    @staticmethod
    def get_table_html(img):
        map_file = img + '.map'
        img = os.path.basename(img)
        html = '<img src="%s" usemap="#mainmap" /><map id="mainmap" name="mainmap">' % img
        map_file = open(map_file, 'r')
        html += map_file.read()
        map_file.close()
        html += '</map>'
        return html

    def _render(self, table, errors, sizes, keys, indexes, columns, triggers):
        self.write('''<h1>Table %s</h1>
                    <ul>
                        <li>Size: %s</li>
                        <li>Size without indexes: %s</li>
                        <li>Rows count: %i</li>
                        <li>Keys: %s</li>
                        <li>Columns count: %i</li>''' % (table, sizes[1], sizes[0],
                                sizes[4], ', '.join(keys), len(columns)))

        _triggers = []
        for trigger in triggers:
            tg_name, tg_event, tg_action, tg_when = trigger
            tg_code = tg_func = ''
            m = re.match('^EXECUTE PROCEDURE ([^ ]*)\(\)$', tg_action)
            if m is not None:
                tg_code = 'EXECUTE PROCEDURE'
                tg_func = m.group(1)
            _triggers.append('<li>%s: %s %s %s <a href="fn_%s.html">%s()</a></li>' %
                   (tg_name, tg_when.title(), tg_event.title(),
                   tg_code, tg_func, tg_func))
        self.write('<li>Triggers:<ul>%s</ul></li>' % '\n'.join(_triggers))
        self.write('</ul>')

        self.write(TableFile.get_table_html(self.filename.replace('.html', '.png')))

class IndexFile(HTMLFile):
    BACK_BUTTON = False
    def _render(self, objects, db_size, db, functions):
        for obj in objects:
            for _obj in obj:
                _obj['url'] = os.path.basename(_obj['filename'])

        self.write('''<ul>
                        <li>Database: %s</li>
                        <li>Date: %s</li>
                        <li>Tables count: %s</li>
                        <li>Total size: %s</li>
                    </ul>''' % (repr(db.engine.url),
                                datetime.now().strftime('%x'),
                                len(db.get_tables()),
                                humanize(sum(db_size.total_size.values()), 'b')))

        for i, obj in enumerate(objects):
            self.write('''
                <figure style="display: inline">
                    <a href="graph_%i.html"><embed type="image/svg+xml" src="%s" width="40%%" height="40%%"/>More...</a>
                </figure>''' % (i, obj[0]['url']))
            page = DBSizeFile('graph_', i)
            page.render(obj)

        # Sort tables by total size of the first type of graph
        # TODO: Refactor the sorting and humanize call with db_size module
        tables = []
        for table in sorted(db_size.total_size, key=db_size.total_size.get, reverse=True):
            _table = [table]
            for graph in db_size.GRAPHS.keys():
                val = getattr(db_size, graph + '_size')
                _table.append(humanize(val[table], db_size.GRAPHS[graph]['counter_type']))
            tables.append(_table)

        self.write('<table><tr>')
        self.write('<th>Table name</th>')
        for graph_conf in db_size.GRAPHS.values():
            self.write('<th>%s</th>' % graph_conf['title'])
        self.write('</tr>')

        for table in tables:
            self.write('<tr>')
            for no, _table in enumerate(table):
                if no == 0:
                    _table = '<a href="%s.html" >%s</a>' % (_table, _table)
                self.write('<td>%s</td>' % _table)
            self.write('</tr>')
        self.write('</table>')
        self.write(TableFile.get_table_html(os.path.join(OUTPUT_DIR, 'map.png')))
        if len(functions):
            self.write('<h2>Functions</h2>')
            self.write('<table><tr><th>Name</th><th>Lines count</th></tr>')
            for function in functions:
                self.write('<tr><td><a href="fn_%s.html">%s</a></td>' % (function[0], function[0]))
                self.write('<td>%i</td></tr>' % function[1])
            self.write('</table>')


FORMATTER = HtmlFormatter()
class HilightCSSFile(OutputFile):
    def __init__(self):
        super(HilightCSSFile, self).__init__('highlight.css')
    def render(self):
        self.write(FORMATTER.get_style_defs('.highlight'))

class FunctionFile(HTMLFile):
    CSS = ['highlight.css']
    LEXERS = {
        'plpgsql': PlPgsqlLexer(),
    }

    def _get_lexer(self, language):
        if language not in self.LEXERS:
            raise NotImplemented('Unknown function language "%s"' % language)
        return self.LEXERS[language]

    def _render(self, function, language, code):
        lexer = self._get_lexer(language)
        highlighted = highlight(code, lexer, FORMATTER)
        self.write('<h1>Function %s</h1>' % function)
        self.write('%s language' % language)
        self.write(highlighted)

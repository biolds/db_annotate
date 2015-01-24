from datetime import datetime
import os

from .db_size import humanize
from .output_file import OutputFile, OUTPUT_DIR

HTML_BODY = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>%s</title>
</head>
<body>
"""
HTML_FOOTER = """
</body>
</html>
"""


class DBSizeFile(OutputFile):
    def __init__(self, filename, dbsize_no):
        OutputFile.__init__(self, '%s%i.html' % (filename, dbsize_no))
        self.dbsize_no = dbsize_no

    def render(self, objects):
        self.write(HTML_BODY % self.filename)
        for obj in objects:
            self.write('''<figure style="display: inline"><embed type="image/svg+xml" src="%s" width="40%%" height="40%%"/>
            </figure>''' % (obj['url']))
        self.write(HTML_FOOTER)


class TableFile(OutputFile):
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

    def render(self, table, errors, sizes, keys, indexes, columns):
        self.write(HTML_BODY % self.filename)
        self.write('''<a href="index.html">Back...</a><br/>
                    <h1>Table %s</h1>
                    <ul>
                        <li>Size: %s</li>
                        <li>Size without indexes: %s</li>
                        <li>Rows count: %i</li>
                        <li>Keys: %s</li>
                        <li>Columns count: %i</li>
                    </ul>''' % (table, sizes[1], sizes[0], sizes[4], ', '.join(keys),
                                len(columns)))
        self.write(TableFile.get_table_html(self.filename.replace('.html', '.png')))
        self.write(HTML_FOOTER)

class IndexFile(OutputFile):
    def render(self, objects, db_size, db):
        for obj in objects:
            for _obj in obj:
                _obj['url'] = os.path.basename(_obj['filename'])

        self.write(HTML_BODY % self.filename)
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
        self.write(HTML_FOOTER)

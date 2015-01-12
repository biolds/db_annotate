import os

from db_size import humanize
from output_file import OutputFile

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


class HtmlFile(OutputFile):
    def render(self, objects, db_size):
        for obj in objects:
            for _obj in obj:
                _obj['url'] = os.path.basename(_obj['filename'])

        self.write(HTML_BODY % self.filename)

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
            for _table in table:
                self.write('<td>%s</td>' % _table)
            self.write('</tr>')
        self.write('</table>')

        self.write(HTML_FOOTER)

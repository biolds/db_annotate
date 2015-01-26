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

import cgi

from .output_file import OutputFile

GV_HEADER = """
digraph G {
    overlap = scale;
    splines = true;
    node [shape=plaintext];

"""
GV_FOOTER = """
}
"""
GV_SEPARATOR = '__42deadbeef__'


class GV(OutputFile):
    def __init__(self, filename, minimap=False):
        super(GV, self).__init__(filename)
        self.tables = []
        self.minimap = minimap

    def _escape(self, s):
        # Make the string one line
        s = str(s or '\n').splitlines()[0]
        return cgi.escape(s)

    def add_header(self):
        self.write(GV_HEADER)

    def add_table(self, name, errors, sizes, keys, indexes, columns, triggers, highlight=False):
        if name in self.tables:
            return
        self.tables.append(name)
        sizes = [sizes[i] for i in (1, 0, 4)]

        color = 'white'
        if len(errors):
            color = 'firebrick1'

        if self.minimap:
            fontsize = 'fontsize="7"'
        elif highlight:
            fontsize = 'fontsize="16"'
        else:
            fontsize = 'fontsize="10"'

        url = ''
        if not highlight:
            url = 'URL="%s.html"' % name

        table = """{name} [ {url} {fontsize} label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
        <TR>
            <TD PORT="{name}" BGCOLOR="{color}"><B>{name} ({sizes})</B></TD>
        """
        if not self.minimap:
            table += """
                <TD BGCOLOR="{color}">I</TD>
                <TD BGCOLOR="{color}">NN</TD>
                <TD BGCOLOR="{color}">U</TD>
                <TD BGCOLOR="{color}"></TD>
                <TD ALIGN="left" BGCOLOR="{color}">{errors}</TD>"""
        table += '</TR>'
        errors = [self._escape(err) for err in errors]
        table = table.format(name=name,
                        color=color,
                        sizes='/'.join([str(n) for n in sizes]),
                        errors=', '.join(errors),
                        fontsize=fontsize,
                        url=url)
        self.write(table)

        if self.minimap:
            self.write("</TABLE>>];")
            return

        for col in columns:
            col_id = "%s%s%s" % (name, GV_SEPARATOR, col.name)
            color = 'limegreen' if col.name in keys else 'gray'
            has_index = '*' if col.name in indexes else ''
            not_nullable = '*' if not col.nullable else ''
            unique = '*' if col.unique else ''

            # Data type
            col_type = str(col.type).lower()
            if col.server_default is not None:
                default = str(col.server_default.arg)
                if default.startswith('nextval'):
                    default = 'nextval'
                col_type += '/def:' + default

            # Escape errors (as they can contain exeception passed when reading sqlachemy's lazy values)
            col_errors = [self._escape(err) for err in col.errors]

            column = """<TR>
                <TD ALIGN="left" PORT="{col_id}" BGCOLOR="{color}">{column}</TD>
                <TD BGCOLOR="{color}">{has_index}</TD>
                <TD BGCOLOR="{color}">{not_nullable}</TD>
                <TD BGCOLOR="{color}">{unique}</TD>
                <TD ALIGN="right" BGCOLOR="{color}">{col_type}</TD>
                <TD ALIGN="left" BGCOLOR="{error_color}" PORT="{col_id}1" >{error}</TD>
            </TR>""".format(**{
                'col_id': col_id,
                'col_type': col_type,
                'color': color,
                'column': col.name,
                'has_index': has_index,
                'unique': unique,
                'not_nullable': not_nullable,
                'error': ', '.join(col_errors),
                'error_color': 'firebrick1' if len(col_errors) else color,
            })
            self.write(column)
        self.write("</TABLE>>];")

    def add_constraint(self, src, dst):
        if self.minimap:
            self.write("%s -> %s;" % (src[0], dst[0]))
        else:
            self.write("%s:%s1:e -> %s:%s:w;" % (src[0], GV_SEPARATOR.join(src),
                                                 dst[0], GV_SEPARATOR.join(dst)))

    def add_missing_constraint(self, table, column, other_table, error):
        if self.minimap:
            self.write('%s -> %s [fontcolor="red", color="red"];' % (table, other_table))
        else:
            self.write('%s:%s1:e -> %s [label="%s" fontcolor="red", color="red"];' % (table, GV_SEPARATOR.join([table, column]),
                                    other_table, error))

    def add_inherited(self, src, dst):
        # :s for the South side of the table
        if self.minimap:
            self.write('%s -> %s [fontcolor="limegreen" color="limegreen"];' % (dst, src))
        else:
            self.write('%s -> %s:n [label="inherits" fontcolor="limegreen" color="limegreen"];' % (dst, src))

    def add_duplicate(self, src, dst, duplicate_type):
        if self.minimap:
            self.write('%s -> %s [fontcolor="red" color="red"];' % (src, dst))
        else:
            self.write('%s -> %s:n [label="%s" fontcolor="red" color="red"];' % (src, dst, ', '.join(duplicate_type)))

    def add_footer(self):
        self.write(GV_FOOTER)

    def add_namespace(self, namespace, tables):
        self.write('%s [label="%s", shape="square"];' % (namespace, namespace.title()))
        for table in tables:
            self.write('%s -> %s [style="dashed"];' % (namespace, table))

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

class GV:
    def __init__(self):
        self.tables = {}
        print(GV_HEADER)

    def add_table(self, name, sizes, keys, indexes, columns):
        # Display the table in red when there is no entries
        color = 'white'
        if sizes[2] == '0':
            color = 'firebrick1'

        table = """%s [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
        <TR><TD PORT="%s" BGCOLOR="%s">%s (%s)</TD></TR>""" % (name, name, color, name, '/'.join(sizes))
        print(table)

        for column in columns:
            column, data_type, char_max, nullable, default, unique = column
            col_id = ''

            col_id += "%s%s%s" % (name, GV_SEPARATOR, column)
            color = 'gray'
            if column in keys:
                color = 'limegreen'
            if column in indexes:
                column = '* %s' % column
            col_type = data_type
            if data_type.startswith('character '):
                col_type += '(%s)' % char_max
            if default:
                if default.startswith('nextval'):
                    default = 'nextval'
                col_type += ' ' + default
            if nullable == 'NO':
                col_type += ' non-null'
            if unique:
                col_type += ' unique'
            column = """<TR>
                <TD ALIGN="left" PORT="%s" BGCOLOR="%s">%s</TD>
                <TD ALIGN="right" PORT="%s" BGCOLOR="%s">%s</TD>
            </TR>""" % (col_id, color, column, col_id + '1', color, col_type)
            print(column)
        print("</TABLE>>];")

    def add_constraint(self, src, dst):
        print("%s:%s1:e -> %s:%s:w;" % (src[0], GV_SEPARATOR.join(src),
                                    dst[0], GV_SEPARATOR.join(dst)))

    def add_inherited(self, src, dst):
        print("%s -> %s [color=red];" % (src, dst))

    def add_footer(self):
        print(GV_FOOTER)

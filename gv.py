GV_HEADER = """
digraph G {
    overlap = scale;
    splines = true;
    node [shape=plaintext];

    subgraph {
    rank = sink;
    label = "Legend";
    graph[style=solid];
    bgcolor=gray;

    // Legend
    legend [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
            <TR>
                <TD BGCOLOR="white">Legend (size without indexes/total size/lines count)</TD>
                <TD >I'</TD>
                <TD >NN'</TD>
                <TD >U'</TD>
            </TR>
            <TR>
                <TD ALIGN="left" BGCOLOR="gray">column</TD>
                <TD BGCOLOR="gray"></TD>
                <TD BGCOLOR="gray"></TD>
                <TD BGCOLOR="gray"></TD>
                <TD ALIGN="right" BGCOLOR="gray">data type</TD>
            </TR>
            <TR>
                <TD ALIGN="left" BGCOLOR="limegreen">column_with_a_foreign_key</TD>
                <TD BGCOLOR="limegreen"></TD>
                <TD BGCOLOR="limegreen"></TD>
                <TD BGCOLOR="limegreen"></TD>
                <TD ALIGN="right" PORT="legend_foreign_key" BGCOLOR="limegreen">data type</TD>
            </TR>
            <TR>
                <TD ALIGN="left" BGCOLOR="gray">I', NN', U': Index, Non null, Unique</TD>
                <TD BGCOLOR="gray"></TD>
                <TD BGCOLOR="gray"></TD>
                <TD BGCOLOR="gray"></TD>
                <TD ALIGN="right" BGCOLOR="gray"></TD>
            </TR>
        </TABLE>>];
    legend2 [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
            <TR>
                <TD BGCOLOR="white">Example table</TD>
                <TD >I</TD>
                <TD >NN</TD>
                <TD >U</TD>
            </TR>
            <TR>
                <TD ALIGN="left" PORT="legend_primary_key" BGCOLOR="limegreen">column_with_a_primary_key</TD>
                <TD BGCOLOR="limegreen"></TD>
                <TD BGCOLOR="limegreen"></TD>
                <TD BGCOLOR="limegreen"></TD>
                <TD ALIGN="right" BGCOLOR="limegreen">data type</TD>
            </TR>
        </TABLE>>];

        // Link the two table
        // :e / :w to tell to link from the East border of the cell to the West border
        // of the other cell
        legend:legend_foreign_key:e -> legend2:legend_primary_key:w;
        }
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
        <TR>
            <TD PORT="%s" BGCOLOR="%s">%s (%s)</TD>
            <TD >I</TD>
            <TD >NN</TD>
            <TD >U</TD>
        </TR>""" % (name, name, color, name, '/'.join(sizes))
        print(table)

        for column in columns:
            column, data_type, char_max, nullable, default, unique = column
            col_id = ''

            col_id += "%s%s%s" % (name, GV_SEPARATOR, column)
            color = 'gray'

            has_index = ''
            if column in keys:
                color = 'limegreen'
            if column in indexes:
                has_index = '*'
            if nullable == 'NO':
                nullable = '*'
            else:
                nullable = ''
            if unique:
                unique = '*'
            else:
                unique = ''

            # Data type
            col_type = data_type
            if data_type.startswith('character '):
                col_type += '(%s)' % char_max
            if default:
                if default.startswith('nextval'):
                    default = 'nextval'
                col_type += ' ' + default

            column = """<TR>
                <TD ALIGN="left" PORT="{col_id}" BGCOLOR="{color}">{column}</TD>
                <TD BGCOLOR="{color}">{has_index}</TD>
                <TD BGCOLOR="{color}">{nullable}</TD>
                <TD BGCOLOR="{color}">{unique}</TD>
                <TD ALIGN="right" PORT="{col_id}1" BGCOLOR="{color}">{col_type}</TD>
            </TR>""".format(**{
                'col_id': col_id,
                'col_type': col_type,
                'color': color,
                'column': column,
                'has_index': has_index,
                'unique': unique,
                'nullable': nullable,
            })
            print(column)
        print("</TABLE>>];")

    def add_constraint(self, src, dst):
        print("%s:%s1:e -> %s:%s:w;" % (src[0], GV_SEPARATOR.join(src),
                                    dst[0], GV_SEPARATOR.join(dst)))

    def add_inherited(self, src, dst):
        # :s for the South side of the table
        print('%s:s -> %s:%s [label="inherits" fontcolor=red color=red];' % (dst, src, src))

    def add_footer(self):
        print(GV_FOOTER)

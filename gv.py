GV_HEADER = """
digraph G {
    overlap = scale;
    splines = true;
    node [shape=plaintext];

    subgraph {
    rank = sink;
    label = "Legend table";
    graph[style=solid];
    bgcolor=gray;

    // Legend
    legend [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
            <TR>
                <TD BGCOLOR="white"><B>Legend (size without indexes/total size/lines count)</B></TD>
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
                <TD BGCOLOR="firebrick1"><B>Example table with errors</B></TD>
                <TD BGCOLOR="firebrick1">I</TD>
                <TD BGCOLOR="firebrick1">NN</TD>
                <TD BGCOLOR="firebrick1">U</TD>
                <TD BGCOLOR="firebrick1"></TD>
                <TD BGCOLOR="firebrick1">table errors</TD>
            </TR>
            <TR>
                <TD ALIGN="left" PORT="legend_primary_key" BGCOLOR="firebrick1">column_with_a_primary_key</TD>
                <TD BGCOLOR="firebrick1"></TD>
                <TD BGCOLOR="firebrick1"></TD>
                <TD BGCOLOR="firebrick1"></TD>
                <TD ALIGN="right" BGCOLOR="firebrick1">data type</TD>
                <TD ALIGN="left" BGCOLOR="firebrick1">column errors</TD>
            </TR>
        </TABLE>>];

        // Link the two table
        // :e / :w to tell to link from the East border of the cell to the West border
        // of the other cell
        legend:legend_foreign_key:e -> legend2:legend_primary_key:w;
        image -> legend [style=invis];
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

    def add_table(self, name, errors, sizes, keys, indexes, columns):
        sizes = sizes[:2] + [sizes[4]]
        # Display the table in red when there is no entries
        color = 'white'
        if len(errors):
            color = 'firebrick1'

        table = """{name} [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
        <TR>
            <TD PORT="{name}" BGCOLOR="{color}"><B>{name} ({sizes})</B></TD>
            <TD BGCOLOR="{color}">I</TD>
            <TD BGCOLOR="{color}">NN</TD>
            <TD BGCOLOR="{color}">U</TD>
            <TD BGCOLOR="{color}"></TD>
            <TD ALIGN="left" BGCOLOR="{color}">{errors}</TD>
        </TR>""".format(name=name,
                        color=color,
                        sizes='/'.join([str(n) for n in sizes]),
                        errors=', '.join(errors))
        print(table)

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
                'error': ', '.join(col.errors),
                'error_color': 'firebrick1' if len(col.errors) else color,
            })
            print(column)
        print("</TABLE>>];")

    def add_constraint(self, src, dst):
        print("%s:%s1:e -> %s:%s:w;" % (src[0], GV_SEPARATOR.join(src),
                                    dst[0], GV_SEPARATOR.join(dst)))

    def add_missing_constraint(self, table, column, other_table, error):
        print('%s:%s1:e -> %s [label="%s" fontcolor="red", color="red"];' % (table, GV_SEPARATOR.join([table, column]),
                                    other_table, error))

    def add_inherited(self, src, dst):
        # :s for the South side of the table
        print('%s -> %s:%s [label="inherits" fontcolor=limegreen color=limegreen];' % (dst, src, src))

    def add_duplicate(self, src, dst, duplicate_type):
        print('%s -> %s:%s [label="%s" fontcolor=red color=red];' % (src, dst, dst, ', '.join(duplicate_type)))

    def add_footer(self):
        print(GV_FOOTER)

    def add_img(self, filename):
        print('image [label="" image="%s"];' % filename)

    def add_namespace(self, namespace, tables):
        print('%s [label="%s"];' % (namespace, namespace.title()))
        for table in tables:
            print('%s -> %s:%s [style="dashed"];' % (namespace, table, table))

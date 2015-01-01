#!/usr/bin/python3
from gv import GV
from pg import PG

if __name__ == '__main__':
    pg = PG()
    gv = GV()

    # Tables
    for table in pg.get_tables():
        columns = pg.get_columns(table)
        sizes = pg.get_table_size(table)
        keys = pg.get_table_keys(table)
        gv.add_table(table, sizes, keys, columns)

    # Constraints
    for table in pg.get_tables():
        for src, dst in pg.get_constraints(table):
            gv.add_constraint(src, dst)

    # Inheritance link
    for src, dst in pg.get_inherited_tables():
        gv.add_inherited(src, dst)

    gv.add_footer()

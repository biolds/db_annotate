#!/usr/bin/python3
from db_size import DBSize
from gv import GV
from pg import PG

if __name__ == '__main__':
    pg = PG()
    gv = GV()
    db_size = DBSize()

    # DB size pies
    for table in pg.get_tables():
        sizes = pg.get_table_size(table)
        db_size.add_table(table, sizes)
    db_size_img = db_size.render()
    gv.add_img(db_size_img)

    # Tables
    for table in pg.get_tables():
        columns = pg.get_columns(table)
        sizes = pg.get_table_size(table)
        keys = pg.get_table_keys(table)
        indexes = pg.get_table_index(table)
        errors = pg.get_table_errors(table)
        gv.add_table(table, errors, sizes, keys, indexes, columns)

    # Constraints
    for table in pg.get_tables():
        for src, dst in pg.get_constraints(table):
            gv.add_constraint(src, dst)

    # Missing constraints
    for table in pg.get_tables():
        for constraint in pg.get_missing_constraints(table):
            gv.add_missing_constraint(*constraint)

    # Inheritance link
    for src, dst in pg.get_inherited_tables():
        gv.add_inherited(src, dst)

    for tables, duplicate_type in pg.get_duplicated_tables().items():
        src, dst = tables.split('/')
        gv.add_duplicate(src, dst, duplicate_type)
    gv.add_footer()

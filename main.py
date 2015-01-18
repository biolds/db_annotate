#!/usr/bin/python3

import os
import sys
import subprocess

from db import DB
from db_size import DBSize
from dot import DotFile
from gv import GV
from html import IndexFile, TableFile
from output_file import OutputFile


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            raise Exception('Invalid URI')

        db = DB(sys.argv[1])
    except Exception as e:
        print(e, file=sys.stderr)
        print('Syntax: %s DATABASE_URI' % sys.argv[0], file=sys.stderr)
        print('For example mysql://username:password@hostname/database', file=sys.stderr)
        print('            postgresql://username:password@hostname/database', file=sys.stderr)
        sys.exit(1)

    OutputFile.create_outputdir()

    gv_map = GV('map.gv', minimap=True)
    gv_tables = {}
    tables = {}

    db_size = DBSize()

    # DB size pies
    for table in db.get_tables():
        sizes = db.get_table_size(table)
        db_size.add_table(table, sizes)
        gv_tables[table] = GV(table + '.gv')
        gv_tables[table].add_header()

    imgs = db_size.render()

    # Tables
    if not gv_map.exists():
        gv_map.add_header()

        for table in db.get_tables():
            columns = db.get_columns(table)
            sizes = db.get_table_size(table)
            keys = db.get_table_keys(table)
            indexes = db.get_table_index(table)
            errors = db.get_table_errors(table)
            gv_map.add_table(table, errors, sizes, keys, indexes, columns)
            gv_tables[table].add_table(table, errors, sizes, keys, indexes, columns, True)
            tables[table] = (table, errors, sizes, keys, indexes, columns)

        # Constraints
        for table in db.get_tables():
            for src, dst in db.get_foreign_keys(table):
                gv_tables[table].add_table(*tables[dst[0]])
                gv_tables[table].add_constraint(src, dst)
                gv_tables[dst[0]].add_table(*tables[table])
                gv_tables[dst[0]].add_constraint(src, dst)
                gv_map.add_constraint(src, dst)

        # Missing constraints
        for table in db.get_tables():
            for constraint in db.get_missing_constraints(table):
                gv_tables[table].add_table(*tables[constraint[2]])
                gv_tables[table].add_missing_constraint(*constraint)
                gv_tables[constraint[2]].add_table(*tables[table])
                gv_tables[constraint[2]].add_missing_constraint(*constraint)
                gv_map.add_missing_constraint(*constraint)

        # Inheritance link
        for src, dst in db.get_inherited_tables():
            gv_map.add_inherited(src, dst)
            gv_tables[src].add_table(*tables[dst])
            gv_tables[src].add_inherited(src, dst)
            gv_tables[dst].add_table(*tables[src])
            gv_tables[dst].add_inherited(src, dst)

        for _tables, duplicate_type in db.get_duplicated_tables().items():
            src, dst = _tables.split('/')
            gv_map.add_duplicate(src, dst, duplicate_type)
            gv_tables[src].add_table(*tables[dst])
            gv_tables[src].add_duplicate(src, dst, duplicate_type)
            gv_tables[dst].add_table(*tables[src])
            gv_tables[dst].add_duplicate(src, dst, duplicate_type)

        namespaces = db.get_namespaces().items()
        if len(namespaces) != 1:
            # Show namespaces only when there are more than one
            for namespace, tables in namespaces:
                gv_map.add_namespace(namespace, tables)

        for gv in [gv_map] + list(gv_tables.values()):
            gv.add_footer()
            gv.close()

            dot = DotFile(gv.basename.replace('.gv', '.png'))
            dot.render(gv.filename)

            table_html = TableFile(gv.basename.replace('.gv', '.html'))
            table_html.render()

    # Generate HTML files
    html_file = IndexFile('index.html')
    html_file.render(imgs, db_size)

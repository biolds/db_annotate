#!/usr/bin/python3

import os
import sys
import subprocess

from db import DB
from db_size import DBSize
from dot import DotFile
from gv import GV
from html import HtmlFile
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

    gv = GV('relationship.gv')
    db_size = DBSize()

    # DB size pies
    for table in db.get_tables():
        sizes = db.get_table_size(table)
        db_size.add_table(table, sizes)
    imgs = db_size.render()

    # Tables
    if not gv.exists():
        gv.add_header()
        for table in db.get_tables():
            columns = db.get_columns(table)
            sizes = db.get_table_size(table)
            keys = db.get_table_keys(table)
            indexes = db.get_table_index(table)
            errors = db.get_table_errors(table)
            gv.add_table(table, errors, sizes, keys, indexes, columns)

        # Constraints
        for table in db.get_tables():
            for src, dst in db.get_foreign_keys(table):
                gv.add_constraint(src, dst)
        # Missing constraints
        for table in db.get_tables():
            for constraint in db.get_missing_constraints(table):
                gv.add_missing_constraint(*constraint)

        # Inheritance link
        for src, dst in db.get_inherited_tables():
            gv.add_inherited(src, dst)

        for tables, duplicate_type in db.get_duplicated_tables().items():
            src, dst = tables.split('/')
            gv.add_duplicate(src, dst, duplicate_type)

        namespaces = db.get_namespaces().items()
        if len(namespaces) != 1:
            # Show namespaces only when there are more than one
            for namespace, tables in namespaces:
                gv.add_namespace(namespace, tables)

        gv.add_footer()

    gv.close()
    dot = DotFile('relationship.png')
    dot.render(gv.filename)

    # Generate HTML files
    html_file = HtmlFile('index.html')
    html_file.render(imgs)

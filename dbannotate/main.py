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

import os
import sys
import subprocess

from .db import DB
from .db_size import DBSize
from .dot import DotFile
from .gv import GV
from .html import IndexFile, TableFile, FunctionFile, HilightCSSFile
from .output_file import OutputFile


def main():
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
    print('Building table sizes')
    for table in db.get_tables():
        print(table)
        sizes = db.get_table_size(table)
        db_size.add_table(table, sizes)
        gv_tables[table] = GV(table + '.gv')
        gv_tables[table].add_header()

    imgs = db_size.render()

    # Tables
    gv_map.add_header()

    print('Building graphs')
    for table in db.get_tables():
        columns = db.get_columns(table)
        sizes = db.get_table_size(table)
        keys = db.get_table_keys(table)
        indexes = db.get_table_index(table)
        errors = db.get_table_errors(table)
        gv_map.add_table(table, errors, sizes, keys, indexes, columns, [])
        triggers = db.get_triggers(table)
        gv_tables[table].add_table(table, errors, sizes, keys, indexes, columns, triggers, True)
        tables[table] = (table, errors, sizes, keys, indexes, columns, triggers)

    print('Adding constraints')
    # Constraints
    for table in db.get_tables():
        for src, dst in db.get_foreign_keys(table):
            gv_tables[table].add_table(*tables[dst[0]])
            gv_tables[table].add_constraint(src, dst)
            gv_tables[dst[0]].add_table(*tables[table])
            gv_tables[dst[0]].add_constraint(src, dst)
            gv_map.add_constraint(src, dst)

    print('Adding missing constraints')
    # Missing constraints
    for table in db.get_tables():
        for constraint in db.get_missing_constraints(table):
            gv_tables[table].add_table(*tables[constraint[2]])
            gv_tables[table].add_missing_constraint(*constraint)
            gv_tables[constraint[2]].add_table(*tables[table])
            gv_tables[constraint[2]].add_missing_constraint(*constraint)
            gv_map.add_missing_constraint(*constraint)

    print('Adding inheritance')
    # Inheritance link
    for src, dst in db.get_inherited_tables():
        gv_map.add_inherited(src, dst)
        gv_tables[src].add_table(*tables[dst])
        gv_tables[src].add_inherited(src, dst)
        gv_tables[dst].add_table(*tables[src])
        gv_tables[dst].add_inherited(src, dst)

    print('Adding duplicates')
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
        for namespace, _tables in namespaces:
            gv_map.add_namespace(namespace, _tables)

    print('Building graphs images')
    # Render the mini-map
    gv_map
    gv_map.add_footer()
    gv_map.close()

    dot = DotFile('map.png')
    dot.render(gv_map.filename)

    for table, gv in gv_tables.items():
        gv.add_footer()
        gv.close()

        dot = DotFile(gv.basename.replace('.gv', '.png'))
        dot.render(gv.filename)

        table_html = TableFile(gv.basename.replace('.gv', '.html'))
        table_html.render(*tables[table])

    # Functions
    functions = []
    _functions = db.get_functions()
    if len(_functions):
        print('Buildings functions')
        css = HilightCSSFile()
        css.render()
        for function in _functions:
            # TODO: there may be a naming conflict with table names here:
            fn_name, fn_lang, fn_code = function
            print(fn_name)
            html = FunctionFile('fn_%s.html' % fn_name)
            functions.append((fn_name, len(fn_code.splitlines())))
            html.render(*function)

        # Sort functions by higher lines count
        functions = sorted(functions, key=lambda x:x[1])

    # Generate HTML files
    html_file = IndexFile('index.html')
    html_file.render(imgs, db_size, db, functions)

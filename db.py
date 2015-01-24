#!/usr/bin/python3
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import ProgrammingError, InvalidRequestError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql import func
from sqlalchemy.types import Boolean, Enum, Integer

MIN_TABLE_SIZE = 10
ROW_LIMIT = 1000

# TODO: merge this function with db_size.humanize
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

class DB:
    def __init__(self, url):
        self.engine = create_engine(url, echo=False, pool_recycle=3600)
        self.inspector = Inspector.from_engine(self.engine)
        self.Session = sessionmaker()
        self.Session.configure(bind=self.engine)

    def get_tables(self):
        return self.inspector.get_table_names()

    def get_namespaces(self):
        # Grouping based on http://stackoverflow.com/questions/7852384/finding-multiple-common-starting-strings
        stringsByPrefix = {}
        for string in self.get_tables():
            if '_' not in string:
                continue
            prefix, suffix = string.split('_', 1)
            group = stringsByPrefix.setdefault(prefix, [])
            group.append(string)

        for namespace, tables in list(stringsByPrefix.items()):
            if len(tables) <= 1:
                stringsByPrefix.pop(namespace)
        return stringsByPrefix

    def get_column_names(self, table):
        return [col['name'] for col in self.inspector.get_columns(table)]

    def get_columns(self, table_name):
        columns = []
        sizes = self.get_table_size(table_name)
        session = self.Session()

        # reflect table from db
        table = Table(table_name, MetaData())
        self.inspector.reflecttable(table, None)

        for col in table.columns:
            try:
                # XXX hack to check sqlalchemy knows how to handle the data type
                tmp = str(col.type).lower()  # noqa
            except NotImplementedError:
                # Ignore user defined data types
                print('Unknown datatype, ignoring column %s of table %s' % (table, col.name), file=sys.stderr)
                continue

            # XXX hack to work with mysql which doesn't have a real 'boolean' type
            is_bool = isinstance(col.type, Boolean) or (isinstance(col.type, Integer) and getattr(col.type, 'display_width', None) == 1)

            col.errors = []
            if sizes[4] >= MIN_TABLE_SIZE:
                try:
                    subtable = session.query(col).select_from(table).limit(ROW_LIMIT).subquery()
                    sub_col = getattr(subtable.c, col.name)
                    res = session.query(sub_col, func.count(sub_col)).group_by(sub_col).limit(MIN_TABLE_SIZE).all()
                except InvalidRequestError:
                    print('Invalid request on:', table, col.name, file=sys.stderr)
                    continue
                if len(res) == 1 and res[0][1] > 1:
                    col.errors.append('value is always "%s"' % res[0][0])
                elif not is_bool:
                    if len(res) == 2:
                        col.errors.append('value is always "%s" or "%s"' % (res[0][0], res[1][0]))
                    elif sizes[4] >= 2 * MIN_TABLE_SIZE and len(res) < MIN_TABLE_SIZE and not isinstance(col.type, Enum):
                        col.errors.append('has less than %s distinct values' % MIN_TABLE_SIZE)
            columns.append(col)
        return columns

    def get_table_keys(self, table):
        keys = [k['constrained_columns'][0] for k in \
                    self.inspector.get_foreign_keys(table)]
        keys += self.inspector.get_pk_constraint(table)['constrained_columns']
        return keys

    def get_table_index(self, table):
        return [idx['column_names'][0] for idx in self.inspector.get_indexes(table)]

    def get_foreign_keys(self, table):
        return [((table, c['constrained_columns'][0]), (c['referred_table'], c['referred_columns'][0])) for c in self.inspector.get_foreign_keys(table)]

    def get_missing_constraints(self, table):
        class LoopBreak(Exception):
            pass
        missings = []
        constraints = self.get_foreign_keys(table)
        namespaces = self.get_namespaces()
        columns = self.get_column_names(table)
        for other_table in self.get_tables():
            if other_table == table:
                continue
            prefixes = ['']
            if '_' in other_table:
                namespace = other_table.split('_', 1)[0]
                if namespace in namespaces:
                    prefixes.append(namespace + '_')

            try:
                for column in columns:
                    has_constraint = False
                    for src, dst in constraints:
                        if (table, column) == src and dst[0] == other_table:
                            has_constraint = True
                    if has_constraint:
                        continue
                    for pattern in ['', 'id', '_id', '_ptr_id']:
                        for other_pattern_prefix in prefixes:
                            for other_pattern in ['', 's']:
                                if other_pattern_prefix + column + other_pattern == \
                                        other_table + pattern:
                                    constraints = self.get_foreign_keys(table)
                                    missings.append((table, column, other_table, 'missing constraint\\nor ambiguous naming'))
                                    raise LoopBreak
            except LoopBreak:
                pass
        return missings

    def get_inherited_tables(self):
        # Based on http://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
        try:
            r = self.engine.execute('''SELECT
                p.relname AS parent, c.relname AS child
            FROM
                pg_inherits JOIN pg_class AS c ON (inhrelid=c.oid)
                    JOIN pg_class as p ON (inhparent=p.oid);''')
            res = r.fetchall()
            return res
        except Exception:
            # if not supported by db
            return []

    def get_table_size(self, table):
        # Based on http://www.niwi.be/2013/02/17/postgresql-database-table-indexes-size/
        # TODO: remove try/except, use a portable query
        try:
            try:
                r = self.engine.execute('select pg_relation_size(%(table_name)s), pg_total_relation_size(%(table_name)s)', {'table_name': table})
            except Exception:
                r = self.engine.execute('select data_length, data_length + index_length FROM information_schema.TABLES WHERE table_name = %s', table)

            size, total_size = r.fetchone()

            r = self.engine.execute('select count(*) from %s' % table)
            count = r.fetchone()[0]
            return [sizeof_fmt(size), sizeof_fmt(total_size), size, total_size, int(count)]
        except ProgrammingError:
            # On permission denied
            return ['0', '0', 0, 0, 0]

    def get_duplicated_tables(self):
        tables = self.get_tables()
        columns = {}
        for table in tables:
            columns[table] = set(self.get_column_names(table))

        inherited = self.get_inherited_tables()
        inherited = ['/'.join(sorted([src, dst])) for src, dst in inherited]
        duplicated = {}
        for idx, table in enumerate(tables):
            for other_table in tables[idx + 1:]:
                dup_name = '/'.join(sorted([table, other_table]))
                if dup_name in inherited:
                    continue

                if columns[table] == columns[other_table]:
                    if dup_name not in duplicated:
                        duplicated[dup_name] = []
                    duplicated[dup_name] += ['same columns, could inherit']
                elif (columns[table].issubset(columns[other_table]) or \
                        columns[table].issubset(columns[other_table])) and \
                        len(columns[table] & columns[other_table]) > 2:
                    if dup_name not in duplicated:
                        duplicated[dup_name] = []
                    duplicated[dup_name] += ['could inherit']

        return duplicated

    def get_table_errors(self, table):
        table_size = self.get_table_size(table)[4]
        errors = []
        if table_size == 0:
            errors += ['empty table']
        elif table_size < MIN_TABLE_SIZE:
            errors += ['has only %s entries' % table_size]

        foreign = self.inspector.get_foreign_keys(table)
        primary = self.inspector.get_pk_constraint(table)
        inherited = self.get_inherited_tables()

        if len(foreign) == 0 and len(primary) == 0 and \
                table not in [i[1] for i in inherited]:
            errors += ['has no foreign or primary key']
        return errors

#!/usr/bin/python3

from sqlalchemy import create_engine
from sqlalchemy.engine.reflection import Inspector

MIN_TABLE_SIZE = 10

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

    def get_tables(self):
        return self.inspector.get_table_names()

    def get_column_names(self, table):
        return [col['name'] for col in self.inspector.get_columns(table)]

    def get_columns(self, table):
        """
        Return value: [(name, type, length, nullable, default, unique, [errors])]
        """
        columns = []
        uniques = self.inspector.get_unique_constraints(table)
        sizes = self.get_table_size(table)
        for col in self.inspector.get_columns(table):
            unique = col['name'] in uniques
            type_name = col['type'].python_type.__name__
            sql_type = type(col['type']).__name__
            if hasattr(col['type'], 'length'):
                length = col['type'].length
            else:
                length = None

            errors = []
            if sizes[4] >= MIN_TABLE_SIZE:
                r = self.engine.execute('SELECT %s, COUNT(%s) FROM %s GROUP BY %s LIMIT %s' % (col['name'], col['name'], table, col['name'], MIN_TABLE_SIZE))
                res = r.fetchall()
                if len(res) == 1 and res[0][1] > 1:
                    errors.append('value is always "%s"' % res[0][0])
                elif len(res) == 2 and type_name != 'bool':
                    errors.append('value is always "%s" or "%s"' % (res[0][0], res[1][0]))
                elif len(res) < MIN_TABLE_SIZE and sql_type != 'enumeration':
                    lines_count = sum([r[1] for r in res])
                    if lines_count > MIN_TABLE_SIZE:
                        errors.append('has less than %s distinct values' % MIN_TABLE_SIZE)
            columns.append((col['name'], sql_type, length, col['nullable'], col['default'], unique, errors))
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
        constraints = []
        columns = self.get_column_names(table)
        for other_table in self.get_tables():
            if other_table == table:
                continue
            for column in columns:
                #print('other_table:', other_table)
                for pattern in ['', 'id', '_id', '_ptr_id']:
                    for other_pattern in ['', 's']:
                        if column + other_pattern == other_table + pattern:
                            constraints.append((table, column, other_table, 'missing constraint\nor ambiguous naming'))
                            break
                    else:
                        continue
                    break
        #print('constraints:', constraints)
        return constraints

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
        try:
            r = self.engine.execute('select pg_relation_size(%(table_name)s), pg_total_relation_size(%(table_name)s)', {'table_name': table})
        except Exception:
            r = self.engine.execute('select data_length, data_length + index_length FROM information_schema.TABLES WHERE table_name = %s', table)

        size, total_size = r.fetchone()

        r = self.engine.execute('select count(*) from %s' % table)
        count = r.fetchone()[0]
        return [sizeof_fmt(size), sizeof_fmt(total_size), size, total_size, int(count)]

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

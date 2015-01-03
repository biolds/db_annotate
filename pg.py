#!/usr/bin/python3
import sys

import psycopg2

MIN_TABLE_SIZE = 10

class PG:
    def __init__(self):
        try:
            if len(sys.argv) == 1:
                raise Exception('No connection to database specified')
            self.conn = psycopg2.connect(' '.join(sys.argv[1:]))
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(e)
            help_str = psycopg2.connect.__doc__.splitlines()
            help_str = [s.strip()for s in help_str]
            PG_HELP_STR = "The basic connection parameters are:"
            if PG_HELP_STR in help_str:
                help_str_idx = help_str.index(PG_HELP_STR)
                help_str = help_str[help_str_idx:help_str_idx + 7]
                help_str = '\n'.join(help_str)
            else:
                help_str = "Please specify db options parameters"

            print(help_str, file=sys.stderr)
            print("\nFor example %s dbname=localhost user=postgres" % sys.argv[0], file=sys.stderr)
            sys.exit(1)

    def get_tables(self):
        self.cursor.execute('''SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name''')
        res = self.cursor.fetchall()
        return [r[0] for r in res]

    def get_columns(self, table):
        self.cursor.execute('''SELECT column_name, data_type, character_maximum_length, is_nullable, column_default 
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %(table_name)s
        ''', {'table_name': table})
        res = self.cursor.fetchall()
        unicity = self.get_constraints(table, 'UNIQUE')
        unicity = [u[0][1] for u in unicity]
        unicity = [col + (col[0] in unicity,) for col in res]
        _res = []

        # Check value differences
        for col in unicity:
            self.cursor.execute('SELECT %s, COUNT(%s) FROM %s GROUP BY %s LIMIT %s' % (col[0], col[0], table, col[0], MIN_TABLE_SIZE))
            res = self.cursor.fetchall()
            error = []
            if len(res) == 1 and res[0][1] > 1:
                error.append('value is always "%s"' % res[0][0])
            elif len(res) == 2 and col[1] != 'boolean':
                error.append('value is always "%s" or "%s"' % (res[0][0], res[1][0]))
            elif len(res) < MIN_TABLE_SIZE and col[1] != 'enumeration':
                lines_count = sum([r[1] for r in res])
                if lines_count > MIN_TABLE_SIZE:
                    error.append('has less than %s distinct values' % MIN_TABLE_SIZE)
            _res.append(col + (error, ))
        return _res

    def get_table_keys(self, table):
        self.cursor.execute('''SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = 'public'
        AND table_name = %(table_name)s
        ''', {'table_name': table})
        res = self.cursor.fetchall()
        return [r[0] for r in res]

    def get_table_index(self, table):
        # Based on http://stackoverflow.com/questions/2204058/show-which-columns-an-index-is-on-in-postgresql
        self.cursor.execute('''select
            a.attname as column_name
        from
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        where
            t.oid = ix.indrelid
            and i.oid = ix.indexrelid
            and a.attrelid = t.oid
            and a.attnum = ANY(ix.indkey)
            and t.relkind = 'r'
            and t.relname = %(table_name)s
        order by
            t.relname,
            i.relname''', {'table_name': table})

        res = self.cursor.fetchall()
        return [r[0] for r in res]

    def get_constraints(self, table, constraint_type='FOREIGN KEY'):
        # Based on http://stackoverflow.com/questions/1152260/postgres-sql-to-list-table-foreign-keys
        #print('table:', table, 'constraint:', constraint_type)
        self.cursor.execute('''SELECT
            tc.table_name, kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = %(constraint_type)s AND tc.table_name = %(table_name)s
        ''', {'constraint_type': constraint_type, 'table_name': table})
        res = self.cursor.fetchall()
        res = [((r[0], r[1]), (r[2], r[3])) for r in res]
        return res

    def get_missing_constraints(self, table):
        constraints = []
        columns = [col[0] for col in self.get_columns(table)]
        for other_table in self.get_tables():
            if other_table == table:
                continue
            for column in columns:
                #print('other_table:', other_table)
                for pattern in ['', 'id', '_id', '_ptr_id']:
                    for other_pattern in ['', 's']:
                        if column + other_pattern == other_table + pattern:
                            constraints.append((table, column, other_table, 'missing constraint or ambiguous naming'))
                            break
                    else:
                        continue
                    break
        #print('constraints:', constraints)
        return constraints

    def get_inherited_tables(self):
        # Based on http://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
        self.cursor.execute('''SELECT
            p.relname AS parent, c.relname AS child
        FROM
            pg_inherits JOIN pg_class AS c ON (inhrelid=c.oid)
                JOIN pg_class as p ON (inhparent=p.oid);''')
        res = self.cursor.fetchall()
        return res

    def get_table_size(self, table):
        # Based on http://www.niwi.be/2013/02/17/postgresql-database-table-indexes-size/
        self.cursor.execute('select pg_size_pretty(pg_relation_size(%(table_name)s)), pg_size_pretty(pg_total_relation_size(%(table_name)s)), pg_relation_size(%(table_name)s), pg_total_relation_size(%(table_name)s)', {'table_name': table})
        res = self.cursor.fetchall()[0]
        res = [str(size).replace(' ', '').replace('bytes', 'b') for size in res]
        self.cursor.execute('select count(*) from %s' % table)
        res += self.cursor.fetchall()[0]
        return res

    def get_duplicated_tables(self):
        tables = self.get_tables()
        columns = {}
        for table in tables:
            columns[table] = set([col[0] for col in self.get_columns(table)])

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

        foreign = self.get_constraints(table)
        primary = self.get_constraints(table, 'PRIMARY KEY')
        inherited = self.get_inherited_tables()

        if len(foreign) == 0 and len(primary) == 0 and \
                table not in [i[1] for i in inherited]:
            errors += ['has no foreign or primary key']
        return errors

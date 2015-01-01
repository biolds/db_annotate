#!/usr/bin/python3
import sys

import psycopg2


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
            exit(sys.EXIT_FAILURE)

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
        _res = []
        unicity = self.get_constraints(table, 'UNIQUE')
        unicity = [u[0][1] for u in unicity]
        unicity = [col + (col[0] in unicity,) for col in res]
        return unicity

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
        #print('res:', res)

        return [((r[0], r[1]), (r[2], r[3])) for r in res]

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
        self.cursor.execute('select pg_size_pretty(pg_relation_size(%(table_name)s)), pg_size_pretty(pg_total_relation_size(%(table_name)s))', {'table_name': table})
        res = self.cursor.fetchall()[0]
        res = [size.replace(' ', '').replace('bytes', 'b') for size in res]
        self.cursor.execute('select count(*)::char from %s' % table)
        res += self.cursor.fetchall()[0]
        return res

from collections import OrderedDict
from tempfile import NamedTemporaryFile

from matplotlib import colors
from matplotlib.cm import get_cmap, ScalarMappable
from matplotlib.pyplot import figure, savefig

from output_file import OutputFile

FIG_BASE_SIZE = 4
TOP_N_VALUES = 10


def humanize(s, counter_type):
    PREFIX = ['', 'k', 'M', 'G', 'T', 'P']
    for prefix in PREFIX:
        if counter_type == 'b':
            if s < 1024:
                break
            s = s / 1024
        else:
            if s < 1000:
                break
            s = s / 1000
    else:
        return 'total count too big'
    return str(int(s)) + prefix + counter_type


class DBSize(OutputFile):
    GRAPHS = OrderedDict(((
        'tables', {
            'title': 'Tables sizes (w/o indices)',
            'counter_type': 'b',
        }), (
        'total', {
            'title': 'Total tables sizes',
            'counter_type': 'b',
        }), (
        'lines_count', {
            'title': 'Lines counts',
            'counter_type': '',
        }), (
        'mean_lines', {
            'title': 'Mean lines sizes',
            'counter_type': 'b',
        }),
    ))

    def __init__(self, filename):
        super(DBSize, self).__init__(filename)
        self.tables_size = {}
        self.total_size = {}
        self.lines_count_size = {}
        self.mean_lines_size = {}

    def add_table(self, table, sizes):
        sizes = [int(s) for s in sizes[2:]]
        self.tables_size[table] = sizes[0]
        self.total_size[table] = sizes[1]
        self.lines_count_size[table] = sizes[2]

        if sizes[2] == 0:
            self.mean_lines_size[table] = 0
        else:
            self.mean_lines_size[table] = sizes[1] / float(sizes[2])

    def render(self):
        fig = figure(figsize=(FIG_BASE_SIZE * 2, FIG_BASE_SIZE * len(self.GRAPHS)))

        _colors = ScalarMappable(norm=colors.Normalize(vmin=0, vmax=TOP_N_VALUES + 0.5), cmap=get_cmap('jet'))
        _colors = _colors.to_rgba(range(TOP_N_VALUES))
        _colors = list(reversed(_colors))

        for i, graph in enumerate(self.GRAPHS.keys()):
            graph_len = float(len(self.GRAPHS))
            axis = fig.add_axes([0.25, (int(graph_len) - 1 - i) / graph_len, 0.5 * 0.9, 0.9 * (1 / graph_len)])
            tables = getattr(self, graph + '_size')
            sorted_values = list(((k, tables[k]) for k in sorted(tables, key=tables.get, reverse=True)))[:TOP_N_VALUES]

            for j, val in enumerate(sorted_values):
                if val[1] < sorted_values[0][1] * 0.01: # 0.01 to limit the size of smallest part of th pie
                    sorted_values = sorted_values[:j]
                    break

            values = [val[1] for val in sorted_values]
            
            labels = ['%s %s' % (val[0], humanize(val[1], self.GRAPHS[graph]['counter_type'])) for val in sorted_values]
            axis.pie(values, labels=labels, colors=_colors)
            axis.set_title('%s %s' % (self.GRAPHS[graph]['title'], 'Top %i' % TOP_N_VALUES))

        savefig(self.filename)

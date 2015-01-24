from collections import OrderedDict
import copy
import os

from pygal import Pie, Config
from pygal.style import SolidColorStyle

from .output_file import OutputFile, OUTPUT_DIR

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
    # Size of the image in pixels
    IMG_SIZE = (600, 600)
    FIG_SIZE = (IMG_SIZE[0] / 100, IMG_SIZE[1] / 100)

    # Size of the pie in the image in %
    PIE_SIZE = 0.4

    GRAPHS = OrderedDict(((
        'total', {
            'title': 'Total tables sizes',
            'counter_type': 'b',
        }), (
        'tables', {
            'title': 'Tables sizes (w/o indexes)',
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

    def __init__(self):
        super(DBSize, self).__init__('total-0.png')
        self.tables_size = {}
        self.total_size = {}
        self.lines_count_size = {}
        self.mean_lines_size = {}
        self.pygal_config = Config()
        self.pygal_config.human_readable = True
        self.pygal_config.legend_box_size = 24
        self.pygal_config.show_legend = True
        self.pygal_config.show_values = True
        self.pygal_config.style = SolidColorStyle
        self.pygal_config.style.colors = ['#ff3000', '#ff8900', '#ffe500', \
            '#b7ff3f', '#66ff90', '#18ffdd', '#00a4ff', '#0040ff', '#0000ec', '#00007f']
        self.pygal_config.style.opacity = '.9'
        self.pygal_config.style.opacity_hover = '.4'
        self.pygal_config.style.transition = '100ms ease-in'
        self.pygal_config.truncate_legend = 9999999

    def _get_filename(self, base, n):
        return os.path.join(OUTPUT_DIR, '%s-%i.svg' % (base, n))

    def add_table(self, table, sizes):
        sizes = [int(s) for s in sizes[2:]]
        self.tables_size[table] = sizes[0]
        self.total_size[table] = sizes[1]
        self.lines_count_size[table] = sizes[2]

        if sizes[2] == 0:
            self.mean_lines_size[table] = 0
        else:
            self.mean_lines_size[table] = sizes[1] / float(sizes[2])

    def _render_pie(self, values, labels, title, filename):
        pie_chart = Pie(config=self.pygal_config)
        pie_chart.title = title
        for label, val in zip(labels, values):
            pie_chart.add(label, val)
        pie_chart.render_to_file(filename)

    def render(self):
        imgs = []

        for i, graph in enumerate(self.GRAPHS.keys()):
            # Add the total size pies
            tables = getattr(self, graph + '_size')
            sorted_values = list(((k, tables[k]) for k in sorted(tables, key=tables.get, reverse=True)))

            filename = self._get_filename(graph, i)
            title = '%s %s' % (self.GRAPHS[graph]['title'], 'Total Top %i' % TOP_N_VALUES)
            imgs.append([{'title': title, 'filename':filename}])
            # Totals graphs
            total_values = copy.copy(sorted_values[:TOP_N_VALUES])
            for j, val in enumerate(total_values):
                if val[1] < sorted_values[0][1] * 0.01: # 0.01 to limit the size of smallest part of the pie
                    total_values = sorted_values[:j]
                    break

            values = [val[1] for val in total_values]
            labels = ['%s %s' % (val[0], humanize(val[1], self.GRAPHS[graph]['counter_type'])) for val in total_values]
            self._render_pie(values, labels, title, filename)

            def grouped(iterable, n):
                "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
                return zip(*[iter(iterable)]*n)

            # Other graphs
            groups = list(grouped(sorted_values, TOP_N_VALUES))
            for j, values in enumerate(groups):
                filename = self._get_filename(graph + str(i), j)
                title = '%s %s' % (self.GRAPHS[graph]['title'], 'All %i/%i' % (j + 1, len(groups)))
                imgs[-1].append({'title': title, 'filename':filename})

                _values = [val[1] for val in values]
                labels = ['%s %s' % (val[0], humanize(val[1], self.GRAPHS[graph]['counter_type'])) for val in values]
                self._render_pie(_values, labels, title, filename)
        return imgs

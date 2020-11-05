import pickle
import matplotlib.pyplot as plt
import numpy as np

from utility import table_rows, table_columns, table_label_data

service_data = {
    'google' : {
        'name' : 'Google',
        'color' : '#4185F4',
        'index' : 1,
    },
    'amazon' : {
        'name' : 'Amazon',
        'color' : '#D9882D',
        'index' : 2,
    },
    'azure': {
        'name': 'Azure',
        'color': '#7FBC00',
        'index': 0,
    },
    'sphinx': {
        'name': 'CMU Sphinx',
        'color': '#84172D',
        'index': 3,
    },
}

labeled_services = []

def draw_data_point(identifier, service, value, emph=False):
    lw = 3 if not emph else 4
    line_length = 0.35 if not emph else 0.4
    loc = table_rows.index(identifier[7:])
    color = service_data[service]['color']
    z_offset = service_data[service]['index']
    x_coords = np.linspace(loc-line_length, loc+line_length, 5)

    for i in range(4):
        if service not in labeled_services:
            label = service_data[service]['name']
            labeled_services.append(service)
        else:
            label = None

        zorder = ((i+z_offset) % 4) + 2
        plt.plot(x_coords[[i, i+1]], [value, value], c=color, lw=lw, label=label, zorder=zorder)

def create_figure(metric, file_name, metric_name, show=False, mark_highest=True):
    skip_cond = lambda sc: sc is None or type(sc[metric]) == str

    fig = plt.figure()
    fig.set_size_inches(7.0, 3.5)

    for identifier in table_rows:
        data_lines = [(id, se, sc) for id, se, sc in data if id == ('OH_ZP1_' + identifier)]

        if mark_highest:
            best = np.argmax([sc[metric] if not skip_cond(sc) else -np.inf for id, se, sc in data_lines])
        else:
            best = np.argmin([sc[metric] if not skip_cond(sc) else np.inf for id, se, sc in data_lines])

        for i, (id, se, sc) in enumerate(data_lines):
            if not skip_cond(sc):
                draw_data_point(id, se, sc[metric], emph=False)
                # draw_data_point(id, se, sc[metric], emph=(i == best))

    x_ticks = list(range(len(table_rows)))
    x_labels = [table_label_data[table_rows[i]]['language'] for i in range(len(table_rows))]
    x_labels[4] += '(1)'
    x_labels[5] += '(2)'
    plt.xticks(x_ticks, x_labels, rotation=45, ha='right', va='center_baseline', fontsize=9)
    plt.ylabel(metric_name)
    plt.legend(loc='lower left', fancybox=False, edgecolor='k', prop={'size' : 9},
               bbox_to_anchor=(0., 1.03, 1., 0.25), ncol=4, mode='expand', borderaxespad=0.0, borderpad=0.5)
    plt.grid(linestyle='--')
    plt.tight_layout()
    fig.savefig('%s.png' % file_name)

    if show:
        plt.show()

data = pickle.load(open('../../Develop/scores.p', 'rb'))

# create_figure('wer', 'word_error_rate', 'Word Error Rate', show=True, mark_highest=False)
# create_figure('tf_idf', 'tf_idf', 'tf-idf', show=True)
create_figure('tf', 'term_frequency', 'Term Frequency', show=True)
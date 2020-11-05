import pickle
import colorsys
import numpy as np

from utility import table_rows, table_columns, table_label_data

def format_color(color, hsv=False, box=True, box_size='2.5'):
    if hsv:
        color = colorsys.hsv_to_rgb(*color)

    if box:
        # \cbox needs to be defined
        # \newcommand{\cbox}[3][black]{\textcolor[rgb]{#1}{\rule{#2}{#3}}}
        return '\cbox[%.2f,%.2f,%.2f]{%smm}{%smm}' % (*tuple(color), box_size, box_size)
    else:
        return '\cellcolor[rgb]{%.2f,%.2f,%.2f}' % tuple(color)

# populate table
raw_data = pickle.load(open('../../Develop/scores.p', 'rb'))
table_data = np.zeros((len(table_rows), len(table_columns), 3), dtype=object)
for identifier, service, scores in raw_data:
    loc = table_rows.index(identifier[7:]), table_columns.index(service)
    if scores is None:
        value = ['n/a'] * 3
    else:
        value = [scores['wer'], scores['tf_idf'], scores['tf']]
        if np.isnan(scores['wer']):
            value[0] = 'nan'

    table_data[loc[0], loc[1]] = value

# create tex tables
## availability table
def format_line_availability(label_data, line):
    def format_entry(entry):
        if entry == 'y':
            text = 'Yes'
            color = (94, 186, 125)
        else:
            text = 'No'
            color = (186, 102, 94)
        return  format_color([v/255 for v in color], box_size='4.0') + r'\makebox[8mm]{\raisebox{0.6mm}{\textcolor{black!70}{ %s}}}' % text

    entries = [format_entry(entry) for entry in line]
    text = ' & '.join([label_data['language'], *entries]) + r' \\'
    return text

availability_tex_lines = []
for i, line in enumerate(table_data):
    if i == 5: # second russian
        continue

    row_data = table_label_data[table_rows[i]]
    line = ['n' if entry == 'n/a' else 'y' for entry in line[:, 0]]

    availability_tex_lines.append(format_line_availability(row_data, line))
availability_tex_table = '\n'.join(availability_tex_lines)

print(availability_tex_table, file=open('availability_table.tex', 'w'))

## wer table
def format_score_line(language, line, emph=None):
    def format_entry(entry, emph=False):
        if type(entry) == str or np.isnan(entry):
            text = '--'
        else:
            text = '%.3f' % entry

        if emph:
            text = '\\textbf{%s}' % text
        return text

    if emph == 'h':
        best_entry = np.argmax([entry if type(entry) != str else -np.inf for entry in line])
    elif emph == 'l':
        best_entry = np.argmin([entry if type(entry) != str else np.inf for entry in line])
    else:
        best_entry = -1

    formatted_entries = [format_entry(entry, i==best_entry) for i, entry in enumerate(line)]
    text = ' & '.join([language, *formatted_entries]) + r' \\'
    return text

def format_csv_score_line(language, line):
    def format_entry(entry):
        if type(entry) == str or np.isnan(entry):
            text = '-'
        else:
            text = '%.3f' % entry
        return text

    text = ', '.join([language, *[format_entry(entry) for entry in line]])
    return text

for j, (metric, emph_type) in enumerate([('wer', 'l'), ('tf_idf', 'h'), ('tf', 'h')]):
    table_tex_lines = []
    table_csv_lines = []
    for i, line in enumerate(table_data):
        row_data = table_label_data[table_rows[i]]

        language = row_data['language']
        if table_rows[i] == '259':
            language += '(1)'
        if table_rows[i] == '031':
            language += '(2)'

        table_tex_lines.append(format_score_line(language, line[:, j], emph=emph_type))
        table_csv_lines.append(format_csv_score_line(language, line[:, j]))

    table_tex = '\n'.join(table_tex_lines)
    print(table_tex, file=open('%s_table.tex' % metric, 'w'))

    table_csv = '\n'.join(table_csv_lines)
    print(table_csv, file=open('%s_table.csv' % metric, 'w'))
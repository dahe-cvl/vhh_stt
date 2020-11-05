import numpy as np
import xml.etree.ElementTree as ET
from enum import Enum
from collections import Counter
import os
from difflib import HtmlDiff
import pdftotext
import subprocess
import re

from parse_config import is_comment, is_int, is_timestamp, get_config

class LineType(Enum):
    TEXT = 1
    COMMENT = 2
    TIMESTAMP = 3

# combine certain elements in list.
# all consecutive list elements that are the same according to <comparator> are combined with <joiner>
def combine(list, comparator, joiner):
    if len(list) == 0:
        return list

    reduced_list = []
    current_run = [list[0]]
    for element in list[1:]:
        if comparator(current_run[0], element):
            current_run.append(element)
        else:
            reduced_list.append(joiner(current_run))
            current_run = [element]

    reduced_list.append(joiner(current_run))
    return reduced_list

def get_parse_diff(pdf_path, parsed_text):
    # read pdf text
    file = open(pdf_path, 'rb')
    pdf = pdftotext.PDF(file)
    pdf_text = '\n'.join([pdf[i] for i in range(len(pdf))])

    html_diff = HtmlDiff().make_file(pdf_text.split(), parsed_text.split())
    return html_diff

class ParseDocument():
    def __init__(self):
        self.document_info = None
        self.speaker = 'Unknown'

    def get_document_info(self, pages):
        document_info = {
            'font_sizes': {},
            'left_margin': []
        }

        for page in pages:
            # add new fontspecs
            fontspecs = {line.attrib.get('id') : line.attrib.get('size') for line in page.findall('fontspec')}
            document_info['font_sizes'].update(fontspecs)

            # find lowest x-coordinate with text (to detect line number)
            left_coords = [int(line.attrib.get('left')) for line in page.findall('text')]
            least_left = np.min(list(filter(lambda l: l is not None, left_coords)))
            document_info['left_margin'].append(least_left)

        # find dominant font on first page with transcribed text
        fonts = [line.attrib.get('font') for line in pages[1].findall('text')]
        font_counter = Counter(filter(lambda f: f is not None, fonts))
        primary_font = font_counter.most_common(1)[0][0]
        document_info['primary_font'] = primary_font
        document_info['primary_font_size'] = document_info['font_sizes'][primary_font]

        return document_info

    def process_text_line(self, text):
        # remove unwanted symbols [hyphen-minus, dash, em-dash, ...]
        for s in ['-', '–', '—', '/', '„', '“', '”', '«', '»']:
            text = text.replace(s, ' ')
        # replace some characters with others
        for a, b in [(';', '.'), ('’', '\'')]:
            text = text.replace(a, b)

        # file specific line manipulations
        text = cfg['line_manipulation'](text)

        # remove content in square brackets
        text = re.sub(r'\[.*?\]', '', text)

        # remove leading whitespace around certain symbols
        for s in ['.', ',']:
            text = s.join([t.rstrip() for t in text.split(s)])

        # remove repeated symbols
        for s in ['.', ',']:
            text = re.sub(re.escape(s) + '+', s + ' ', text)

        # replace excess whitespace with space
        text = ' '.join(text.split())
        return text

    def parse_lines(self, line_iterator):
        for page_number, raw_line in line_iterator:
            text = ''.join(raw_line.itertext()).strip()

            font = raw_line.attrib.get('font')
            if cfg['text_check_type'] == 'font':
                is_primary_type = font == self.document_info['primary_font']
            else:
                font_size = self.document_info['font_sizes'][raw_line.attrib.get('font')]
                is_primary_type = font_size == self.document_info['primary_font_size']

            is_text = (is_primary_type and not font in cfg['font_blacklist']) or font in cfg['font_whitelist']
            page_margin = self.document_info['left_margin'][page_number]
            is_line_number = is_int(text) and int(raw_line.attrib.get('left')) - 10 <= page_margin

            # text is empty or line number
            if len(text) == 0 or is_line_number:
                continue
            # line is metadata
            elif is_comment(text):
                # remove square brackets
                text = text[1:-1]
                is_stamp, time = is_timestamp(text)
                if is_stamp:
                    yield [LineType.TIMESTAMP, time, text]
                else:
                    yield [LineType.COMMENT, None, text]

            # line is text
            elif is_text:
                # starts with initials
                initials, text = cfg['get_initials'](text)
                if len(initials) > 0:
                    self.speaker = initials

                yield [LineType.TEXT, self.speaker, text]
            else:
                print('dropping line:', ET.tostring(raw_line))

    def parse(self, root, n_pages=None):
        pages = root if n_pages is None else root[:n_pages + 1]
        self.document_info = self.get_document_info(pages)

        # don't parse title page
        def line_iterator():
            for i, page in enumerate(pages[1:]):
                xml_lines = page.findall('text')
                for xml_line in xml_lines:
                    yield i, xml_line

        lines = list(self.parse_lines(line_iterator()))

        def line_comparator(a, b):
            # LineType and font are the same
            return a[0] == b[0] == LineType.TEXT and a[1] == b[1]

        def line_joiner(list):
            text = ' '.join([element[2] for element in list])
            return [list[0][0], list[0][1], text]

        lines = combine(lines, line_comparator, line_joiner)

        # process text lines
        for line in lines:
            if line[0] == LineType.TEXT:
                line[2] = self.process_text_line(line[2])

        return lines

## configuration
directory = 'text_transcripts'
current_file = 'OH_ZP1_817'
file_name, cfg = get_config(current_file)
file_name = os.path.join(directory, file_name)
base_path = os.path.join(directory, current_file)

## create xml
subprocess.run(['pdftohtml', os.path.join(directory, file_name), '-xml', '-i'])

## parse content
parser = ET.XMLParser(encoding='utf-8')
tree = ET.parse(os.path.splitext(file_name)[0] + '.xml', parser=parser)
root = tree.getroot()
root = cfg['xml_manipulation'](root)

n_pages = None
document_parser = ParseDocument()
lines = document_parser.parse(root, n_pages)

## save data
# includes comments and timestamps
formatted_text = '\n'.join(map(str, lines))
print(formatted_text, file=open(base_path + '_formatted.txt', 'w'))

# text only
text = ' '.join([line[2] for line in lines if line[0] == LineType.TEXT])
print(text, file=open(base_path + '_punctuated.txt', 'w'))

# plain text with punctuation removed
punctuation_symbols = r'!"#$%&()*+,-./:;<=>?¿@[\]^_`{|}~'
plain_text = text.translate((str.maketrans('', '', punctuation_symbols)))
print(plain_text, file=open(base_path + '_plain.txt', 'w'))

# diffs between entire pdf content and plain_text formatted as html
html_diff = get_parse_diff(file_name, plain_text)
print(html_diff, file=open(base_path + '_diff.html', 'w'))

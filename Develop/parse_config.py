import re
import numpy as np

def is_comment(text):
    return text[0] == '[' and text[-1] == ']'

def is_int(string):
    try:
        int(string)
        return True
    except ValueError:
        return False

def is_timestamp(text):
    for deliminator in ['.', ':']:
        int_parts = [int(part) for part in text.split(deliminator) if is_int(part)]
        if len(int_parts) != 3 or np.any([part is None for part in int_parts]):
            continue

        if int_parts[1] < 60 and int_parts[2] < 60:
            seconds = ((int_parts[0] * 60) + int_parts[1] * 60) + int_parts[2]
            return (True, seconds)

    return (False, None)

def get_initials(text):
    # in some pdfs initials have '–  ' as prefix
    if text[:3] == '–  ':
        text = text[3:]

    # check if line has the form 'AB- other text' (or similar) where the first to characters are initials
    if len(text) < 4:
        return '', text

    maybe_initials = text[:2]
    initials = maybe_initials.isalpha() and maybe_initials.isupper()
    if initials and (text[2:4] == '- ' or text[2:4] == ': '):
        return text[:2], text[4:]
    else:
        return '', text

# ------------------------------
# modifications

def OH_ZP1_195_get_initials(text):
    text = re.sub(r'^([A-Z]) *([A-Z])\.?: ', r'\1\2: ', text)
    return get_initials(text)

def OH_ZP1_208_get_initials(text):
    # on first occurence name is spelled out instead of initials only
    text = text.replace('Julia Montredon (JM)', 'JM ', 1)
    text = text.replace('Marie Salou (MS)', 'MS ', 1)
    text = re.sub(r'^([A-Z]{2}) :', r'\1: ', text)
    return get_initials(text)

def OH_ZP1_214_get_initials(text):
    # remove two lines with follwing format
    text = re.sub(r'^Van der Willik 1 – [0-9]', '', text)

    # Initials are expected to be two letters only
    text = text.replace('MVdW:', 'MW:', 1)
    text = re.sub(r'^([A-Z]{2}):', r'\1: ', text)
    return get_initials(text)

def OH_ZP1_259_xml_manipulation(root):
    for line in root[0][29:46][::-1]:
        root[1].insert(3, line)
    return root

def OH_ZP1_259_get_initials(text):
    text = re.sub(r'^([А-Я])\.([А-Я])\.', r'\1\2: ', text)
    return get_initials(text)

def OH_ZP1_291_get_initials(text):
    text = re.sub(r'^([A-Z]{2}):', r'\1: ', text)
    return get_initials(text)

def OH_ZP1_291_line_manipulation(line):
    line = line.replace('{', '[')
    line = line.replace('}', ']')
    line = re.sub(r'[0-9]{2}:[0-9]{2}:[0-9]{2}', '', line)
    return line

def OH_ZP1_673_xml_manipulation(root):
    for line in root[1][7:24]:
        root[1].remove(line)
    return root

def OH_ZP1_795_get_initials(text):
    # on first occurence name is spelled out instead of initials only
    text = text.replace('Irena Rowińska:', 'IR:', 1)
    text = text.replace('Monika Kapa-Cichocka:', 'MK:', 1)
    text = text.replace('MK-C:', 'MK:', 1)
    text = text.replace('Jerzy Tabor:', 'JK:', 1)
    return get_initials(text)

def OH_ZP1_795_line_manipulation(line):
    line = line.replace(' ż ', ' ż')
    return line

files = {
    'OH_ZP1_016' : {
        'path' : 'OH_ZP1_016_Todros_Alberto.pdf',
        'cfg' : {}
    },
    'OH_ZP1_031' : {
        'path' : 'OH_ZP1_031_Tereschenko_Nadejscha.pdf',
        'cfg' : {}
    },
    'OH_ZP1_163' : {
        'path' : 'OH_ZP1_163_Ferenczi_Pal.pdf',
        'cfg' : {
            'text_check_type' : 'font'
        }
    },
    'OH_ZP1_195' : {
        'path' : 'OH_ZP1_195_Cabeza_Letosa_Carlos.pdf',
        'cfg' : {
            'get_initials' : OH_ZP1_195_get_initials
        }
    },
    'OH_ZP1_208' : {
        'path' : 'OH_ZP1_208_Salou_Marie.pdf',
        'cfg' : {
            'get_initials' : OH_ZP1_208_get_initials
        }
    },
    'OH_ZP1_214' : {
        'path' : 'OH_ZP1_214_Van_der_Willik_Martinus.pdf',
        'cfg' : {
            'get_initials' : OH_ZP1_214_get_initials
        }
    },
    'OH_ZP1_259' : {
        'path' : 'OH_ZP1_259_Driga_Sergey.pdf',
        'cfg' : {
            'get_initials' : OH_ZP1_259_get_initials,
            'xml_manipulation' : OH_ZP1_259_xml_manipulation
        }
    },
    'OH_ZP1_291' : {
        'path' : 'OH_ZP1_291_Liebman_Irena.pdf',
        'cfg' : {
            'get_initials' : OH_ZP1_291_get_initials,
            'line_manipulation' : OH_ZP1_291_line_manipulation
        }
    },
    'OH_ZP1_423' : {
        'path' : 'OH_ZP1_423_Weisbord_Ann.pdf',
        'cfg' : {}
    },
    'OH_ZP1_625' : {
        'path' : 'OH_ZP1_625_Kambanellis_Iacovos.pdf',
        'cfg' : {}
    },
    'OH_ZP1_673' : {
        'path' : 'OH_ZP1_673_Jovanovic_Nikola.pdf',
        'cfg' : {
            'xml_manipulation' : OH_ZP1_673_xml_manipulation
        }
    },
    'OH_ZP1_693' : {
        'path' : 'OH_ZP1_693_Gosnik_Tone.pdf',
        'cfg' : {
            'font_whitelist' : ['1']
        }
    },
    'OH_ZP1_795' : {
        'path' : 'OH_ZP1_795_Rowinska_Anna.pdf',
        'cfg' : {
            'get_initials' : OH_ZP1_795_get_initials,
            'line_manipulation' : OH_ZP1_795_line_manipulation
        }
    },
    'OH_ZP1_817' : {
        'path' : 'OH_ZP1_817_Selucka_Eva.pdf',
        'cfg' : {}
    },
}

# parameters
# 'text_check_type' : main method to determine if text should be kept or discarded
#       options: 'font' (by font spec), 'font_size' (by font size)
# 'get_initials' : function extracting initials from line of text

def get_config(name):
    # default config:
    cfg = {
        'text_check_type': 'font_size',
        'font_whitelist' : [],
        'font_blacklist' : [],
        'get_initials' : get_initials,
        'xml_manipulation' : lambda xml: xml,
        'line_manipulation' : lambda line: line,
    }

    cfg.update(files[name]['cfg'])
    return files[name]['path'], cfg
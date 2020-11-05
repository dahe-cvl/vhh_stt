import os
import numpy as np
import gensim
import nltk
from nltk import sent_tokenize, word_tokenize
nltk.download('punkt')
from difflib import ndiff, HtmlDiff
from scipy.spatial.distance import cosine
from collections import Counter
from itertools import product
import json
import pickle

def get_html_diff(textA, textB):
    textA = remove_punctuation(textA).split()
    textB = remove_punctuation(textB).split()
    html_diff = HtmlDiff().make_file(textA, textB)
    return html_diff

def remove_punctuation(text):
    punctuation_symbols = r'!"#$%&()*+,-./:;<=>?¿@[\]^_`{|}~'
    return text.translate((str.maketrans('', '', punctuation_symbols)))

def dictionaries_to_vectors(dictA, dictB):
    tmp = dictA.copy()
    tmp.update(dictB)
    keys = tmp.keys()

    vectorA = np.array([dictA[key] if key in dictA else 0.0 for key in keys])
    vectorB = np.array([dictB[key] if key in dictB else 0.0 for key in keys])
    return vectorA, vectorB

def tf_vectors(textA, textB):
    def get_score_dict(text):
        word_tokens = word_tokenize(text)
        tf_counter = Counter(word_tokens)
        return dict(tf_counter)

    dictA = get_score_dict(textA)
    dictB = get_score_dict(textB)

    return dictionaries_to_vectors(dictA, dictB)

def tf_idf_vectors(textA, textB):
    def get_score_dict(text):
        sent_tokens = sent_tokenize(text)
        sent_word_tokens = [[word.lower() for word in word_tokenize(sent)] for sent in sent_tokens]

        dictionary = gensim.corpora.Dictionary(sent_word_tokens)
        # print(dictionary.token2id)
        corpus = [dictionary.doc2bow(word_tokens) for word_tokens in sent_word_tokens]

        tf_idf = gensim.models.TfidfModel(corpus)
        scores = {}
        for doc in tf_idf[corpus]:
            for id, freq in doc:
                scores[dictionary[id]] = freq
        return scores

    dictA = get_score_dict(textA)
    dictB = get_score_dict(textB)

    return dictionaries_to_vectors(dictA, dictB)

def cosine_similarity(textA, textB, embedding):
    vectorA, vectorB = embedding(textA, textB)
    return 1 - cosine(vectorA, vectorB)

def word_error_rate(textA, textB):
    textA = remove_punctuation(textA).split()
    textB = remove_punctuation(textB).split()
    diff = list(ndiff(textA, textB))

    insertions = 0
    deletions = 0
    substitutions = 0
    matching = 0

    current_plus = 0
    current_minus = 0
    for entry in diff:
        if entry[0] not in ['+', '-']:
            substitutions += min(current_plus, current_minus)
            insertions += max(current_plus - current_minus, 0)
            deletions += max(current_minus - current_plus, 0)
            current_plus, current_minus = 0, 0

        if entry[0] == ' ':
            matching += 1
        elif entry[0] == '+':
            current_plus += 1
        elif entry[0] == '-':
            current_minus += 1

    substitutions += min(current_plus, current_minus)
    insertions += max(current_plus - current_minus, 0)
    deletions += max(current_minus - current_plus, 0)

    wer = (insertions + deletions + substitutions) / len(textA)

    # number pairs should match if calculations works correctly
    # print(len(textA), matching + substitutions + deletions)
    # print(len(textB), matching + substitutions + insertions)
    return wer

def synchronize_ends(textA, textB, lb=0.05, ub=0.95):
    split_textA = remove_punctuation(textA).split()
    split_textB = remove_punctuation(textB).split()
    diff = list(ndiff(split_textA, split_textB))

    indices_matching = []
    indicesA = {}
    indicesB = {}
    # find out how matching pairs are distributed and where words of the individual texts are located in the diffs
    for i, entry in enumerate(diff):
        if entry[0] == ' ':
            indices_matching.append(i)
        if entry[0] in [' ', '-']:
            indicesA[i] = len(indicesA)
        if entry[0] in [' ', '+']:
            indicesB[i] = len(indicesB)

    first_index = indices_matching[int(len(indices_matching) * lb)]
    last_index = indices_matching[int(len(indices_matching) * ub)]

    # trimming punctuated text
    textA_interval = slice(indicesA[first_index], indicesA[last_index])
    wordsA = textA.split()
    trimmed_wordsA = wordsA[textA_interval]

    textB_interval = slice(indicesB[first_index], indicesB[last_index])
    wordsB = textB.split()
    trimmed_wordsB = wordsB[textB_interval]

    reduction = lambda words, trimmed_words: int(100*(1-len(trimmed_words)/len(words)))
    print('trimming textA by %d%% and textB by %d%%' % (reduction(wordsA, trimmed_wordsA), reduction(wordsB, trimmed_wordsB)))

    return ' '.join(trimmed_wordsA), ' '.join(trimmed_wordsB)

def evaluate(identifier, service, generate_diff=True, print_scores=True):
    text_transcript_path = os.path.join('text_transcripts', identifier + '_punctuated.txt')
    audio_transcript_path = os.path.join('audio_transcripts', identifier + '_' + service, 'transcribed_text.txt')

    if not os.path.exists(text_transcript_path) or not os.path.exists(audio_transcript_path):
        return None

    textA = open(text_transcript_path, 'r').read().lower()
    textB = open(audio_transcript_path, 'r').read().lower()

    textA, textB = synchronize_ends(textA, textB)

    scores = {
        'tf' : cosine_similarity(textA, textB, tf_vectors),
        'tf_idf' : cosine_similarity(textA, textB, tf_idf_vectors),
        'wer' : word_error_rate(textA, textB),
    }

    if print_scores:
        print('tf cosine similarity:', scores['tf'])
        print('tf_idf cosine similarity:', scores['tf_idf'])
        print('word error rate:', scores['wer'])

    if generate_diff:
        diff_path = os.path.join('transcript_diffs', identifier + '_' + service + '.html')
        print(get_html_diff(textA, textB), file=open(diff_path, 'w'))

    return scores

# evaluate('OH_ZP1_031', 'google', print_scores=True, generate_diff=True)

identifiers = ['OH_ZP1_' + n for n in ['016', '031', '163', '195', '208', '214', '259', '291', '423', '625', '673', '693', '795', '817']]
services = ['google', 'azure', 'sphinx', 'amazon']

data = []
for identifier, service in product(identifiers, services):
    scores = evaluate(identifier, service, print_scores=False, generate_diff=False)
    print(service, identifier, scores)
    data.append((identifier, service, scores))

# json.dump(data, open('scores.json', 'w'))
pickle.dump(data, open('scores.p', 'wb'))


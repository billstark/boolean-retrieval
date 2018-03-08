#!/usr/bin/python
import re
import nltk
import sys
import getopt
import math
import os
from config import *


def usage():
    print "usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file"


input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-i':  # input directory
        input_directory = a
    elif o == '-d':  # dictionary file
        output_file_dictionary = a
    elif o == '-p':  # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if input_directory is None or output_file_postings is None or output_file_dictionary is None:
    usage()
    sys.exit(2)

############################
# Implementation overview: #
############################

# This implementation for indexing is not efficient at all.

# It does the following things:
# 1. read through all the training files and for each file, tokenize it and form terms
#   1.1. using word_tokenize to get words first, then use nltk stemmer
#       to stem the words. After that, fold the word to lower case
#   1.2. stores a [word, index (doc_id)] pair into a `temp_list`
#   Note: may have improvement since reading all files is not efficient
# 2. sort the `temp_list` by doc_id
# 3. sort the `temp_list` by word
#   Note: after this step the `temp_list` will be ordered by word in alphabetical order
#       and for each word, they will be ordered by doc_id
# 4. zips the `temp_list` into a dictionary that is of the following format (`processed_list`)
#       {
#           'word': { 'posting': [doc_id, doc_id, doc_id] }
#       }
#   Note: at the same time, keep a `word_list` that is used to keep word ordering
# 5. creates the posting. With the order in `word_list`, stores the posing in the following
#   format: "doc_id:next_index doc_id:next_index doc_id:next_index"
#   Note: next_id is used for skip pointers. we could later read each line and store them into
#       [[doc_id, next_index], [doc_id, next_index], ...], then next_index will give a skip
#       pointer to the "next" array element. For non-skipping ones, next_index is just current
#       index + 1
#   Note: at the same time, get the line length and keep an offset for the use of seek()
#       store the offset into the dictionary and the format of `processed_list` becomes
#       {
#           'word': { 'posting': [doc_id, doc_id, ...], 'offset': offset }    
#       }
# 6. stores the dictionary with the following format:
#       "word offset count"

# create stemmer object
ps = nltk.stem.PorterStemmer()

# words is a set of (word, document_id)
words = set()
all_doc_ids = []
dictionary_file = open(output_file_dictionary, 'w')
posting_file = open(output_file_postings, 'w')

# for each file, try to read it
for doc_id in os.listdir(input_directory):
    with open(os.path.join(input_directory, doc_id)) as input_file:
        for word in nltk.word_tokenize(input_file.read()):
            # Remove invalid characters (punctuations, special characters, etc.)
            word = re.sub(INVALID_CHARS, "", word)

            if not word:
                continue

            # Stem and lowercase the word
            word = ps.stem(word.lower())
            words.add((word, doc_id))

        all_doc_ids.append(doc_id)

# sorts the temp dictionary by document ID, then by word
words = sorted(words, key=lambda t: t[1])
words = sorted(words, key=lambda t: t[0])

# create a dictionary and a word list to keep sequence
processed_list = {}
word_list = []

for word, doc_id in words:
    if word not in processed_list:
        word_list.append(word)
        processed_list[word] = {
            'posting': [doc_id]
        }
    else:
        processed_list[word]['posting'].append(doc_id)


def get_posting_string(posting):
    # Calculates the number of index per skip
    skip = int(math.sqrt(len(posting)))

    # Keep track of the next skip pointer index
    next_index = 0
    postings = []

    for index, doc_id in enumerate(posting):
        # If the current index is the next index, we reach a skip point
        if index == next_index and index != len(posting) - 1:
            # If the next skip point exceeds the total length, just let the next_index to be the last index
            if index + skip >= len(posting):
                next_index = len(posting) - 1
            else:
                next_index = index + skip

            postings.append("{}:{}".format(doc_id, next_index))
        else:
            postings.append(str(doc_id))

    return " ".join(postings) + "\n"


# formating posting
offset = 0
for word in word_list:
    posting = processed_list[word]['posting']
    posting_list = get_posting_string(posting)
    processed_list[word]['offset'] = offset
    offset = offset + len(posting_list)

    # writes into posting
    posting_file.write(posting_list)

# This is to add all postings (a posting of all existing doc ids)
posting_file.write(get_posting_string(all_doc_ids))
posting_file.close()

# writes into dictionary
# add this offset for the last posting (all postings)
dictionary_file.write(str(offset) + "\n")
for word in word_list:
    dictionary_file.write("{} {} {}\n".format(word, processed_list[word]['offset'], len(processed_list[word]['posting'])))

dictionary_file.close()

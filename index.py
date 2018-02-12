#!/usr/bin/python
import re
import nltk
import sys
import getopt
import math

def usage():
    print "usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file"

input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)
    
for o, a in opts:
    if o == '-i': # input directory
        input_directory = a
    elif o == '-d': # dictionary file
        output_file_dictionary = a
    elif o == '-p': # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"
        
if input_directory == None or output_file_postings == None or output_file_dictionary == None:
    usage()
    sys.exit(2)

############################
# Implementation overview: #
############################

# This implementation for indexing is not efficient at all.

# It does the following things:
# 1. read through all the training files and for each file, tokenize it and form terms
#   1.1. using nltk sent_tokenize and word_tokenize to get words first, then use nltk stemmer
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

# the temp list that is used to store [word, doc_id]
temp_list = []
dictionary_file = open(output_file_dictionary, 'w')
posting_file = open(output_file_postings, 'w')

# for each file, try to read it
for index in range(1, 14818):
    input_file_name = input_directory + str(index)
    print "trying to index file " + str(index) + "\n"
    try:
        input_file = open(input_file_name, 'r')
        input_file_content = input_file.read()

        for sentence in nltk.sent_tokenize(input_file_content):
            words = map(lambda word: ps.stem(word).lower(), nltk.word_tokenize(sentence))
            for word in words:
                if [word, index] in temp_list:
                    continue
                temp_list.append([word, index])

        input_file.close()
    except IOError as e:
        continue

# sorts the temp dictionary
temp_list.sort(key = lambda doc: doc[1])
temp_list.sort(key = lambda doc: doc[0])

# create a dictionary and a word list to keep sequence
processed_list = {}
word_list = []

for [word, doc_id] in temp_list:
    if word not in processed_list:
        word_list.append(word)
        processed_list[word] = {
            'posting': [doc_id]
        }
        continue
    processed_list[word]['posting'].append(doc_id)

# formating posting
offset = 0
for word in word_list:
    posting = processed_list[word]['posting']

    # calculates the skipping
    skip = int(math.sqrt(len(posting)))

    # keep track of the next index
    next_index = 0
    posting_list = ""

    for index, doc_id in enumerate(posting):

        # if the current index is the next index, we reach a skip point
        if index == next_index:

            # if the next skip point execeeds the total length, just
            # let the next_index to be the last index
            if index + skip >= len(posting):
                posting_list = posting_list + str(doc_id) + ":" + str(len(posting) - 1) + " "
                continue

            # else, specifies the next index to be current index + skip
            next_index = next_index + skip
            posting_list = posting_list + str(doc_id) + ":" + str(next_index) + " "
            continue

        # else, not skipping point, next index is just current index + 1 (it it redundant actually)
        posting_list = posting_list + str(doc_id) + ":" + str(index + 1) + " "

    # add new line syntex, get length and add offset
    posting_list = posting_list[:len(posting_list) - 1] + "\n"
    processed_list[word]['offset'] = offset
    offset = offset + len(posting_list)

    # writes into posting
    posting_file.write(posting_list)

posting_file.close()

# writes into dictionary
for word in word_list:
    dictionary_file.write(word + " " + str(processed_list[word]['offset']) + " " + str(len(processed_list[word]['posting'])) + "\n")

dictionary_file.close()



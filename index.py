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

ps = nltk.stem.PorterStemmer()
temp_list = []
dictionary_file = open(output_file_dictionary, 'w')
posting_file = open(output_file_postings, 'w')

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

temp_list.sort(key = lambda doc: doc[1])
temp_list.sort(key = lambda doc: doc[0])

processed_list = {}
word_list = []
index = 0
for [word, doc_id] in temp_list:
    if word not in processed_list:
        word_list.append(word)
        processed_list[word] = {
            'index': index,
            'posting': [doc_id]
        }
        index = index + 1
        continue
    processed_list[word]['posting'].append(doc_id)



offset = 0
for word in word_list:
    posting = processed_list[word]['posting']
    skip = int(math.sqrt(len(posting)))
    next_index = 0
    posting_list = ""
    for index, doc_id in enumerate(posting):
        if index == next_index:
            if index + skip >= len(posting):
                posting_list = posting_list + str(doc_id) + ":" + str(len(posting) - 1) + " "
                continue
            next_index = next_index + skip
            posting_list = posting_list + str(doc_id) + ":" + str(next_index) + " "
            continue
        posting_list = posting_list + str(doc_id) + ":" + str(index + 1) + " "
    posting_list = posting_list[:len(posting_list) - 1] + "\n"
    processed_list[word]['offset'] = offset
    offset = offset + len(posting_list)
    posting_file.write(posting_list)

posting_file.close()

for word in word_list:
    dictionary_file.write(word + " " + str(processed_list[word]['offset']) + " " + str(len(processed_list[word]['posting'])) + "\n")

dictionary_file.close()



#!/usr/bin/python
import re
import nltk
import sys
import getopt

def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"

dictionary_file = postings_file = file_of_queries = output_file_of_results = None
	
try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file  = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file == None or postings_file == None or file_of_queries == None or file_of_output == None :
    usage()
    sys.exit(2)

query_file = open(file_of_queries)
output_file = open(file_of_output, 'w')
dictionary_file = open(dictionary_file)
postings_file = open(postings_file)

ps = nltk.stem.PorterStemmer()

dictionary = {}
total_count = 0
for line in dictionary_file:
    total_count = total_count + 1
    data_array = line.split()
    dictionary[data_array[0]] = [data_array[1], data_array[2]]


def get_posting(word):


for line in query_file:

    # TODO: parse query
    query = line





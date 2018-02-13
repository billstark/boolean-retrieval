#!/usr/bin/python
import re
import nltk
import math
import sys
import getopt

def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"

def create_term(token):
    return ps.stem(token).lower()

def parse_postings(offset):
    postings_file.seek(offset)
    postings_string = postings_file.readline()
    postings = map(lambda item: 
        map(lambda num_string: int(num_string), item.split(":")), 
        postings_string.split())
    return postings

def get_posting(word):
    term = create_term(word)
    if term not in dictionary:
        return []
    return parse_postings(int(dictionary[term][0]))

def add_skip_pointers(temp_posting):
    skip = int(math.sqrt(len(temp_posting)))
    next_index = 0
    return_posting = []

    for index, doc_id in enumerate(temp_posting):
        if index == next_index:
            if index + skip >= len(temp_posting):
                return_posting.append([doc_id, len(temp_posting) - 1])
                continue

            next_index = next_index + skip
            return_posting.append([doc_id, next_index])
            continue
        return_posting.append([doc_id, index + 1])
    return return_posting

def and_next_index(current_index, the_other_index, current_list, the_other_list):
    if current_index >= len(current_list) - 1:
        return current_index + 1
    next_index = current_list[current_index][1]
    if next_index >= len(current_list):
        return current_index + 1
    if current_list[next_index][0] < the_other_list[the_other_index][0]:
        return next_index
    return current_index + 1

def and_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    temp_posting = []
    while (index_one < len(posting_one) and index_two < len(posting_two)):
        if posting_one[index_one][0] < posting_two[index_two][0]:
            index_one = and_next_index(index_one, index_two, posting_one, posting_two)
            continue

        if posting_two[index_two][0] < posting_one[index_one][0]:
            index_two = and_next_index(index_two, index_one, posting_two, posting_one)
            continue

        temp_posting.append(posting_one[index_one][0])
        index_one = index_one + 1
        index_two = index_two + 1
    return add_skip_pointers(temp_posting)

def or_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    temp_posting = []
    while (index_one < len(posting_one) or index_two < len(posting_two)):
        if index_one >= len(posting_one):
            temp_posting.append(posting_two[index_two][0])
            index_two = index_two + 1
            continue
        if index_two >= len(posting_two):
            temp_posting.append(posting_one[index_one][0])
            index_one = index_one + 1
            continue
        if posting_one[index_one][0] < posting_two[index_two][0]:
            temp_posting.append(posting_one[index_one][0])
            index_one = index_one + 1
            continue
        if posting_two[index_two][0] < posting_one[index_one][0]:
            temp_posting.append(posting_two[index_two][0])
            index_two = index_two + 1
            continue
        temp_posting.append(posting_one[index_one][0])
        index_one = index_one + 1
        index_two = index_two + 1
    return add_skip_pointers(temp_posting)

def and_not_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    temp_posting = []
    while (index_one < len(posting_one)):
        if index_two >= len(posting_two):
            temp_posting.append(posting_one[index_one][0])
            index_one = index_one + 1
            continue
        if posting_one[index_one][0] < posting_two[index_two][0]:
            temp_posting.append(posting_one[index_one][0])
            index_one = index_one + 1
            continue
        if posting_two[index_two][0] < posting_one[index_one][0]:
            index_two = index_two + 1
            continue
        index_one = index_one + 1
        index_two = index_two + 1
    return add_skip_pointers(temp_posting)

def not_postings(posting):
    return and_not_postings(all_posting, posting)

def break_with_keyword(query, keyword):
    breaked = query.split(" " + keyword + " ")
    parsed = []
    index = 0
    while index < len(breaked):
        if '(' not in breaked[index] and ')' not in breaked[index]:
            parsed.append(breaked[index])
            index = index + 1
            continue
        if '(' in breaked[index]:
            parenth = ""
            while ')' not in breaked[index]:
                parenth = parenth + breaked[index] + " " + keyword + " "
                index = index + 1
            parenth = parenth + breaked[index]
            if parenth[0] == '(' and parenth[len(parenth) - 1] == ')':
                parenth = parenth[1:len(parenth) - 1]
            parsed.append(parenth)
            index = index + 1
            continue
    return parsed

def parse_query(query):
    if query[0] == '(' and query[len(query) - 1] == ')':
        query = query[1:len(query) - 1]
    breaked_or = break_with_keyword(query, "OR")
    if len(breaked_or) == 1:
        breaked_and = break_with_keyword(query, "AND")
        term_postings = []
        for keyword in breaked_and:
            if "NOT" in keyword:
                keyword = keyword[4:]
                posting = parse_query(keyword)
                if len(posting) < len(all_posting) - len(posting):
                    term_postings.append([1, posting])
                    continue
                term_postings.append([0, not_postings(posting)])
            posting = get_posting(keyword)
            if len(posting) == 0:
                return []
            term_postings.append([0, posting])

        term_postings.sort(key = lambda x: len(x[1]))
        
        result_and_postings = []

        if term_postings[0][0] == 1:
            result_and_postings = not_postings(term_postings[0][1])
        else:
            result_and_postings = term_postings[0][1]

        for index in range(1, len(term_postings)):
            if term_postings[index][0] == 1:
                result_and_postings = and_not_postings(result_and_postings, term_postings[index][1])
                continue
            result_and_postings = and_postings(result_and_postings, term_postings[index][1])
        return result_and_postings

    result_or_posting = []
    for grouped_terms in breaked_or:
        result_or_posting = or_postings(result_or_posting, parse_query(grouped_terms))

    return result_or_posting

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

all_posting_offset = int(dictionary_file.readline())
all_posting = parse_postings(all_posting_offset)

ps = nltk.stem.PorterStemmer()

dictionary = {}
for line in dictionary_file:
    data_array = line.split()
    if len(data_array) != 3:
        continue
    dictionary[data_array[0]] = [data_array[1], data_array[2]]


# for line in query_file:

#     # TODO: parse query
#     query = line

# print and_postings(get_posting("Nicaragua"), get_posting("Representatives"))
# print and_postings(get_posting("Nicaragua"), get_posting("Nicaragua"))
# print or_postings(get_posting("Dauster"), get_posting("Dauster"))
print len(parse_query("bill OR Gates AND (vista OR XP) AND NOT mac"))
print len(or_postings(get_posting("bill"), and_postings(or_postings(get_posting("vista"), get_posting("XP")), and_postings(get_posting("Gates"), not_postings(get_posting("mac"))))))
# print or_postings(get_posting("Dauster"), get_posting("Nicaragua"))
# print len(all_posting)
# print len(not_postings(get_posting("Dauster")))
# print all_posting
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


# Finds the posting from a given offset.
# returns the posting in the form of [[docId, position], [docId, position], ...]
# The position here refers to the index of the next element (skip pointers included).
def parse_postings(offset):
    postings_file.seek(offset)
    postings_string = postings_file.readline()
    postings = map(lambda item:
                   map(lambda num_string: int(num_string), item.split(":")),
                   postings_string.split())
    return postings


# returns the posting according to a specific word.
# returns the posting in the form of [[docId, position], [docId, position], ...]
# The position here refers to the index of the next element (skip pointers included).
def get_posting(word):
    term = create_term(word)
    if term not in dictionary:
        return []
    return parse_postings(int(dictionary[term][0]))


# Adds skip pointers to a posting with the form [docId, docId, ...]
# This would be useful when we are dealing with merging.
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


# Gets the next index of a specified posting list in AND operation.
# e.g. we are operating on 1, 2, 3, 4 and
#                          2, 3, 5, 6
# suppose current index is 0 and the other index is 3, we could move the current
# index to 2 due to the skip pointer.
def and_next_index(current_index, the_other_index, current_list, the_other_list):
    if current_index >= len(current_list) - 1:
        return current_index + 1
    next_index = current_list[current_index][1]
    if next_index >= len(current_list):
        return current_index + 1
    if current_list[next_index][0] < the_other_list[the_other_index][0]:
        return next_index
    return current_index + 1


# Given two postings of the form [[docId, pointer], [docId, pointer], ...]
# returns a posting that is the result of and "AND" operation
# return format: [[docId, pointer], [docId, pointer], ...]
def and_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    temp_posting = []
    while index_one < len(posting_one) and index_two < len(posting_two):
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


# similar to "AND" operation.
def or_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    temp_posting = []
    while index_one < len(posting_one) or index_two < len(posting_two):
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


# defines and_not operation
def and_not_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    temp_posting = []
    while index_one < len(posting_one):
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


# defines not operation
def not_postings(posting):
    return and_not_postings(all_posting, posting)


# breaks the query according to the "AND", "OR" or "NOT" keyword.
# input is a string of unparsed query
# output is an array of breaked subquerys at the same level.
# Note: This method is intended to solve the following case:
# query: C OR (A OR B). We perhaps need to break the query to 
# C and (A OR B) first.
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


# Parses the query.
def parse_query(query):
    # at first, if it is wrapped with only one bracket, remove it.
    if query[0] == '(' and query[len(query) - 1] == ')' and query.count('(') == 1 and query.count(')') == 1:
        query = query[1:len(query) - 1]

    # break with "OR" first, since OR is processed at last.
    breaked_or = break_with_keyword(query, "OR")

    # if nothing is breaked, which means that there is no OR operation, then we consider AND
    if len(breaked_or) == 1:

        # break with AND
        breaked_and = break_with_keyword(query, "AND")

        # NOTE: there is a flag, it: [[0 or 1, posting], [0 or 1, posting], ...]
        # when the flag is set to 1, remember to toggle the posting when doing the 
        # outer AND (I am using the flag because if the original posting is very large, 
        # we can toggle it first and do NOT first, otherwise we should do "AND NOT")
        term_postings = []

        # for each keyword in the breaked and
        for keyword in breaked_and:

            # if there is not and not is not included in the bracket, parse it as NOT something.
            if "NOT" in keyword and not (keyword[0] == '(' and keyword[len(keyword) - 1] == ')'):
                keyword = keyword[4:]
                posting = parse_query(keyword)
                if len(posting) < len(all_posting) - len(posting):
                    term_postings.append([1, posting])
                    continue
                term_postings.append([0, not_postings(posting)])
                continue

            # if there is bracket, pass it to parse query.
            if " " in keyword:
                term_postings.append([0, parse_query(keyword)])
                continue

            # else, there is only single-word left. get the posting of it
            posting = get_posting(keyword)
            if len(posting) == 0:
                return []
            term_postings.append([0, posting])

        # sort all postings by length first
        term_postings.sort(key=lambda x: len(x[1]))

        result_and_postings = []

        # check the first posting (see whether we need to toggle)
        if term_postings[0][0] == 1:
            result_and_postings = not_postings(term_postings[0][1])
        else:
            result_and_postings = term_postings[0][1]

        # then operate AND on all the sub querys.
        for index in range(1, len(term_postings)):
            if term_postings[index][0] == 1:
                result_and_postings = and_not_postings(result_and_postings, term_postings[index][1])
                continue
            result_and_postings = and_postings(result_and_postings, term_postings[index][1])
        return result_and_postings

    # else, which means that there are more than one sub queries for OR
    # we process it one by one.
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
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file is None or postings_file is None or file_of_queries is None or file_of_output is None:
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

for line in query_file:
    if "\n" in line:
        line = line[0:len(line) - 1]
    temp_result = parse_query(line)
    temp_result = map(lambda item: str(item[0]), temp_result)

    if len(temp_result) == 0:
        output_file.write("\n")
        continue
    result_string = " ".join(temp_result)
    output_file.write(result_string + "\n")

#!/usr/bin/python
import re
import nltk
import math
import sys
import getopt
from config import *


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


def create_term(token):
    return ps.stem(token).lower()


# AST nodes
class Node:
    def __init__(self):
        self.children = []

    def count(self):
        raise NotImplementedError()

    def add_child(self, child):
        self.children.append(child)


class KeywordNode(Node):
    def __init__(self, term, postings=None):
        Node.__init__(self)
        self.term = term
        self._children = postings

    @property
    def children(self):
        # Keyword node children are lazy loaded
        if self._children is None:
            self._children = get_posting(self.term)
        return self._children

    def count(self):
        return len(self.children)

    def __repr__(self):
        return "(%s, %s)" % (self.term, self.count())


class OperatorNode(Node):
    def collapsible(self):
        return all(map(lambda node: isinstance(node, KeywordNode), self.children))

    def smallest_collapsible_child(self):
        """Find the operator node in the """
        if self.collapsible():
            return self, self.count()

        operator_children = filter(lambda node: isinstance(node, OperatorNode), self.children)
        return min(map(lambda node: node.smallest_collapsible_child(), operator_children), key=lambda t: t[1])


class AndNode(OperatorNode):
    def add_child(self, child):
        # Flatten AND node
        if isinstance(child, AndNode):
            for subchild in child.children:
                self.add_child(subchild)
        else:
            Node.add_child(self, child)

    def count(self):
        return min(self.children, key=lambda n: n.count())

    def next_index(self, current_index, other_index, current_list, the_other_list):
        if current_index >= len(current_list) - 1:
            return current_index + 1
        next_index = current_list[current_index][1]
        if next_index >= len(current_list):
            return current_index + 1
        if current_list[next_index][0] < the_other_list[other_index][0]:
            return next_index
        return current_index + 1


class OrNode(OperatorNode):
    def add_child(self, child):
        # Flatten OR node
        if isinstance(child, OrNode):
            for subchild in child.children:
                self.add_child(subchild)
        else:
            Node.add_child(self, child)

    def count(self):
        return sum(child.count() for child in self.children)


class NotNode(OperatorNode):
    def __init__(self, all_postings):
        Node.__init__(self)
        self.all_postings = all_postings

    def add_child(self, child):
        if self.children:
            raise ValueError("NotNode already has child")

        Node.add_child(self, child)

    def count(self):
        return len(self.all_postings) - self.children[0].count()


# Finds the posting from a given offset.
# returns the posting in the form of [[doc_id, position], [doc_id, position], ...]
# The position here refers to the index of the next element (skip pointers included).
def parse_postings(offset):
    postings_file.seek(offset)
    postings_string = postings_file.readline()
    postings = map(lambda item:
                   map(lambda num_string: int(num_string), item.split(":")),
                   postings_string.split())
    return postings


# returns the posting according to a specific word.
# returns the posting in the form of [[doc_id, position], [doc_id, position], ...]
# The position here refers to the index of the next element (skip pointers included).
def get_posting(word):
    term = create_term(word)
    if term not in dictionary:
        return []
    return parse_postings(int(dictionary[term][0]))


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


# Given two postings of the form [[doc_id, pointer], [doc_id, pointer], ...]
# returns a posting that is the result of and "AND" operation
# return format: [[doc_id, pointer], [doc_id, pointer], ...]
def and_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    results = []
    while index_one < len(posting_one) and index_two < len(posting_two):
        if posting_one[index_one][0] < posting_two[index_two][0]:
            index_one = and_next_index(index_one, index_two, posting_one, posting_two)
        elif posting_two[index_two][0] < posting_one[index_one][0]:
            index_two = and_next_index(index_two, index_one, posting_two, posting_one)
        else:
            results.append(posting_one[index_one][0])
            index_one = index_one + 1
            index_two = index_two + 1
    return results


# similar to "AND" operation.
def or_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    results = []
    while index_one < len(posting_one) or index_two < len(posting_two):
        if index_one >= len(posting_one):
            results.append(posting_two[index_two][0])
            index_two += 1
        elif index_two >= len(posting_two):
            results.append(posting_one[index_one][0])
            index_one += 1
        elif posting_one[index_one][0] < posting_two[index_two][0]:
            results.append(posting_one[index_one][0])
            index_one += 1
        elif posting_two[index_two][0] < posting_one[index_one][0]:
            results.append(posting_two[index_two][0])
            index_two += 1
        else:
            results.append(posting_one[index_one][0])
            index_one += 1
            index_two += 1
    return results


# defines and_not operation
def and_not_postings(posting_one, posting_two):
    index_one = 0
    index_two = 0
    results = []
    while index_one < len(posting_one):
        if index_two >= len(posting_two) or posting_one[index_one][0] < posting_two[index_two][0]:
            results.append(posting_one[index_one][0])
            index_one += 1
        elif posting_two[index_two][0] < posting_one[index_one][0]:
            index_two += 1
        else:
            index_one += 1
            index_two += 1
    return results


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


def tokenize_query(query):
    """Remove all invalid characters and return query as a list of keyword and operator tokens"""
    # Remove invalid chars
    query = re.sub(INVALID_QUERY_CHARS, ' ', query)
    # Add a whitespace around each ( and ) chars to aid tokenization
    query = re.sub(r'([()])', r' \1 ', query)
    # Trim whitespace
    query = query.strip()

    return re.split(r'\s+', query)


def parse_query(query):
    tokens = tokenize_query(query)
    tokens.reverse()

    # Shunting-yard algorithm https://en.wikipedia.org/wiki/Shunting-yard_algorithm
    stack = []
    output = []

    while tokens:
        token = tokens.pop()
        # Keyword
        if token not in OPERATORS:
            output.append(token.lower())
        # Open parenthesis
        elif token == '(':
            stack.append(token)
        # Close parenthesis
        elif token == ')':
            # Slice [:-1] to drop the matching parenthesis
            operator = stack.pop()
            while operator != '(':
                output.append(operator)
                operator = stack.pop()
        # All other operators
        else:
            precedence = OPERATORS[token]

            while stack:
                # Pop operators until...
                operator = stack[-1]

                # ...we find an opening parenthesis, an operator with lower precedence,
                # or if we're parsing an unary operator, a binary operator
                if operator == '(' \
                        or (token in UNARY_OPERATORS and operator not in UNARY_OPERATORS) \
                        or OPERATORS[operator] <= precedence:
                    break

                output.append(stack.pop())

            stack.append(token)

    # Append leftover operations
    output.extend(reversed(stack))

    return output


def build_ast(query_terms):
    # Preprocess queries by replacing all keywords with keyword nodes
    terms = []
    for term in query_terms:
        if term == 'AND':
            terms.append(AndNode())
        elif term == 'OR':
            terms.append(OrNode())
        elif term == 'NOT':
            terms.append(NotNode(all_posting))
        else:
            terms.append(KeywordNode(term, get_posting(term)))

    stack = []
    for term in terms:
        # Handle operators
        if not isinstance(term, KeywordNode):
            if isinstance(term, NotNode):
                term.add_child(stack.pop())
            else:
                term.add_child(stack.pop())
                term.add_child(stack.pop())

        # Push back into stack
        stack.append(term)

    assert len(stack) == 1
    return stack[0]


def optimize_ast(tree):
    if isinstance(tree, KeywordNode):
        return tree

    # Remove NOT-NOT operations
    if isinstance(tree, NotNode) and isinstance(tree.children[0], NotNode):
        return optimize_ast(tree.children[0].children[0])

    # Use De Morgan's law to change (NOT a OR NOT b) into NOT (a AND b)
    if isinstance(tree, OrNode) and all(map(lambda node: isinstance(node, NotNode), tree.children)):
        not_node = NotNode(all_posting)
        and_node = AndNode()

        not_node.add_child(and_node)

        for child in tree.children:
            and_node.add_child(optimize_ast(child.children[0]))
        return not_node

    tree.children = map(optimize_ast, tree.children)
    return tree


def run_query(query):
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
    try:
        term, offset, frequency = line.split()
        dictionary[term] = [offset, frequency]
    except ValueError:
        pass

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

#!/usr/bin/python
import re
import nltk
import math
import sys
import getopt
from config import *
from operator import attrgetter, methodcaller


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


def create_term(token):
    return ps.stem(token).lower()


def parse_postings(offset):
    """
    Returns the posting and skip pointers from a given offset in the postings file.
    Posting is returned as a list of document IDs, and skip pointer as a dictionary of index to index"""
    postings_file.seek(offset)
    postings_string = postings_file.readline()
    postings = []
    skip_pointers = {}

    for index, posting in enumerate(postings_string.split()):
        # Postings may come with a skip pointer, eg. 123:12 where 123 is the usual docId, and 12 is a pointer
        # to the 12th item in the list.
        parsed_posting = posting.split(':')

        if len(parsed_posting) == 2:
            skip_pointers[index] = int(parsed_posting[1])

        postings.append(int(parsed_posting[0]))

    return postings, skip_pointers


def get_posting(word):
    """Return the posting and skip pointers for a specific word."""
    term = create_term(word)
    if term not in dictionary:
        return [], {}
    return parse_postings(int(dictionary[term][0]))


# Gets the next index of a specified posting list in AND operation.
# e.g. we are operating on 1, 2, 3, 4 and
#                          2, 3, 5, 6
# suppose current index is 0 and the other index is 3, we could move the current
# index to 2 due to the skip pointer.
def and_next_index(index, postings, other_id, skip_pointers):
    if index in skip_pointers and postings[skip_pointers[index]] <= other_id:
        while index in skip_pointers and postings[skip_pointers[index]] <= other_id:
            index = skip_pointers[index]
        return index

    return index + 1


def and_postings(posting_one, posting_two, skip_pointers_one, skip_pointers_two):
    """
    Returns the result of an AND (intersection) operation
    ie. all posting in posting_one that match a posting in posting_two

    Skip pointers can be provided to speed up the operation.
    """
    index_one = 0
    index_two = 0
    results = []

    while index_one < len(posting_one) and index_two < len(posting_two):
        if posting_one[index_one] < posting_two[index_two]:
            index_one = and_next_index(index_one, posting_one, posting_two[index_two], skip_pointers_one)
        elif posting_two[index_two] < posting_one[index_one]:
            index_two = and_next_index(index_two, posting_two, posting_one[index_one], skip_pointers_two)
        else:
            results.append(posting_one[index_one])
            index_one = index_one + 1
            index_two = index_two + 1

    return results


def or_postings(posting_one, posting_two):
    """
    Returns the result of an OR operation (union)
    ie. merge posting_one and posting_two without duplicates
    """
    index_one = 0
    index_two = 0
    results = []

    while index_one < len(posting_one) and index_two < len(posting_two):
        if posting_one[index_one] < posting_two[index_two]:
            results.append(posting_one[index_one])
            index_one += 1
        elif posting_two[index_two] < posting_one[index_one]:
            results.append(posting_two[index_two])
            index_two += 1
        else:
            results.append(posting_one[index_one])
            index_one += 1
            index_two += 1

    # Add in the leftover results
    results.extend(posting_one[index_one:])
    results.extend(posting_two[index_two:])

    return results


def and_not_postings(posting_one, posting_two):
    """
    Returns the result of an AND NOT (difference) operation
    ie. all postings in posting_one excluding those in posting_two
    """
    index_one = 0
    index_two = 0
    results = []

    while index_one < len(posting_one):
        if index_two >= len(posting_two) or posting_one[index_one] < posting_two[index_two]:
            results.append(posting_one[index_one])
            index_one += 1
        elif posting_two[index_two] < posting_one[index_one]:
            index_two += 1
        else:
            index_one += 1
            index_two += 1

    return results


# Return the result of a NOT operation
# ie. all postings that is not in posting
def not_postings(posting):
    return and_not_postings(all_posting, posting)


# AST nodes used for parsing and execution of boolean logic
class Node:
    """Abstract base class used for all nodes"""
    def __init__(self):
        self.children = []

    def count(self):
        raise NotImplementedError()

    def add_child(self, child):
        self.children.append(child)

    def collapse(self):
        """Collapse this node into a KeywordNode by executing the operation recursively"""
        raise NotImplementedError()


class KeywordNode(Node):
    """Represents a computed term with postings"""
    def __init__(self, term, postings=None, skip_pointers=None):
        Node.__init__(self)
        self.term = term
        self._postings = postings

        if skip_pointers is None:
            self.skip_pointers = {}
        else:
            self.skip_pointers = skip_pointers

    @property
    def postings(self):
        # Keyword node children are lazy loaded
        if self._postings is None:
            self._postings, self.skip_pointers = get_posting(self.term)
        return self._postings

    def count(self):
        return len(self.postings)

    def collapse(self):
        return self

    def __repr__(self):
        # For debugging
        return "(%s, %s)" % (self.term, self.count())


class OperatorNode(Node):
    pass


class NotNode(OperatorNode):
    def __init__(self):
        Node.__init__(self)

    @property
    def child(self):
        return self.children[0]

    def add_child(self, child):
        if self.children:
            raise ValueError("NotNode already has child")

        Node.add_child(self, child)

    def count(self):
        return len(all_posting) - self.child.count()

    def collapse(self):
        child = self.child.collapse()
        term = 'NOT %s' % child.term
        return KeywordNode(term, and_not_postings(all_posting, child.postings))


class AndNode(OperatorNode):
    def add_child(self, child):
        # Flatten AND node
        if isinstance(child, AndNode):
            for subchild in child.children:
                self.add_child(subchild)
        else:
            Node.add_child(self, child)

    def count(self):
        return min(self.children, key=methodcaller('count'))

    def collapse(self):
        terms = []

        # Start with the child that has the smallest number of postings
        first_node = min(self.children, key=methodcaller('count'))
        self.children.remove(first_node)

        first_node_collapsed = first_node.collapse()
        postings = first_node_collapsed.postings
        skip_pointers = first_node_collapsed.skip_pointers
        terms.append(first_node_collapsed.term)

        while self.children:
            # Find the next smallest
            next_node = min(self.children, key=self.child_count)
            self.children.remove(next_node)

            if self.can_use_and_not(next_node):
                next_node_collapsed = next_node.child.collapse()
                terms.append('NOT %s' % next_node_collapsed.term)

                postings = and_not_postings(postings, next_node_collapsed.postings)
            else:
                next_node_collapsed = next_node.collapse()
                terms.append(next_node_collapsed.term)

                postings = and_postings(postings, next_node_collapsed.postings,
                                        skip_pointers, next_node_collapsed.skip_pointers)

            skip_pointers = {}

        term = ' AND '.join(terms)
        return KeywordNode(term, postings)

    @staticmethod
    def can_use_and_not(node):
        # Check if we can use AND NOT optimization
        return isinstance(node, NotNode) and node.child.count() < node.count()

    @staticmethod
    def child_count(node):
        if AndNode.can_use_and_not(node):
            return node.child.count()
        return node.count()


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

    def collapse(self):
        children = map(lambda node: node.collapse(), self.children)
        posting = reduce(lambda posting, node: or_postings(posting, node.postings),
                         children[1:], children[0].postings)
        term = "(%s)" % ' OR '.join(map(attrgetter('term'), children))
        return KeywordNode(term, posting)


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
                #    or if we're parsing an unary operator, a binary operator
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
            terms.append(NotNode())
        else:
            postings, skip_pointers = get_posting(term)
            terms.append(KeywordNode(term, postings, skip_pointers))

    stack = []
    for term in terms:
        # Handle operators
        if isinstance(term, OperatorNode):
            # NOT is the only unary operator
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

    # Use De Morgan's law to change (NOT a OR NOT b) into NOT (a AND b), which is much cheaper
    if isinstance(tree, OrNode) and all(map(lambda node: isinstance(node, NotNode), tree.children)):
        not_node = NotNode()
        and_node = AndNode()

        for child in tree.children:
            and_node.add_child(child.child)

        not_node.add_child(optimize_ast(and_node))
        return not_node

    tree.children = map(optimize_ast, tree.children)
    return tree


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
all_posting, all_posting_skip_pointers = parse_postings(all_posting_offset)

ps = nltk.stem.PorterStemmer()

dictionary = {}
for line in dictionary_file:
    try:
        term, offset, frequency = line.split()
        dictionary[term] = [offset, frequency]
    except ValueError:
        pass

for line in query_file:
    query = parse_query(line.strip())
    ast = optimize_ast(build_ast(query))

    result = ast.collapse()
    result_string = " ".join(map(str, result.postings))
    output_file.write(result_string + "\n")

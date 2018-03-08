This is the README file for A0135817B and A0147995H's submission

Email address:
Zhang Yijiang: e0011848@u.nus.edu
Yang Zhuohan: e0012667@u.nus.edu

== Python Version ==

We're using Python Version 2.7.14 for this assignment.

== General Notes about this assignment ==

Indexing:
- Procedure:
  1. for every training file, load the whole content into the system and tokenize into words
  2. remove invalid characters of the tokenized word
  3. if the word exists (meaning, not an empty string), add it into a set with the format (term, docId)
  4. sort words accordingly and carefully merge the tuple with same term into a posting.
  5. format postings and add skip pointers.
  6. write postings into the posting file
  7. write terms into dictionary file with offset to the corresponding postings.

- Notes:
  1. we choose not to use sentence tokenizer because we are handle invalid punctuation by keeping only 
     digits, alphabets, white spaces and dashes
  2. we are using set to remove duplicated (term, id) pair
  3. sorting procedure is to sort by doc id first and then terms.
  4. the posting is in the format of: docId:pointer or docId (if there is a skip, add a digit which 
     represents the index of the "next" docId)
  5. we write a posting with all file names at the end of the posting file just for NOT operation
  6. at the first line in the dictionary file we write the offset for all postings

== Files included with this submission ==

config.py - includes regex, enums and some constants that will be used in index.py and search.py.
index.py  - indexing program that will be run to index all the training files.
search.py - searching program that will be used to execute querys in a specific file and give output.

== Statement of individual work ==

Please initial one of the following statements.

[X] I, A0135817B and A0147995H, certify that I have followed the CS 3245 Information
Retrieval class guidelines for homework assignments.  In particular, I
expressly vow that I have followed the Facebook rule in discussing
with others in doing the assignment and did not take notes (digital or
printed) from the discussions.  

[ ] I, A0000000X, did not follow the class rules regarding homework
assignment, because of the following reason:

<Please fill in>

I suggest that I should be graded as follows:

<Please fill in>

== References ==

- Shunting-yard algorithm: https://en.wikipedia.org/wiki/Shunting-yard_algorithm
- The Shunting-Yard Algorithm - Nathan Reed's coding blog: http://reedbeta.com/blog/the-shunting-yard-algorithm/
- Introduction to Information Retrieval
  - Faster postings list intersection via skip pointers
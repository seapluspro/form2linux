'''
Const.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
# replaces re.I:
IGNORE_CASE = 2
RE_UNICODE = 32
RE_TEMPLATE = 1 # template mode (disable backtracking)
RE_IGNORECASE = 2 # case insensitive
RE_LOCALE = 4 # honour system locale
RE_MULTILINE = 8 # treat target as multiline string
RE_DOTALL = 16 # treat target as a single string
RE_UNICODE = 32 # use unicode "locale"
RE_VERBOSE = 64 # ignore whitespace and comments
RE_DEBUG = 128 # debugging
RE_ASCII = 256 # use ascii "locale"

# base.Logger levels:
LEVEL_SUMMARY = 1
LEVEL_DETAIL = 2
LEVEL_LOOP = 3
LEVEL_FINE = 4
LEVEL_DEBUG = 5

'''
Text.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import json
import os.path
from Builder import Builder, CLIError, GlobalOptions
from text import JsonUtils
from base import StringUtils

class RuleSet:
    '''Stores a file and the associated rules.
    '''
    def __init__(self, filename: str):
        '''Constructor.
        @param filename: the filename
        '''
        self.filename = filename
        self.rules = []

    def addRule(self, rule: str):
        self.rules.append(rule)

class TextTool (Builder):
    def __init__(self, options: GlobalOptions):
        Builder.__init__(self, False, options)
        self._ruleSets = []

    def adaptVariables(self, form):
        '''Checks variables in a configuration file and set that if needed.
        @param form: the filename of the Json form
        '''
        self.checkAdaptVariables(form)
        for ruleSet in self._ruleSets:
            self._adaptVariables(ruleSet.filename, ruleSet.rules, False)

    def checkAdaptVariables(self, form):
        '''Checks the form of the command 'adapt-variables'.
        @param form: the file with the form
        '''
        with open(form, 'r', encoding='utf-8') as fp:
            data = fp.read()
            self._root = root = json.loads(data)
            variables = root['Variables']
            for name in variables:
                self.setVariable(name, variables[name])
            self.finishVariables()
            entries = 'Files:m Variables:m'
            JsonUtils.checkJsonMapAndRaise(root, entries, True, 'Comment:s')
            for filename in root['Files']:
                name = self.replaceVariables(filename)
                if not os.path.exists(name):
                    raise CLIError(f'missing file: {name}')
                ruleSet = RuleSet(name)
                self._ruleSets.append(ruleSet)
                rules = JsonUtils.nodeOfJsonTree(root, f'Files {filename}', 'a')
                for node in rules:
                    JsonUtils.checkJsonNodeType('s', node)
                self.checkRules(rules, name, ruleSet.rules)

    def exampleAdaptVariables(self, filename: str):
        '''Shows the example for the configuration of the command "adapt-variables".
        @param filename: None or the file to store
        '''
        self._example(filename, r'''{
  "Variables": {
    "VERSION": "8.2"
  },
  "Comment": "Rules: 'VARIABLE|VALUE' or 'VARIABLE|VALUE|ANCHOR_IF_NOT_FOUND'",
  "Files": {
    "/etc/php/%(VERSION)/fpm/php.ini": [
      "memory_limit|2048M",
      "upload_max_filesize|512M",
      "max_file_uploads|100",
      "post_max_size|512M",
      "max_execution_time|600",
      "max_input_time|600",
      "default_socket_timeout|600",
      "session.save_handler|redis|^\\[Session\\]",
      "session.save_path|\"tcp://127.0.0.1:6379\"|^session.save_handler",
      "opcache.enable|1|^\\[opcache\\]",
      "opcache.memory_consumption|1024|opcache.enable",
      "opcache.interned_strings_buffer|512|^opcache.memory_consumption"
    ],
    "/etc/php/%(VERSION)/cli/php.ini": [
      "memory_limit|2048M",
      "upload_max_filesize|512M",
      "max_file_uploads|100",
      "post_max_size|512M",
      "max_execution_time|600",
      "max_input_time|600",
      "default_socket_timeout|600"
    ]
  }
}
''')

    def replaceRange(self, document: str, replacement: str, fileReplacement: str, 
                     anchor: str, start: str, end: str, 
                     insertionPosition: str, insertion: str,
                     minLength, newline: bool):
        '''Replaces a value in a configuration if needed.
        @param document: the document to change
        @param replacement: None or the replacement string
        @param replacementFile: None or a file with the replacement. 
            Exclusive to <em>replacement</em>
        @param anchor: None or a regular expression where the search of the start begins
        @param start: a regular expression in front of the value to change
        @param end: a regular expression behind the value to change
        @param insertionPosition: None or a regular expression for insertion, if the start is not found
        @param insertion: the string to insert if the start is not found
        @param minLength: the replacement must have at least that length
        @param newline: <em>True</em>: the replacement string is completed with a newline 
        '''
        if replacement is None and fileReplacement is None:
            raise CLIError('missing --replacement or --file')
        if replacement is not None and fileReplacement is not None:
            raise CLIError('only one option is allowed: --replacement or --file')
        if fileReplacement is not None:
            replacement = StringUtils.fromFile(fileReplacement)
        else:
            if newline:
                replacement += '\n'
        if minLength is not None and len(replacement) < minLength:
            raise CLIError(f'replacement is too small: {len(replacement)} / {minLength}')
        try:
            regexAnchor = None if anchor is None or anchor == '' else re.compile(anchor)
        except Exception as exc:
            self.error(f'error in anchor regular expression: {exc}')
        if start is None or start == '':
            raise CLIError('start must not be empty')
        try:
            regexStart = re.compile(start)
        except Exception as exc:
            self.error(f'error in start regular expression: {exc}')
        if end is None or end == '':
            raise CLIError('end must not be empty')
        try:
            regexEnd = re.compile(end)
        except Exception as exc:
            self.error(f'error in end regular expression: {exc}')
        with open(document, "r") as fp:
            topOfDocument = ''
            tailOfDocument = ''
            oldRange = ''
            state = 'anchor' if regexAnchor is None else 'top'
            for line in fp:
                if state == 'top':
                    topOfDocument += line
                    if regexAnchor.search(line) is not None:
                        state = 'anchor'
                elif state == 'anchor':
                    match = regexStart.search(line)
                    if match is None:
                        topOfDocument += line
                    else:
                        endPos = match.end(0)
                        topOfDocument += line[0:endPos]
                        oldRange = '' if len(line) == endPos else line[endPos:]
                        if oldRange == '\n':
                            oldRange = ''
                            topOfDocument += '\n'
                        match = regexEnd.search(oldRange)
                        if match is None:
                            state = 'range'
                        else:
                            pos = match.start(0)
                            if pos == 0:
                                tailOfDocument = oldRange
                                oldRange = ''
                            else:
                                tailOfDocument = oldRange[pos:]
                                oldRange = oldRange[0:pos]
                            state = 'tail'
                elif state == 'range':
                    match = regexEnd.search(line)
                    if match is None:
                        oldRange += line
                    else:
                        if match.pos > 0:
                            oldRange += line[0:match.pos]
                        tailOfDocument = line[match.pos:]
                        state = 'tail'
                else:
                    tailOfDocument += line
            if state in ('anchor', 'top') and insertionPosition is not None:
                topOfDocument = self.insert(topOfDocument, insertionPosition, insertion)
                replacement = tailOfDocument = None
            else:
                if state == 'top':
                    raise CLIError(f'missing anchor: {anchor}')
                if state == 'anchor':
                    raise CLIError(f'missing start "{start}')
                if state == 'range':
                    raise CLIError(f'missing end "{end}')
        if oldRange == replacement:
            self.info(f'{document}: new and old content are equal. Nothing changed.')
        else:
            with open(document, "w") as fp:
                fp.write(topOfDocument)
                if replacement is not None:
                    fp.write(replacement)
                    fp.write(tailOfDocument)
                    oldCount = oldRange.count('\n')
                    newCount = replacement.count('\n')
                    if oldCount == 1 and newCount == 1:
                        self.info(f'{document}: {len(oldRange)} characters have been replaced by {len(replacement)} characters')
                    else:
                        self.info(f'{document}: {oldCount} lines have been replaced by {newCount} lines')

    def insert(self, contents: str, insertionPosition: str, insertion: str):
        '''Makes an insertion because the value is not found.
        @param contents: the file contents
        @param insertionPosition: None or a regular expression for insertion, if the start is not found
        @param insertion: the string to insert if the start is not found
        @param return the contents with inserted value
        '''
        rc = None
        lines = contents.split('\n')
        ix = -1
        regExpr = None if insertionPosition is None else re.compile(insertionPosition)
        for line in lines:
            ix += 1
            if regExpr is not None and regExpr.search(line):
                rc = '\n'.join(lines[0:ix+1])
                rest = '' if ix == len(lines) - 1 else '\n'.join(lines[ix+1:])
                rc = f"{rc}\n{insertion}\n{rest}"
                break
        if rc is None:
            rc = contents
            if not contents.endswith('\n'):
                rc += '\n'
            rc += insertion + '\n'
        return rc

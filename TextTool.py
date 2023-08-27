'''
Text.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import base.StringUtils
from Builder import Builder, CLIError, GlobalOptions

class TextTool (Builder):
    def __init__(self, options: GlobalOptions):
        Builder.__init__(self, False, options)
        
    def replaceRange(self, document: str, replacement: str, fileReplacement: str, 
                     anchor: str, start: str, end: str, minLength: int, newline: bool):
        if replacement is None and fileReplacement is None:
            raise CLIError('missing --replacement or --file')
        if replacement is not None and fileReplacement is not None:
            raise CLIError('only one option is allowed: --replacement or --file')
        if fileReplacement is not None:
            replacement = base.StringUtils.fromFile(fileReplacement)
        else:
            if newline:
                replacement += '\n'
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
                fp.write(replacement)
                fp.write(tailOfDocument)
                oldCount = oldRange.count('\n')
                newCount = replacement.count('\n')
                if oldCount == 1 and newCount == 1:
                    self.info(f'{document}: {len(oldRange)} characters have been replaced by {len(replacement)} characters')
                else:
                    self.info(f'{document}: {oldCount} lines have been replaced by {newCount} lines')
            

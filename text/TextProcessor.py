'''
TextProcessor.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import os.path
import datetime
from typing import Sequence

from base import Const
from base import StringUtils
from base import FileHelper
from base import Logger
from text import SearchRule
from text import SearchRuleList


class TextProcessor:
    '''A processor for finding/modifying text.
    '''

    def __init__(self, logger: Logger.Logger):
        self.filename = None
        self.lines = None
        self.logger = logger
        self.region = SearchRule.Region(self)
        self._cursor = SearchRule.Position(0, 0)
        self.endOfFile = SearchRule.Position(0, 0)
        self.beginOfFile = SearchRule.Position(0, 0)
        self.lastState = None
        self.hasChanged = False
        self.traceFile = None

    def cursor(self, mode: str='both'):
        '''Returns the cursor as pair (line, col), or the line or the column, depending on mode.
        @param mode: 'both', 'line' or 'col'
        @return [line, col], line or col, depending on mode
        '''
        rc = ([self._cursor.line, self._cursor.col] if mode == 'both' else
              (self._cursor.col if mode == 'col' else self._cursor.line))
        return rc

    def executeRules(self, rulesAsString: str, maxLoops: int=1) -> bool:
        '''Compiles the rules and executes them.
        @param rules: a sequence of rules given as string
        @return True: success False: error
        '''
        ruleList = SearchRuleList.SearchRuleList(self.logger)
        rc = ruleList.parseRules(rulesAsString)
        if rc:
            rc = ruleList.check()
        if rc:
            status = SearchRule.ProcessState(self.lines, self.region.startPosition, self.region.endPosition,
                                                  self._cursor, self.logger, maxLoops)
            if self.traceFile is not None:
                ruleList.startTrace(self.traceFile, True)
            ruleList.apply(status)
            self._cursor.clone(status.cursor)
            self.lastState = status
            self.hasChanged = status.hasChanged
            rc = status.success
            if self.traceFile is not None:
                ruleList.stopTrace()
        return rc

    def findLine(self, pattern: str, firstIndex: int=0, lastIndex: int=None):
        '''Search a line matching a given regular expression.
        @param pattern: the pattern to find: a string or a RegExpr instance
        @param firstIndex: the index of the first line to inspect
        @param endIndex: exclusive: the index below the last line to inspect
        @return: -1: not found otherwise: the line index 0..N-1
        '''
        rc = -1
        regExpr = re.compile(pattern) if isinstance(pattern, str) else pattern
        ixLine = firstIndex
        last = min(lastIndex, len(self.lines)
                   ) if lastIndex is not None else len(self.lines)
        while ixLine < last:
            if regExpr.search(self.lines[ixLine]):
                rc = ixLine
                break
            ixLine += 1
        return rc

    def insertOrReplace(self, key: str, line: str, anchor=None, above: bool=False):
        '''Replaces a a line or inserts it.
        Searches the key. If found the line (with the key) is replaced by line.
        If not the anchor is searched an the line is inserted at the anchor.
        @param key: a regular expression identifying the line to replace
        @param line: the line to replace or to insert
        @param anchor: None: anchor is the end of the file
            if key is not found this position is used for insertion
        @param above: True: the insertion is done above the anchor
        '''
        if isinstance(key, str):
            key = re.compile(key)
        ix = self.findLine(key)
        if ix >= 0:
            if self.lines[ix] == line:
                self.logger.log(
                    f'key found, but same content at {ix}', Const.LEVEL_DETAIL)
            else:
                if self.logger.verboseLevel() >= Const.LEVEL_DETAIL:
                    line2 = StringUtils.limitLength2(self.lines[ix], 132)
                    line3 = StringUtils.limitLength2(line, 132)
                    self.logger.log(
                        f'replacement at {ix}:\n{line2}\n{line3}', Const.LEVEL_DETAIL)
                self.hasChanged = True
                self.lines[ix] = line
        else:
            if anchor is None:
                ix = len(self.lines)
            else:
                if isinstance(anchor, str):
                    anchor = re.compile(anchor)
                ix = self.findLine(anchor)
                if ix < 0:
                    ix = len(self.lines)
                else:
                    ix = ix if above else ix + 1
                self.lines.insert(ix, line)
                self.hasChanged = True
                if self.logger.verboseLevel() >= Const.LEVEL_DETAIL:
                    line3 = StringUtils.limitLength2(line, 132)
                    self.logger.log(
                        f'insert at {ix}:\n{line}', Const.LEVEL_DETAIL)

    def readFile(self, filename: str, mustExists: bool=True):
        '''Reads a file into the internal buffer.
        @param filename: the file to read
        @param mustExists: True: errros will be logged
        @return True: success False: cannot read
        '''
        self.filename = filename
        rc = os.path.exists(filename)
        if not rc:
            if mustExists:
                self.logger.error(f'{filename} does not exists')
        else:
            self.lines = StringUtils.fromFile(filename, '\n')
        self.setEndOfFile(self.endOfFile)
        self.region.startPosition.clone(self.beginOfFile)
        self.region.endPosition.clone(self.endOfFile)
        self._cursor.clone(self.beginOfFile)
        return rc

    def replace(self, pattern: str, replacement: str, groupMarker:str =None,
                noRegExpr: bool=False, countHits: bool=False,
                wordOnly: bool=False, ignoreCase: bool=False, escActive: bool=False):
        r'''Replaces all occurrences of what with a replacement in the current region.
        @param pattern: a regular expression of the string to search unless noRegExpr==True:
        @param replacement: what will be replaced with this. May contain a placeholder for groups in what
        @param groupMarker: None: no group placeholder otherwise: the prefix of a group placeholder
            example: groupMarker='$' then "$1" means the first group in what
        @param noRegExpr: True: pattern is a plain string, not a regular expression
        @param countHits: False: the result is the number of changed lines True: the result is the number of replacements
        @param wordOnly: True: only whole words will be found. Only relevant for regular expressions
        @param ignoreCase: True: the search is not case sensitive
        @param escActive: True: esc sequences '\n', '\r', \t', '\xXX' in replacement will be recognized
        @return: the number of replaced lines/replacements depending on countHits
        '''
        rc = 0
        verbose = self.logger.verboseLevel() > Const.LEVEL_LOOP
        prefix = (self.filename + '-') if self.filename is not None else ''
        if noRegExpr:
            # pylint: disable-next=consider-using-enumerate
            for ix in range(len(self.lines)):
                line = self.lines[ix]
                if line.find(pattern) >= 0:
                    hits = self.lines[ix].count(pattern) if countHits else 1
                    rc += hits
                    self.lines[ix] = self.lines[ix].replace(
                        pattern, replacement)
                    if verbose:
                        line2 = StringUtils.limitLength2(line, 130)
                        line3 = StringUtils.limitLength2(
                            self.lines[ix], 130)
                        self.logger.log(
                            f'{prefix}{ix+1}: {hits} hit(s)\n{line2}\n{line3}')
        else:
            if wordOnly and not noRegExpr:
                pattern = r'\b' + pattern + r'\b'
            reWhat = re.compile(pattern, Const.IGNORE_CASE if ignoreCase else 0) if isinstance(
                pattern, str) else pattern
            if escActive:
                replacement = StringUtils.unescChars(replacement)
            repl = replacement if groupMarker is None else replacement.replace(
                groupMarker, '\\')
            for ix, line in enumerate(self.lines):
                if reWhat.search(line):
                    self.lines[ix], count = reWhat.subn(repl, line)
                    hits = count if countHits else 1
                    rc += hits
                    if verbose:
                        line2 = StringUtils.limitLength2(line, 130)
                        line3 = StringUtils.limitLength2(
                            self.lines[ix], 130)
                        self.logger.log(
                            f'{prefix}{ix+1}: {hits} hit(s)\n{line2}\n{line3}')
        if rc > 0:
            self.hasChanged = True
            prefix = self.filename + ': ' if self.filename is not None else ''
            self.logger.log(f'{prefix}{hits} hit(s)', Const.LEVEL_DETAIL)
        return rc

    def replaceMany(self, what: Sequence[str], replacements: Sequence[str]):
        '''Replaces a list of strings with replacement.
        @param what: a list of strings to search
        @param replacements: a list of replacements
        '''
        allHits = 0
        verbose = self.logger.verboseLevel() >= Const.LEVEL_LOOP
        prefix = (self.filename + '-') if self.filename is not None else ''
        for ix, line in enumerate(self.lines):
            hits = 0
            for ix2, item in enumerate(what):
                hits2 = line.count(item)
                if hits2 > 0:
                    hits += hits2
                    line = line.replace(item, replacements[ix2])
            if hits > 0:
                allHits += hits
                if verbose:
                    line2 = StringUtils.limitLength2(self.lines[ix], 130)
                    line3 = StringUtils.limitLength2(line, 130)
                    self.logger.log(
                        f'{prefix}{ix+1}: {hits} hit(s)\n{line2}\n{line3}')
                self.lines[ix] = line
        if allHits > 0:
            self.hasChanged = True
            prefix = self.filename + ': ' if self.filename is not None else ''
            self.logger.log(f'{prefix}{allHits} hit(s)',
                             Const.LEVEL_DETAIL)
        return allHits

    def searchByGroup(self, pattern: str, groupNo: int=0):
        '''Returns the first hit of a pattern defined by a group.
        @param pattern: a regular expression to search in each line of the buffer
        @param groupNo: the result is that group (defined by parentheses)
        @result: None: not found Otherwise: the group content. example: pattern='ID=(\\d+)' group=1 line='ID=443' result: '443'
        '''
        rc = None
        regExpr = re.compile(pattern) if isinstance(pattern, str) else pattern
        for line in self.lines:
            matcher = regExpr.match(line)
            if matcher:
                rc = matcher.group(groupNo)
                break
        return rc

    def setContent(self, content):
        '''Sets the lines without a file.
        @param content: the content for later processing: a string or a list of strings.
            the single string will be splitted by '\n'
        '''
        if isinstance(content, str):
            self.lines = content.split('\n')
        else:
            self.lines = content
        self.setEndOfFile(self.endOfFile)
        self.region.startPosition.clone(self.beginOfFile)
        self.region.endPosition.clone(self.endOfFile)
        self._cursor.clone(self.beginOfFile)

    def setEndOfFile(self, position: SearchRule.Position):
        '''Sets the position to end of file.
        '''
        position.line = len(self.lines)
        position.col = 0

    def simpleInsertOrReplace(self, filename: str, key, line: str, anchor=None, above: bool=False):
        '''Combination of readFile(), simpleInsertOrReplace() and writeFile().
        Searches the key. If found the line (with the key) is replaced by line.
        If not found: the anchor is searched an the line is inserted at the anchor.
        @param filename: the file to modify
        @param key: a regular expression identifying the line to replace
        @param line: the line to replace or to insert
        @param anchor: None: anchor is the end of the file
            if key is not found this position is used for insertion
        @param above: True: the insertion is done above the anchor
        '''
        self.readFile(filename)
        self.insertOrReplace(key, line, anchor, above)
        self.writeFile()

    def writeFile(self, filename: str=None, backupExtension: str=None):
        '''Writes the internal buffer to a file.
        @param filename: the file to write: if None _filename is taken
        @param backupExtension: None or: if the file already exists it will be renamed by this "rule":
            if it contains os.sep and it is a directory: the file
            if it contains os.sep and it does not exists:
            otherwise: it is handled as a file extension
            following placeholders are allowed:
            '%date%' replace with the  current date %datetime%: replace with the date and time
            '%seconds%' replace with the seconds from epoche
        '''
        filename = self.filename if filename is None else filename
        if os.path.exists(filename) and backupExtension is not None:

            if backupExtension.find('%') >= 0:
                now = datetime.datetime.now()
                backupExtension = backupExtension.replace(
                    '%date%', now.strftime('%Y.%m.%d'))
                backupExtension = backupExtension.replace(
                    '%datetime%', now.strftime('%Y.%m.%d-%H_%M_%S'))
                backupExtension = backupExtension.replace(
                    '%seconds%', now.strftime('%a'))
            if not backupExtension.startswith('.'):
                backupExtension = '.' + backupExtension
            parts = FileHelper.splitFilename(filename)
            parts['ext'] = backupExtension
            newNode = parts['fn'] + backupExtension
            FileHelper.deepRename(filename, newNode, deleteExisting=True)
        StringUtils.toFile(filename, self.lines, '\n')


if __name__ == '__main__':
    pass

'''
TextProcessor.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import os.path
import datetime

import base.Const
import base.StringUtils
import base.SearchRule
import base.SearchRuleList


class TextProcessor:
    '''A processor for finding/modifying text.
    '''

    def __init__(self, logger):
        self._filename = None
        self._lines = None
        self._logger = logger
        self._region = base.SearchRule.Region(self)
        self._cursor = base.SearchRule.Position(0, 0)
        self._endOfFile = base.SearchRule.Position(0, 0)
        self._beginOfFile = base.SearchRule.Position(0, 0)
        self._lastState = None
        self._hasChanged = False
        self._traceFile = None

    def cursor(self, mode='both'):
        '''Returns the cursor as pair (line, col), or the line or the column, depending on mode.
        @param mode: 'both', 'line' or 'col'
        @return [line, col], line or col, depending on mode
        '''
        rc = ([self._cursor._line, self._cursor._col] if mode == 'both' else
              (self._cursor._col if mode == 'col' else self._cursor._line))
        return rc

    def executeRules(self, rulesAsString, maxLoops=1):
        '''Compiles the rules and executes them.
        @param rules: a sequence of rules given as string
        @return True: success False: error
        '''
        ruleList = base.SearchRuleList.SearchRuleList(self._logger)
        rc = ruleList.parseRules(rulesAsString)
        if rc:
            rc = ruleList.check()
        if rc:
            status = base.SearchRule.ProcessState(self._lines, self._region._startPosition, self._region._endPosition,
                                                  self._cursor, self._logger, maxLoops)
            if self._traceFile is not None:
                ruleList.startTrace(self._traceFile, True)
            ruleList.apply(status)
            self._cursor.clone(status._cursor)
            self._lastState = status
            self._hasChanged = status._hasChanged
            rc = status._success
            if self._traceFile is not None:
                ruleList.stopTrace()
        return rc

    def findLine(self, pattern, firstIndex=0, lastIndex=None):
        '''Search a line matching a given regular expression.
        @param pattern: the pattern to find: a string or a RegExpr instance
        @param firstIndex: the index of the first line to inspect
        @param endIndex: exclusive: the index below the last line to inspect
        @return: -1: not found otherwise: the line index 0..N-1
        '''
        rc = -1
        regExpr = re.compile(pattern) if isinstance(pattern, str) else pattern
        ixLine = firstIndex
        last = min(lastIndex, len(self._lines)
                   ) if lastIndex is not None else len(self._lines)
        while ixLine < last:
            if regExpr.search(self._lines[ixLine]):
                rc = ixLine
                break
            ixLine += 1
        return rc

    def insertOrReplace(self, key, line, anchor=None, above=False):
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
            if self._lines[ix] == line:
                self._logger.log(
                    f'key found, but same content at {ix}', base.Const.LEVEL_DETAIL)
            else:
                if self._logger._verboseLevel >= base.Const.LEVEL_DETAIL:
                    line2 = base.StringUtils.limitLength2(self._lines[ix], 132)
                    line3 = base.StringUtils.limitLength2(line, 132)
                    self._logger.log(
                        f'replacement at {ix}:\n{line2}\n{line3}', base.Const.LEVEL_DETAIL)
                self._hasChanged = True
                self._lines[ix] = line
        else:
            if anchor is None:
                ix = len(self._lines)
            else:
                if isinstance(anchor, str):
                    anchor = re.compile(anchor)
                ix = self.findLine(anchor)
                if ix < 0:
                    ix = len(self._lines)
                else:
                    ix = ix if above else ix + 1
                self._lines.insert(ix, line)
                self._hasChanged = True
                if self._logger._verboseLevel >= base.Const.LEVEL_DETAIL:
                    line3 = base.StringUtils.limitLength2(line, 132)
                    self._logger.log(
                        f'insert at {ix}:\n{line2}', base.Const.LEVEL_DETAIL)

    def readFile(self, filename, mustExists=True):
        '''Reads a file into the internal buffer.
        @param filename: the file to read
        @param mustExists: True: errros will be logged
        @return True: success False: cannot read
        '''
        self._filename = filename
        rc = os.path.exists(filename)
        if not rc:
            if mustExists:
                self._logger.error('{} does not exists'.format(filename))
        else:
            self._lines = base.StringUtils.fromFile(filename, '\n')
        self.setEndOfFile(self._endOfFile)
        self._region._startPosition.clone(self._beginOfFile)
        self._region._endPosition.clone(self._endOfFile)
        self._cursor.clone(self._beginOfFile)
        return rc

    def replace(self, pattern, replacement, groupMarker=None, noRegExpr=False, countHits=False,
                wordOnly=False, ignoreCase=False, escActive=False):
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
        verbose = self._logger._verboseLevel > base.Const.LEVEL_LOOP
        prefix = (self._filename + '-') if self._filename is not None else ''
        if noRegExpr:
            for ix in range(len(self._lines)):
                line = self._lines[ix]
                if line.find(pattern) >= 0:
                    hits = self._lines[ix].count(pattern) if countHits else 1
                    rc += hits
                    self._lines[ix] = self._lines[ix].replace(
                        pattern, replacement)
                    if verbose:
                        line2 = base.StringUtils.limitLength2(line, 130)
                        line3 = base.StringUtils.limitLength2(
                            self._lines[ix], 130)
                        self._logger.log(
                            f'{prefix}{ix+1}: {hits} hit(s)\n{line2}\n{line3}')
        else:
            if wordOnly and not noRegExpr:
                pattern = r'\b' + pattern + r'\b'
            reWhat = re.compile(pattern, base.Const.IGNORE_CASE if ignoreCase else 0) if isinstance(
                pattern, str) else pattern
            if escActive:
                replacement = base.StringUtils.unescChars(replacement)
            repl = replacement if groupMarker is None else replacement.replace(
                groupMarker, '\\')
            for ix, line in enumerate(self._lines):
                if reWhat.search(line):
                    self._lines[ix], count = reWhat.subn(repl, line)
                    hits = count if countHits else 1
                    rc += hits
                    if verbose:
                        line2 = base.StringUtils.limitLength2(line, 130)
                        line3 = base.StringUtils.limitLength2(
                            self._lines[ix], 130)
                        self._logger.log(
                            f'{prefix}{ix+1}: {hits} hit(s)\n{line2}\n{line3}')
        if rc > 0:
            self._hasChanged = True
            prefix = self._filename + ': ' if self._filename is not None else ''
            self._logger.log(f'{prefix}{hits} hit(s)', base.Const.LEVEL_DETAIL)
        return rc

    def replaceMany(self, what, replacements):
        '''Replaces a list of strings with replacement.
        @param what: a list of strings to search
        @param replacements: a list of replacements
        '''
        allHits = 0
        verbose = self._logger._verboseLevel >= base.Const.LEVEL_LOOP
        prefix = (self._filename + '-') if self._filename is not None else ''
        for ix, line in enumerate(self._lines):
            hits = 0
            for ix2, item in enumerate(what):
                hits2 = line.count(item)
                if hits2 > 0:
                    hits += hits2
                    line = line.replace(item, replacements[ix2])
            if hits > 0:
                allHits += hits
                if verbose:
                    line2 = base.StringUtils.limitLength2(self._lines[ix], 130)
                    line3 = base.StringUtils.limitLength2(line, 130)
                    self._logger.log(
                        f'{prefix}{ix+1}: {hits} hit(s)\n{line2}\n{line3}')
                self._lines[ix] = line
        if allHits > 0:
            self._hasChanged = True
            prefix = self._filename + ': ' if self._filename is not None else ''
            self._logger.log(f'{prefix}{allHits} hit(s)',
                             base.Const.LEVEL_DETAIL)
        return allHits

    def searchByGroup(self, pattern, groupNo=0):
        '''Returns the first hit of a pattern defined by a group.
        @param pattern: a regular expression to search in each line of the buffer
        @param groupNo: the result is that group (defined by parentheses)
        @result: None: not found Otherwise: the group content. example: pattern='ID=(\d+)' group=1 line='ID=443' result: '443'
        '''
        rc = None
        regExpr = re.compile(pattern) if type(pattern) == str else pattern
        for line in self._lines:
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
            self._lines = content.split('\n')
        else:
            self._lines = content
        self.setEndOfFile(self._endOfFile)
        self._region._startPosition.clone(self._beginOfFile)
        self._region._endPosition.clone(self._endOfFile)
        self._cursor.clone(self._beginOfFile)

    def setEndOfFile(self, position):
        '''Sets the position to end of file.
        '''
        position._line = len(self._lines)
        position._col = 0

    def simpleInsertOrReplace(self, filename, key, line, anchor=None, above=False):
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

    def writeFile(self, filename=None, backupExtension=None):
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
        filename = self._filename if filename is None else filename
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
            parts = base.FileHelper.splitFilename(filename)
            parts['ext'] = backupExtension
            newNode = parts['fn'] + backupExtension
            base.FileHelper.deepRename(filename, newNode, deleteExisting=True)
        base.StringUtils.toFile(filename, self._lines, '\n')


if __name__ == '__main__':
    pass

'''
SearchRule.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import base.StringUtils


class CommandData:
    '''Properties given for a command (action except search and reposition).
    @param register: None or the related register ('A'..'Z')
    @param marker: None or the related marker: 'a' .. 'z'
    @param text: None or the related text
    @param text2: None or the related 2nd text
    @param group: None or the related reg. expression group: 0..N
    @param escChar: None or a prefix character to address registers (@see parseRuleReplace())
    @param options: None or an command specific options
    '''

    def __init__(self, register=None, register2=None, marker=None, text=None, text2=None,
                 group=None, escChar=None, options=None):
        self._register = register
        self._register2 = register2
        self._marker = marker
        self._text = text
        self._text2 = text2
        self._group = group
        self._options = options
        self._escChar = escChar

    def getText(self, state, second=False):
        '''Replaces register placeholders with the register content.
        Note: register placeholders starts with self._escChar followed by the register name, e.g. '$A'
        @param state: the ProcessState instance with the registers
        @param second: True: _text2 is used False: _text is used
        @return text with replaced register placeholders
        '''
        text = self._text2 if second else self._text
        if self._escChar is None:
            rc = text
        else:
            startIx = 0
            rc = ''
            while startIx + 2 < len(text):
                ix = text.find(self._escChar, startIx)
                if ix < 0:
                    break
                rc += text[startIx:ix]
                name = text[ix + 1]
                if 'A' <= name <= 'Z':
                    rc += state.getRegister(name)
                else:
                    rc += self._escChar + name
                startIx = ix + 2
            rc += text[startIx:]
        return rc


class FlowControl:
    '''Flow control of a rule: continue, stop or jump on a condition
    '''
    # ..................................A.........A

    def __init__(self):
        '''Constructor.
        '''
        self._onSuccess = 'c'
        self._onError = 'e'

    def setControl(self, control):
        '''Translate the options given as string into the class variables.
        @param control: the control as string
        @param logger: only internal errors are possible
        @return: None: success otherwise: error message
        '''
        rc = None
        reaction = None
        if control[-1] == '%':
            reaction = control[control.find('%'):]
        elif control.endswith('continue'):
            reaction = 'c'
        elif control.endswith('stop'):
            reaction = 's'
        elif control.endswith('error'):
            reaction = 'e'  # error
        else:
            rc = 'unknown control: ' + control
        if control.startswith('success'):
            self._onSuccess = reaction
        elif control.startswith('error'):
            self._onError = reaction
        else:
            rc = 'unknown control statement: ' + control
        return rc


class Position:
    '''Constructor.
    @param line: the line number
    @param col: the column number
    '''

    def __init__(self, line, col):
        self._line = line
        self._col = col

    def toString(self):
        '''Returns the position as string.
        @return: <line>:<col>
        '''
        return '{}:{}'.format(self._line, self._col)

    def check(self, lines, behindLineIsAllowed=False):
        '''Checks, whether the instance is valid in lines.
        @param lines: the list of lines to inspect
        @param behindLineIsAllowed: True: the column may be equal the line length
        @return: True: the cursor is inside the lines
        '''
        rc = self._line < len(lines) and self._col <= len(
            lines[self._line]) - (1 if behindLineIsAllowed else 0)
        return rc

    def clone(self, source):
        '''Transfers the internal state from the source to the self.
        @param source: the Position instance to clone
        '''
        self._line = source._line
        self._col = source._col

    def compare(self, other):
        '''Compares the instance with an other instance
        @param other: the Position instance to compare
        @return: <0: self < other 0: self==other >0: self>other
        '''
        rc = self._line - other._line
        if rc == 0:
            rc = self._col - other._col
        return rc

    def endOfLine(self, lines):
        '''Tests whether the instance is one position behind the current line.
        @param lines: the list of lines to inspect
        @return: True: the instance points to the position one behind the current line or the beginning of the next line
        '''
        rc = self._line == len(
            lines) and self._col == 0 or self._col == len(lines[self._line])
        return rc


class ProcessState:
    '''Reflects the state while processing a rule list.
    '''

    def __init__(self, lines, startRange, endRange, start, logger, maxLoops=10):
        '''Constructor.
        @param lines: the list of lines to inspect
        @param startRange: the rule starts at this position
        @param endRange: the end of the rules must be below this position
        @param start: the rule starts from this position
        @param logger:
        @param maxLoops: the number of executed rules is limited to maxLoops*len(lines)
        '''
        self._logger = logger
        self._lines = lines
        self._maxLoops = maxLoops
        self._cursor = Position(start._line, start._col)
        self._startRange = startRange
        self._endRange = endRange
        self._logger = logger
        self._success = True
        self._lastMatch = None
        # replaces temporary _startRange or _endRange
        self._tempRange = Position(0, 0)
        self._safePosition = Position(0, 0)
        # <name>: Position
        self._markers = {}
        # <name>: string
        self._registers = {}
        self._hasChanged = False
        self._lastHits = 0

    def deleteToMarker(self, name):
        '''Deletes the text from the cursor to the marker.
        @param name: a bound of the region to delete, _position is the other
        '''

        marker = self.getMarker(name)
        self._success = marker is not None and self.inRange(
            marker) and self.inRange()
        if self._success:
            comp = self._cursor.compare(marker)
            start = marker if comp >= 0 else self._cursor
            end = self._cursor if comp >= 0 else marker
            ixStart = start._line
            deletedLines = 0
            self._hasChanged = True
            if start._line == end._line:
                self._lines[ixStart] = self._lines[ixStart][0:start._col] + \
                    self._lines[ixStart][end._col:]
            else:
                prefix = '' if start._col == 0 else self._lines[start._line][0:start._col]
                ixEnd = end._line if end._col > 0 else end._line + 1
                if end._col > 0:
                    self._lines[end._line] = prefix + \
                        self._lines[end._line][end._col:]
                for ix in range(ixStart, ixEnd):
                    del self._lines[ix]
                    deletedLines += 1
            # Adapt the existing markers:
            for name2 in self._markers:
                current = self.getMarker(name2)
                if current.compare(start) >= 0:
                    if current._line > end._line or current._line == end._line and end._col == 0:
                        current._line -= deletedLines
                    elif current._line == end._line:
                        if current._col > end._col:
                            current._col -= end.col
                        current.clone(start)
                    else:
                        current.clone(start)

    def insertAtCursor(self, text):
        '''Inserts a text at the cursor.
        @param text: the text to insert, may contain '\n'
        '''
        self._success = self.inRange()
        if self._success:
            newLines = text.split('\n')
            curLine = self._cursor._line
            self._hasChanged = True
            if len(newLines) == 1:
                insertedLines = 0
                colNew = self._cursor._col + len(text)
                self._lines[curLine] = (self._lines[curLine][0:self._cursor._col] + newLines[0]
                                        + self._lines[curLine][self._cursor._col:])
            else:
                insertedLines = len(newLines)
                tail = ''
                ixNew = 0
                if self._cursor._col > 0:
                    ixNew = 1
                    tail = self._lines[self._cursor._line][self._cursor._col:]
                    self._lines[curLine] = self._lines[curLine][0:self._cursor._col] + newLines[0]
                    curLine += 1
                    insertedLines -= 1
                ixLast = len(newLines)
                while ixNew < ixLast:
                    self._lines.insert(curLine, newLines[ixNew])
                    ixNew += 1
                    curLine += 1
                self._lines[curLine - 1] = self._lines[curLine - 1] + tail
                colNew = len(newLines[-1])
            for name in self._markers:
                marker = self._markers[name]
                if marker.compare(self._cursor) >= 0:
                    if marker._line == self._cursor._line and marker._col > self._cursor._col:
                        marker._line += insertedLines
                        marker._col += len(newLines[-1])
                    elif marker._line == self._cursor._line > 0:
                        marker._line += insertedLines
            self._cursor._line += insertedLines
            self._cursor._col = colNew

    def getMarker(self, name):
        '''Returns the marker given by the name ('a'..'z')
        @param name: the marker's name: 'a'..'z'
        @return: None: not found otherwise: the Position instance
        '''
        rc = None if not name in self._markers else self._markers[name]
        return rc

    def getRegister(self, name, maxLength=None):
        '''Returns the marker given by the name ('a'..'z')
        @param name: the marker's name: 'a'..'z'
        @return: '': not found otherwise: the register content
        '''
        rc = '' if not name in self._registers else self._registers[name]
        if maxLength is not None:
            rc = base.StringUtils.limitLength2(
                rc, maxLength).replace('\n', '\\n')
        return rc

    def inRange(self, position=None):
        '''Returns whether a position is in the current range.
        @param position: a Position instance to test
        @return: position is between _startRange and _endRange
        '''
        if position is None:
            position = self._cursor
        rc = (position._line > self._startRange._line
              or position._line == self._startRange._line and position._col >= self._startRange._col)
        rc = rc and (position._line < self._endRange._line or position._line == self._endRange._line
                     and position._col <= self._endRange._col)
        return rc

    def putToRegister(self, name, text, append=False):
        '''Sets the register <name> with a text.
        @param name: the register name: 'A'..'Z'
        @param text: the text to set
        @param append: True: the text will be appended False: the text will be set
        '''
        if not append or not name in self._registers:
            self._registers[name] = text
        else:
            self._registers[name] += text

    def setMarker(self, name):
        '''Sets the marker <name> from the current position.
        @param name: the marker name: 'a'..'z'
        '''
        if not name in self._markers:
            self._markers[name] = Position(0, 0)
        self._markers[name].clone(self._cursor)

    def textToMarker(self, name):
        '''Returns the text between the marker name and the cursor.
        @param name: the marker's name
        @return: the text between marker and cursor (current position)
        '''
        rc = ''
        marker = self.getMarker(name)
        if marker is not None and self.inRange(marker) and self.inRange():
            comp = self._cursor.compare(marker)
            start = marker if comp >= 0 else self._cursor
            end = self._cursor if comp >= 0 else marker
            ixStart = start._line
            if start._line == end._line:
                rc = self._lines[start._line][start._col:end._col]
            else:
                if start._col > 0:
                    prefix = self._lines[start._line][start._col:]
                    ixStart += 1
                rc = '\n'.join(self._lines[ixStart:end._line])
                if start._col > 0:
                    if rc == '':
                        rc = prefix
                    else:
                        rc = prefix + '\n' + rc
                if end._col > 0:
                    if rc != '':
                        rc += '\n'
                    rc += self._lines[end._line][0:end._col]
        return rc


class Region:
    '''Stores the data of a region, which is a part of the file given by a start and an end position.
    '''

    def __init__(self, parent, startRuleList=None, endRuleList=None, endIsIncluded=False):
        '''Constructor.
        @param parent: the TextProcessor instance
        @param startRuleList: None or the compiled rules defining the start of the region
        @param startRuleList: None or the compiled rules defining the end of the region
        @param endIsIncluded: True: if the last rule is a search: the hit belongs to the region
        '''
        self._parent = parent
        self._startRules = startRuleList
        self._endRules = endRuleList
        self._startPosition = Position(0, 0)
        # index of the first line below the region (exclusive)
        self._endPosition = Position(0, 0)
        self._endIsIncluded = endIsIncluded
        self._start = None
        self._end = None

    def next(self):
        '''Search the next region from current region end.
        @param ixFirst: the index of the first line (in parent._lines) to inspect
        @return: True: the start has been found False: not found
        '''
        rc = self._parent.apply(
            self._startRules, self._endPosition, self._parent._endOfFile)
        return rc

    def find(self, pattern):
        '''Searches the pattern in the region.
        @param pattern: a string or a RegExp instance to search
        @return: -1: not found otherwise: the index of the first line matching the pattern
        '''
        rc = self._parent.findLine(pattern, self._start, self._end)
        return rc


class SearchRule:
    '''Describes a single action: search, reposition, set label/bookmark, print....
    @see SearchRuleList vor details.
    '''

    def __init__(self, ruleType, param=None):
        '''Constructor.
        @param ruleType: the type: '<' (search backwards) '>': search forward 'l': line:col 'a': anchor
        @param parameter: parameter depending on ruleType: RegExp instance for searches,
            names for anchors or a [<line>, <col>] array for ruleType == 'l'
        '''
        self._ruleType = ruleType
        self._param = param
        self._flowControl = FlowControl()

    def name(self, extended=False):
        '''Returns the command name.
        @return the command name
        '''
        rc = None
        if self._ruleType == '%':
            rc = 'label' + ((' ' + self._param) if extended else '')
        elif self._ruleType == '>':
            rc = 'search (forward)' + ((' /' +
                                        self._param._regExpr.pattern + '/') if extended else '')
        elif self._ruleType == '<':
            rc = 'search (backward)' + ((' /' +
                                         self._param._regExpr.pattern + '/') if extended else '')
        elif self._ruleType == '+':
            rc = 'reposition'
            if extended:
                rc += ' {}{}:{}'.format(self._param[2],
                                        self._param[0], self._param[1])
        elif self._ruleType == 'anchor':
            rc = self._param
        else:
            rc = self._ruleType
        return rc

    def searchForward(self, state):
        '''Searches forward in lines in the range given by startRange and endRange.
        @param processState: IN/OUT: the context of searching, an instance of ProcessState
        '''
        state._safePosition.clone(state._cursor)
        state._success = state.inRange()
        if state._success:
            startIx = state._cursor._line
            endIx = min(len(state._lines), state._endRange._line + 1)
            if self._param._rangeLines is not None:
                endIx = min(startIx + self._param._rangeLines, endIx)
            match = None
            regExpr = self._param._regExpr
            for ix in range(startIx, endIx):
                if ix == state._startRange._line:
                    match = regExpr.search(
                        state._lines[ix], state._startRange._col)
                elif ix == state._endRange._line:
                    match = regExpr.search(
                        state._lines[ix], 0, state._endRange._col)
                else:
                    match = regExpr.search(
                        state._lines[ix], state._startRange._col)
                if match is not None:
                    break
            state._success = match is not None
            state._lastMatch = match
            if state._success:
                state._cursor._line = ix
                state._cursor._col = match.end(
                    0) if self._param._useEnd else match.start(0)
                state._success = state.inRange()

    def searchBackward(self, state):
        '''Searches backward in lines in the range given by startRange and endRange.
        @param processState: IN/OUT: the context of searching, an instance of ProcessState
        '''
        state._safePosition.clone(state._cursor)
        state._success = state.inRange()
        if state._success:
            regExpr = self._param._regExpr
            startIx = max(0, min(state._cursor._line, len(state._lines) - 1))
            endIx = state._startRange._line - 1
            state._lastMatch = None
            if self._param._rangeLines is not None:
                endIx = max(state._startRange._line - 1,
                            max(-1, startIx - self._param._rangeLines))
            for ix in range(startIx, endIx, -1):
                if ix == state._startRange._line:
                    iterator = regExpr.finditer(
                        state._lines[ix], state._startRange._col)
                elif ix == state._endRange._line:
                    iterator = regExpr.finditer(
                        state._lines[ix], 0, state._endRange._col)
                else:
                    iterator = regExpr.finditer(
                        state._lines[ix], state._startRange._col)
                # Look for the last match:
                for match in iterator:
                    state._lastMatch = match
                if state._lastMatch is not None:
                    break
            state._success = state._lastMatch is not None
            if state._success:
                state._cursor._line = ix
                state._cursor._col = state._lastMatch.end(
                    0) if self._param._useEnd else state._lastMatch.start(0)
                state._success = state.inRange()

    def reposition(self, state):
        '''Apply the reposition rule: an anchor or a line/col move.
        @param processState: IN/OUT: the context of searching, an instance of ProcessState
        '''
        if self._ruleType == '+':
            if self._param[2] == ':':
                state._cursor._line = self._param[0]
                state._cursor._col = self._param[1]
            else:
                state._cursor._line += self._param[0]
                state._cursor._col += self._param[1]
                # if the new line is shorter than the old col position: goto last column
                # except the column is explicitly set
                if self._param[1] == 0 and state._cursor._line < len(state._lines):
                    lineLength = len(state._lines[state._cursor._line])
                    if state._cursor._col >= lineLength:
                        state._cursor._col = max(0, lineLength - 1)
        elif self._param == 'bof':
            state._cursor._line = state._cursor._col = 0
        elif self._param == 'eof':
            state._cursor._line = len(state._lines)
            state._cursor._col = 0
        elif self._param == 'bol':
            state._cursor._col = 0
        elif self._param == 'eol':
            # overflow is allowed:
            state._cursor._line += 1
            state._cursor._col = 0
        elif self._param == 'bopl':
            state._cursor._line -= 1
            state._cursor._col = 0
        elif self._param == 'eopl':
            state._cursor._col = 0
        elif self._param == 'bonl':
            # overflow is allowed:
            state._cursor._line += 1
            state._cursor._col = 0
        elif self._param == 'eonl':
            # overflow is allowed:
            state._cursor._line += 2
            state._cursor._col = 0
        else:
            state._logger.error(
                'reposition(): unknown anchor: {}'.format(self._param))
        state._success = state.inRange()

    def state(self, after, state):
        '''Returns the "state" of the rule, used for tracing.
        @param after: True: the state is after the rule processing
        @param state: the ProcessState instance
        @return: the specific data of the rule
        '''
        def cursor():
            return state._cursor.toString()

        def marker():
            name = self._param._marker
            return '{}[{}]'.format(name, '-' if name not in state._markers else state.getMarker(self._param._marker).toString())

        def register():
            name = self._param._register
            return ((name if name is not None else '<none>') + ':'
                    + ('<none>' if name not in state._registers else state.getRegister(name, 40)))
        name = self._ruleType
        if not after:
            state._traceCursor = cursor()
            state._traceState = ''
            rc = ''
        else:
            rc = '{} => {}, {} => '.format(
                state._traceCursor, cursor(), state._traceState)
        if name in ('>', '<', '+', 'anchor', 'swap'):
            rc += '-'
        elif name in ('add', 'insert', 'set', 'expr', 'state'):
            rc += register()
        elif name == 'cut':
            # cut-m
            # cut-R-m
            rc += '' if after else marker() + ' / '
            if after and self._param._register is not None:
                rc += register()
            else:
                rc += '-'
        elif name == 'group':
            rc += register()
        elif name == 'jump':
            if after and self._param._marker is not None:
                rc += state.getMarker(self._param._marker).toString()
            else:
                rc += '-'
        elif name == 'mark':
            rc += marker()
        elif name == 'print':
            if self._param._marker is not None:
                rc += marker() if after else '-'
            elif self._param._register is not None:
                rc += register() if after else ''
        elif name == 'replace':
            if self._param._register is not None:
                rc += register()
            elif self._param._marker is not None and after:
                rc += marker()
            else:
                rc += '-'
            if after:
                rc += ' hits: {}'.format(state._lastHits)
        if not after:
            state._traceState = rc
        return rc

    def toString(self):
        '''Returns a string describing the instance.
        @return: a string describing the instance
        '''
        name = self._ruleType
        if name in ('>', '<'):
            rc = name + '/' + \
                base.StringUtils.limitLength2(
                    self._param._regExpr.pattern, 40) + '/'
        elif name == '+':
            rc = 'reposition {}{}:{}'.format(
                self._param[2], self._param[0], self._param[1])
        elif name == 'anchor':
            rc = self._param
        elif name == 'jump':
            rc = name + '-' + \
                (self._param._marker if self._param._marker is not None else self._param._text)
        elif name == '%':
            rc = 'label ' + self._param
        elif name == 'replace':
            rc = name
            if self._param._register is not None:
                rc += '-' + self._param._register
            if self._param._marker is not None:
                rc += '-' + self._param._marker
            rc += (':/' + base.StringUtils.limitLength2(self._param._text, 20)
                   + '/' + base.StringUtils.limitLength2(self._param._text2, 20))
        else:
            rc = name
            if self._param._register is not None:
                rc += '-' + self._param._register
            if self._param._marker is not None:
                rc += '-' + self._param._marker
            if self._param._text is not None:
                rc += ':"' + \
                    base.StringUtils.limitLength2(self._param._text, 40) + '"'
        return rc

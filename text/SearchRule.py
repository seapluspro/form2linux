'''
SearchRule.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
from typing import Sequence

from base import StringUtils
from base import Logger


# pylint: disable-next=too-few-public-methods
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

    def __init__(self, register: str=None, register2: str=None,
                 marker: str=None, text: str=None, text2: str=None,
                 group: str=None, escChar: str=None, options=None):
        self.register = register
        self.register2 = register2
        self.marker = marker
        self.text = text
        self.text2 = text2
        self.group = group
        self.options = options
        self.escChar = escChar

    def getText(self, state, second: bool=False):
        '''Replaces register placeholders with the register content.
        Note: register placeholders starts with self.escChar followed by the register name, e.g. '$A'
        @param state: the ProcessState instance with the registers
        @param second: True: _text2 is used False: _text is used
        @return text with replaced register placeholders
        '''
        text = self.text2 if second else self.text
        if self.escChar is None:
            rc = text
        else:
            startIx = 0
            rc = ''
            while startIx + 2 < len(text):
                ix = text.find(self.escChar, startIx)
                if ix < 0:
                    break
                rc += text[startIx:ix]
                name = text[ix + 1]
                if 'A' <= name <= 'Z':
                    rc += state.getRegister(name)
                else:
                    rc += self.escChar + name
                startIx = ix + 2
            rc += text[startIx:]
        return rc


# pylint: disable-next=too-few-public-methods
class FlowControl:
    '''Flow control of a rule: continue, stop or jump on a condition
    '''
    # ..................................A.........A

    def __init__(self):
        '''Constructor.
        '''
        self.onSuccess = 'c'
        self.onError = 'e'

    def setControl(self, control: str):
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
            # error
            reaction = 'e'
        else:
            rc = f'unknown control: {control}'
        if control.startswith('success'):
            self.onSuccess = reaction
        elif control.startswith('error'):
            self.onError = reaction
        else:
            rc = 'unknown control statement: ' + control
        return rc


class Position:
    '''Constructor.
    @param line: the line number
    @param col: the column number
    '''

    def __init__(self, line: int, col: int):
        self.line = line
        self.col = col

    def toString(self) -> str:
        '''Returns the position as string.
        @return: <line>:<col>
        '''
        return '{self.line}:{self.col}'

    def check(self, lines: Sequence[str], behindLineIsAllowed: bool=False):
        '''Checks, whether the instance is valid in lines.
        @param lines: the list of lines to inspect
        @param behindLineIsAllowed: True: the column may be equal the line length
        @return: True: the cursor is inside the lines
        '''
        rc = self.line < len(lines) and self.col <= len(
            lines[self.line]) - (1 if behindLineIsAllowed else 0)
        return rc

    def clone(self, source):
        '''Transfers the internal state from the source to the self.
        @param source: the Position instance to clone
        '''
        self.line = source.line
        self.col = source.col

    def compare(self, other):
        '''Compares the instance with an other instance
        @param other: the Position instance to compare
        @return: <0: self < other 0: self==other >0: self>other
        '''
        rc = self.line - other.line
        if rc == 0:
            rc = self.col - other.col
        return rc

    def endOfLine(self, lines: Sequence[str]):
        '''Tests whether the instance is one position behind the current line.
        @param lines: the list of lines to inspect
        @return: True: the instance points to the position one behind the current line or the beginning of the next line
        '''
        rc = self.line == len(
            lines) and self.col == 0 or self.col == len(lines[self.line])
        return rc


class ProcessState:
    '''Reflects the state while processing a rule list.
    '''

    def __init__(self, lines: Sequence[str], startRange, endRange, start, logger: Logger.Logger, maxLoops: int=10):
        '''Constructor.
        @param lines: the list of lines to inspect
        @param startRange: the rule starts at this position
        @param endRange: the end of the rules must be below this position
        @param start: the rule starts from this position
        @param logger:
        @param maxLoops: the number of executed rules is limited to maxLoops*len(lines)
        '''
        self.logger = logger
        self.lines = lines
        self.maxLoops = maxLoops
        self.cursor = Position(start.line, start.col)
        self.startRange = startRange
        self.endRange = endRange
        self.logger = logger
        self.success = True
        self.lastMatch = None
        # replaces temporary _startRange or _endRange
        self.tempRange = Position(0, 0)
        self.safePosition = Position(0, 0)
        # <name>: Position
        self.markers = {}
        # <name>: string
        self.registers = {}
        self.hasChanged = False
        self.lastHits = 0

    def deleteToMarker(self, name: str):
        '''Deletes the text from the cursor to the marker.
        @param name: a bound of the region to delete, _position is the other
        '''

        marker = self.getMarker(name)
        self.success = marker is not None and self.inRange(
            marker) and self.inRange()
        if self.success:
            comp = self.cursor.compare(marker)
            start = marker if comp >= 0 else self.cursor
            end = self.cursor if comp >= 0 else marker
            ixStart = start.line
            deletedLines = 0
            self.hasChanged = True
            if start.line == end.line:
                self.lines[ixStart] = self.lines[ixStart][0:start.col] + \
                    self.lines[ixStart][end.col:]
            else:
                prefix = '' if start.col == 0 else self.lines[start.line][0:start.col]
                ixEnd = end.line if end.col > 0 else end.line + 1
                if end.col > 0:
                    self.lines[end.line] = prefix + \
                        self.lines[end.line][end.col:]
                for ix in range(ixStart, ixEnd):
                    del self.lines[ix]
                    deletedLines += 1
            # Adapt the existing markers:
            # pylint: disable-next=consider-using-dict-items
            for name2 in self.markers:
                current = self.getMarker(name2)
                if current.compare(start) >= 0:
                    if current.line > end.line or current.line == end.line and end.col == 0:
                        current.line -= deletedLines
                    elif current.line == end.line:
                        if current.col > end.col:
                            current.col -= end.col
                        current.clone(start)
                    else:
                        current.clone(start)

    def insertAtCursor(self, text: str):
        '''Inserts a text at the cursor.
        @param text: the text to insert, may contain '\n'
        '''
        self.success = self.inRange()
        if self.success:
            newLines = text.split('\n')
            curLine = self.cursor.line
            self.hasChanged = True
            if len(newLines) == 1:
                insertedLines = 0
                colNew = self.cursor.col + len(text)
                self.lines[curLine] = (self.lines[curLine][0:self.cursor.col] + newLines[0]
                                       + self.lines[curLine][self.cursor.col:])
            else:
                insertedLines = len(newLines)
                tail = ''
                ixNew = 0
                if self.cursor.col > 0:
                    ixNew = 1
                    tail = self.lines[self.cursor.line][self.cursor.col:]
                    self.lines[curLine] = self.lines[curLine][0:self.cursor.col] + newLines[0]
                    curLine += 1
                    insertedLines -= 1
                ixLast = len(newLines)
                while ixNew < ixLast:
                    self.lines.insert(curLine, newLines[ixNew])
                    ixNew += 1
                    curLine += 1
                self.lines[curLine - 1] = self.lines[curLine - 1] + tail
                colNew = len(newLines[-1])
            for marker in self.markers.values():
                if marker.compare(self.cursor) >= 0:
                    if marker.line == self.cursor.line and marker.col > self.cursor.col:
                        marker.line += insertedLines
                        marker.col += len(newLines[-1])
                    elif marker.line == self.cursor.line > 0:
                        marker.line += insertedLines
            self.cursor.line += insertedLines
            self.cursor.col = colNew

    def getMarker(self, name: str):
        '''Returns the marker given by the name ('a'..'z')
        @param name: the marker's name: 'a'..'z'
        @return: None: not found otherwise: the Position instance
        '''
        rc = None if not name in self.markers else self.markers[name]
        return rc

    def getRegister(self, name: str, maxLength: int=None):
        '''Returns the marker given by the name ('a'..'z')
        @param name: the marker's name: 'a'..'z'
        @return: '': not found otherwise: the register content
        '''
        rc = '' if not name in self.registers else self.registers[name]
        if maxLength is not None:
            rc = StringUtils.limitLength2(
                rc, maxLength).replace('\n', '\\n')
        return rc

    def inRange(self, position: Position=None):
        '''Returns whether a position is in the current range.
        @param position: a Position instance to test
        @return: position is between _startRange and _endRange
        '''
        if position is None:
            position = self.cursor
        rc = (position.line > self.startRange.line
              or position.line == self.startRange.line and position.col >= self.startRange.col)
        rc = rc and (position.line < self.endRange.line or position.line == self.endRange.line
                     and position.col <= self.endRange.col)
        return rc

    def putToRegister(self, name: str, text: str, append: bool=False):
        '''Sets the register <name> with a text.
        @param name: the register name: 'A'..'Z'
        @param text: the text to set
        @param append: True: the text will be appended False: the text will be set
        '''
        if not append or not name in self.registers:
            self.registers[name] = text
        else:
            self.registers[name] += text

    def setMarker(self, name: str):
        '''Sets the marker <name> from the current position.
        @param name: the marker name: 'a'..'z'
        '''
        if not name in self.markers:
            self.markers[name] = Position(0, 0)
        self.markers[name].clone(self.cursor)

    def textToMarker(self, name: str):
        '''Returns the text between the marker name and the cursor.
        @param name: the marker's name
        @return: the text between marker and cursor (current position)
        '''
        rc = ''
        marker = self.getMarker(name)
        if marker is not None and self.inRange(marker) and self.inRange():
            comp = self.cursor.compare(marker)
            start = marker if comp >= 0 else self.cursor
            end = self.cursor if comp >= 0 else marker
            ixStart = start.line
            if start.line == end.line:
                rc = self.lines[start.line][start.col:end.col]
            else:
                if start.col > 0:
                    prefix = self.lines[start.line][start.col:]
                    ixStart += 1
                rc = '\n'.join(self.lines[ixStart:end.line])
                if start.col > 0:
                    if rc == '':
                        rc = prefix
                    else:
                        rc = prefix + '\n' + rc
                if end.col > 0:
                    if rc != '':
                        rc += '\n'
                    rc += self.lines[end.line][0:end.col]
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
        self.parent = parent
        self.startRules = startRuleList
        self.endRules = endRuleList
        self.startPosition = Position(0, 0)
        # index of the first line below the region (exclusive)
        self.endPosition = Position(0, 0)
        self.endIsIncluded = endIsIncluded
        self.start = None
        self.end = None

    def next(self):
        '''Search the next region from current region end.
        @param ixFirst: the index of the first line (in parent.lines) to inspect
        @return: True: the start has been found False: not found
        '''
        rc = self.parent.apply(
            self.startRules, self.endPosition, self.parent.endOfFile)
        return rc

    def find(self, pattern: str):
        '''Searches the pattern in the region.
        @param pattern: a string or a RegExp instance to search
        @return: -1: not found otherwise: the index of the first line matching the pattern
        '''
        rc = self.parent.findLine(pattern, self.start, self.end)
        return rc


class SearchRule:
    '''Describes a single action: search, reposition, set label/bookmark, print....
    @see SearchRuleList vor details.
    '''

    def __init__(self, ruleType: str, param=None):
        '''Constructor.
        @param ruleType: the type: '<' (search backwards) '>': search forward 'l': line:col 'a': anchor
        @param param: parameter depending on ruleType: RegExp instance for searches,
            names for anchors or a [<line>, <col>] array for ruleType == 'l'
        '''
        self.ruleType = ruleType
        self.param = param
        self.flowControl = FlowControl()

    def name(self, extended: bool=False) -> str:
        '''Returns the command name.
        @return the command name
        '''
        rc = None
        if self.ruleType == '%':
            rc = 'label' + ((' ' + self.param) if extended else '')
        elif self.ruleType == '>':
            rc = 'search (forward)' + ((' /' +
                                        self.param.regExpr.pattern + '/') if extended else '')
        elif self.ruleType == '<':
            rc = 'search (backward)' + ((' /' +
                                         self.param.regExpr.pattern + '/') if extended else '')
        elif self.ruleType == '+':
            rc = 'reposition'
            if extended:
                rc += f' {self.param[2]}{self.param[0]}:{self.param[1]}'
        elif self.ruleType == 'anchor':
            rc = self.param
        else:
            rc = self.ruleType
        return rc

    def searchForward(self, state: ProcessState):
        '''Searches forward in lines in the range given by startRange and endRange.
        @param processState: IN/OUT: the context of searching, an instance of ProcessState
        '''
        state.safePosition.clone(state.cursor)
        state.success = state.inRange()
        if state.success:
            startIx = state.cursor.line
            endIx = min(len(state.lines), state.endRange.line + 1)
            if self.param.rangeLines is not None:
                endIx = min(startIx + self.param.rangeLines, endIx)
            match = None
            regExpr = self.param.regExpr
            for ix in range(startIx, endIx):
                if ix == state.startRange.line:
                    match = regExpr.search(
                        state.lines[ix], state.startRange.col)
                elif ix == state.endRange.line:
                    match = regExpr.search(
                        state.lines[ix], 0, state.endRange.col)
                else:
                    match = regExpr.search(
                        state.lines[ix], state.startRange.col)
                if match is not None:
                    break
            state.success = match is not None
            state.lastMatch = match
            if state.success:
                state.cursor.line = ix
                state.cursor.col = match.end(
                    0) if self.param.useEnd else match.start(0)
                state.success = state.inRange()

    def searchBackward(self, state: ProcessState):
        '''Searches backward in lines in the range given by startRange and endRange.
        @param processState: IN/OUT: the context of searching, an instance of ProcessState
        '''
        state.safePosition.clone(state.cursor)
        state.success = state.inRange()
        if state.success:
            regExpr = self.param.regExpr
            startIx = max(0, min(state.cursor.line, len(state.lines) - 1))
            endIx = state.startRange.line - 1
            state.lastMatch = None
            if self.param.rangeLines is not None:
                endIx = max(state.startRange.line - 1, -1, startIx - self.param.rangeLines)
            for ix in range(startIx, endIx, -1):
                if ix == state.startRange.line:
                    iterator = regExpr.finditer(
                        state.lines[ix], state.startRange.col)
                elif ix == state.endRange.line:
                    iterator = regExpr.finditer(
                        state.lines[ix], 0, state.endRange.col)
                else:
                    iterator = regExpr.finditer(
                        state.lines[ix], state.startRange.col)
                # Look for the last match:
                for match in iterator:
                    state.lastMatch = match
                if state.lastMatch is not None:
                    break
            state.success = state.lastMatch is not None
            if state.success:
                state.cursor.line = ix
                state.cursor.col = state.lastMatch.end(
                    0) if self.param.useEnd else state.lastMatch.start(0)
                state.success = state.inRange()

    def reposition(self, state: ProcessState):
        '''Apply the reposition rule: an anchor or a line/col move.
        @param processState: IN/OUT: the context of searching, an instance of ProcessState
        '''
        if self.ruleType == '+':
            if self.param[2] == ':':
                state.cursor.line = self.param[0]
                state.cursor.col = self.param[1]
            else:
                state.cursor.line += self.param[0]
                state.cursor.col += self.param[1]
                # if the new line is shorter than the old col position: goto last column
                # except the column is explicitly set
                if self.param[1] == 0 and state.cursor.line < len(state.lines):
                    lineLength = len(state.lines[state.cursor.line])
                    if state.cursor.col >= lineLength:
                        state.cursor.col = max(0, lineLength - 1)
        elif self.param == 'bof':
            state.cursor.line = state.cursor.col = 0
        elif self.param == 'eof':
            state.cursor.line = len(state.lines)
            state.cursor.col = 0
        elif self.param == 'bol':
            state.cursor.col = 0
        elif self.param == 'eol':
            # overflow is allowed:
            state.cursor.line += 1
            state.cursor.col = 0
        elif self.param == 'bopl':
            state.cursor.line -= 1
            state.cursor.col = 0
        elif self.param == 'eopl':
            state.cursor.col = 0
        elif self.param == 'bonl':
            # overflow is allowed:
            state.cursor.line += 1
            state.cursor.col = 0
        elif self.param == 'eonl':
            # overflow is allowed:
            state.cursor.line += 2
            state.cursor.col = 0
        else:
            state.logger.error( f'reposition(): unknown anchor: {self.param}')
        state.success = state.inRange()

    def state(self, after: bool, state: ProcessState):
        '''Returns the "state" of the rule, used for tracing.
        @param after: True: the state is after the rule processing
        @param state: the ProcessState instance
        @return: the specific data of the rule
        '''
        def cursor():
            return state.cursor.toString()

        def marker():
            name = self.param.marker
            return f'{name}[{"-" if name not in state.markers else state.getMarker(self.param.marker).toString()}]'

        def register():
            name = self.param.register
            return ((name if name is not None else '<none>') + ':'
                    + ('<none>' if name not in state.registers else state.getRegister(name, 40)))
        name = self.ruleType
        if not after:
            state.traceCursor = cursor()
            state.traceState = ''
            rc = ''
        else:
            rc = f'{state.traceCursor} => {cursor()}, {state.traceState} => '
        if name in ('>', '<', '+', 'anchor', 'swap'):
            rc += '-'
        elif name in ('add', 'insert', 'set', 'expr', 'state'):
            rc += register()
        elif name == 'cut':
            # cut-m
            # cut-R-m
            rc += '' if after else marker() + ' / '
            if after and self.param.register is not None:
                rc += register()
            else:
                rc += '-'
        elif name == 'group':
            rc += register()
        elif name == 'jump':
            if after and self.param.marker is not None:
                rc += state.getMarker(self.param.marker).toString()
            else:
                rc += '-'
        elif name == 'mark':
            rc += marker()
        elif name == 'print':
            if self.param.marker is not None:
                rc += marker() if after else '-'
            elif self.param.register is not None:
                rc += register() if after else ''
        elif name == 'replace':
            if self.param.register is not None:
                rc += register()
            elif self.param.marker is not None and after:
                rc += marker()
            else:
                rc += '-'
            if after:
                rc += ' hits: {state.lastHits}'
        if not after:
            state.traceState = rc
        return rc

    def toString(self) -> str:
        '''Returns a string describing the instance.
        @return: a string describing the instance
        '''
        name = self.ruleType
        if name in ('>', '<'):
            rc = name + '/' + \
                StringUtils.limitLength2(
                    self.param.regExpr.pattern, 40) + '/'
        elif name == '+':
            rc = f'reposition {self.param[2]}{self.param[0]}:{self.param[1]}'
        elif name == 'anchor':
            rc = self.param
        elif name == 'jump':
            rc = name + '-' + \
                (self.param.marker if self.param.marker is not None else self.param.text)
        elif name == '%':
            rc = 'label ' + self.param
        elif name == 'replace':
            rc = name
            if self.param.register is not None:
                rc += '-' + self.param.register
            if self.param.marker is not None:
                rc += '-' + self.param.marker
            rc += (':/' + StringUtils.limitLength2(self.param.text, 20)
                   + '/' + StringUtils.limitLength2(self.param.text2, 20))
        else:
            rc = name
            if self.param.register is not None:
                rc += '-' + self.param.register
            if self.param.marker is not None:
                rc += '-' + self.param.marker
            if self.param.text is not None:
                rc += f':"{StringUtils.limitLength2(self.param.text, 40)}"'
        return rc

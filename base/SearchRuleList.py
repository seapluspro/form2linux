'''
SearchRuleList.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re

import base.Const
import base.StringUtils
import base.SearchRule

class SearchRuleList:
    '''A list of rules to find a new position or do some other things.
    @see describe() for detailed description.
    '''
    #..........................rule
    # .........................1
    __reRule = re.compile(r'%[a-zA-Z_]\w*%:'
                          #        rule
                          #........A
                          + r'|(?:[be]of|[be]o[pn]?l'
                          #...........line........col
                          #.............1...1......2...2
                          + r'|[+-]?(\d+):[+-]?(\d+)'
                          #..............sep.....sep rows/cols
                          #..............3..3........C.......C
                          + r'|[<>FB](\S).+?\3\s?(?::?\d+)?\s?[ie]{0,2}'
                          #.command.name
                          # .......4E
                          + r'|((?:add|cut|expr|group|insert|jump'
                          # ........................................./name
                          # .........................................E
                          + r'|mark|print|replace|set|state|swap)'
                          #..suffix1 name...............suffix2.........text.delim......txt-opt /t /command
                          # ......F...G........... ....GF.H...........H.I...5.....5.....J......J.I.4
                          + r'(?:-(?:[a-zA-Z]|\d\d?))?(?:-[a-zA-Z])?(?::([^\s]).*?\5(?:e=\S)?)?)'
                          #.......A
                          + r')')
    __reRuleExprParams = re.compile(r'[-+/*%](\$[A-Z]|\d+)?')
    # .........................1......12..............2.3.........3
    __reCommand = re.compile(r'([a-z]+)(-[a-zA-Z]|-\d+)?(-[a-zA-Z])?')
    __reRuleStateParam = re.compile(r'rows?|col|size-[A-Z]|rows-[A-Z]|hits')
    __reFlowControl = re.compile(
        r'(success|error):(continue|error|stop|%\w+%)')
    # ....................................A.........  A..1......12...2..3..3..4...........4
    __reRuleReplace = re.compile(
        r'replace(?:-[a-zA-Z])?:([^\s])(.+?)\1(.*?)\1(e=.|,|c=\d+)*')
    # x=re.compile(r'replace:([^\s])(.+)\1(.*)\1(e=.)?')

    def __init__(self, logger, rules=None):
        '''Constructor.
        @param rules: None or the rules as string
            Example: '>/logfile:/ -2:0 bol':
            search forwards "logfile:" go backward 2 line 0 column, go to begin of line
        '''
        self._logger = logger
        self._col = 0
        self._currentRule = ''
        self._errorCount = 0
        self._rules = []
        self._labels = {}
        self._markers = {}
        self._fpTrace = None
        self._maxLoops = None
        if rules is not None:
            self.parseRules(rules)

    def appendCommand(self, name, commandData):
        '''Stores the command data in the _rules.
        Stores markers defined by "mark".
        Tests used markers for a previous definition.
        @param name: the name of the command, e.g. 'add'. Will be used as _ruleType
        @param commandData: an instance of base.SearchRule.CommandData
        '''
        if name == 'mark':
            self._markers[commandData._marker] = self._col
        elif commandData._marker is not None and commandData._marker not in self._markers:
            self.parseError(
                'marker {} was not previously defined'.format(commandData._marker))
        self._rules.append(base.SearchRule.SearchRule(name, commandData))

    def apply(self, state):
        '''Executes the internal stored rules in a given list of lines inside a range.
        @param state: IN/OUT IN: the context to search OUT: the state at the end of applying the rule list
        '''
        ix = 0
        count = 0
        maxCount = len(state._lines) * state._maxLoops
        while ix < len(self._rules):
            if count >= maxCount:
                state._logger.error(
                    'base.SearchRule.SearchRule.apply(): to many loops: {}'.format(self._maxLoops))
                break
            item = self._rules[ix]
            if self._fpTrace is not None:
                ixTrace = ix
                self.trace(ixTrace, False, state)
            flowControl = self._rules[ix]._flowControl
            ix += 1
            if item._ruleType == '>':
                item.searchForward(state)
            elif item._ruleType == '<':
                item.searchBackward(state)
            elif item._ruleType == '%':
                # label
                pass
            elif item._ruleType == 'anchor' or item._ruleType == '+':
                item.reposition(state)
            elif item._ruleType >= 'p':
                self.applyCommand2(item, state)
            else:
                ix2 = self.applyCommand1(item, state)
                if ix2 is not None:
                    ix = ix2
            if self._fpTrace is not None:
                self.trace(ixTrace, True, state)
            if flowControl is not None:
                reaction = flowControl._onSuccess if state._success else flowControl._onError
                if reaction == 'c':
                    pass
                elif reaction == 's':
                    break
                elif reaction == 'e':
                    self._logger.error('{} stopped with error')
                    break
                elif reaction in self._labels:
                    ix = self._labels[reaction] + 1

    def applyCommand1(self, rule, state):
        '''Executes the action named 'a*' to 'p*' (exclusive)
        @param processState: IN/OUT IN: the context to search OUT: the state at the end of applying the rule list
        @return: None: normal processing otherwise: the index of the next rule to process
        '''
        rc = None
        name = rule._ruleType
        checkPosition = False
        if name == 'add':
            # add-R-m
            # add-R-S
            # add-R D<text>D
            if rule._param._marker is not None:
                text = state.textToMarker(rule._param._marker)
            elif rule._param._register2 is not None:
                text = state.getRegister(rule._param._register2)
            elif rule._param._text is not None:
                text = rule._param.getText(state)
            else:
                state._logger.error('add: nothing to do')
                text = ''
            state.putToRegister(rule._param._register, text, append=True)
        elif name == 'cut':
            # cut-m
            # cut-R-m
            if rule._param._register is not None:
                text = state.textToMarker(rule._param._marker)
                state.putToRegister(rule._param._register, text)
            state.deleteToMarker(rule._param._marker)
        elif name == 'expr':
            # expr-R:"+4"
            value = base.StringUtils.asInt(
                state.getRegister(rule._param._register), 0)
            param = rule._param.getText(state)
            value2 = base.StringUtils.asInt(param[1:], 0)
            op = param[0]
            if op == '+':
                value += value2
            elif op == '-':
                value -= value2
            elif op == '*':
                value *= value2
            elif op == '/':
                if value2 == 0:
                    state._success = self._logger.error(
                        'division by 0 is not defined')
                else:
                    value //= value2
            elif op == '%':
                if value2 == 0:
                    state._success = self._logger.error(
                        'modulo 0 is not defined')
                else:
                    value %= value2
            state._registers[rule._param._register] = str(value)
        elif name == 'insert':
            # insert-R
            # insert D<content>D
            text = ''
            if rule._param._register is not None:
                text = state.getRegister(rule._param._register)
            elif rule._param._text is not None:
                text = rule._param.getText(state)
            state.insertAtCursor(text)
        elif name == 'group':
            # group-G-R
            state._success = state._lastMatch is not None and state._lastMatch.lastindex <= rule._param._group
            if state._success:
                text = '' if state._lastMatch.lastindex < rule._param._group else state._lastMatch.group(
                    rule._param._group)
                state.putToRegister(rule._param._register, text)
        elif name == 'jump':
            if rule._param._marker is not None:
                state._cursor.clone(state.getMarker(rule._param._marker))
                checkPosition = True
            else:
                rc = self._labels[rule._param._text]
        elif name == 'mark':
            state.setMarker(rule._param._marker)
        else:
            state._logger.error('applyCommand1: unknown command')
        if checkPosition:
            state._success = state.inRange()
        return rc

    def applyCommand2(self, rule, state):
        '''Executes the actions named 'p*' to 'z*' (inclusive)
        @param processState: IN/OUT IN: the context to search OUT: the state at the end of applying the rule list
        '''
        name = rule._ruleType
        if name == 'print':
            state._success = True
            if rule._param._register is not None:
                print(state.getRegister(rule._param._register))
            elif rule._param._marker is not None:
                print(state.textToMarker(rule._param._marker))
            elif rule._param._text is not None:
                print(rule._param.getText(state))
        elif name == 'replace':
            param = rule._param
            if param._register is not None:
                replaced, state._lastHits = re.subn(
                    param._text, param._text2, state.getRegister(param._register))
                state._registers[param._register] = replaced
            elif param._marker is not None:
                SearchRuleList.applyReplaceRegion(state._cursor, state.getMarker(param._marker),
                                            re.compile(param._text), param._text2, state)
            else:
                # replace in the current line:
                line = state._lines[state._cursor._line]
                replaced, state._lastHits = re.subn(
                    param._text, param._text2, line)
                if line != replaced:
                    state._hasChanged = True
                    state._lines[state._cursor._line] = replaced
        elif name == 'set':
            if rule._param._marker is not None:
                text = state.textToMarker(rule._param._marker)
            elif rule._param._register2 is not None:
                text = state.textToMarker(rule._param._marker)
            elif rule._param._text is not None:
                text = rule._param.getText(state)
            else:
                state._logger.error('set: nothing to do')
                text = ''
            state.putToRegister(rule._param._register, text)
        elif name == 'state':
            name = rule._param._text
            if name == 'row':
                value = state._cursor._line + 1
            elif name == 'col':
                value = state._cursor._col + 1
            elif name == 'rows':
                value = len(state._lines)
            elif name.startswith('size-'):
                value = len(state.getRegister(name[5]))
            elif name.startswith('rows-'):
                value = state.getRegister(name[5]).count('\n')
            elif name == 'hits':
                value = state._lastHits
            else:
                value = '?'
            state._registers[rule._param._register] = str(value)
        elif name == 'swap':
            marker = state.getMarker(rule._param._marker)
            if marker is None:
                state._success = False
                state._logger.error(
                    'swap: marker {} is not defined'.format(rule._param._marker))
            else:
                state._tempRange.clone(state._cursor)
                state._cursor.clone(marker)
                marker.clone(state._tempRange)
                state._success = state.inRange()
        else:
            self._logger.error(
                'unknown command {} in {}'.format(name, rule._ruleType))

    @staticmethod
    def applyReplaceRegion(start, end, what, replacement, state):
        '''Replaces inside the region.
        @param start: first bound of the region
        @param end: second bound of the region
        @param what: the regular expression to search
        @param replacement: the string to replace
        @param state: a base.SearchRule.ProcessState instance
        '''
        if start.compare(end) > 0:
            start, end = end, start
        state._lastHits = 0
        if start._line == end._line:
            value = state._lines[start._line][start._col:end._col]
            value2, hits = what.subn(replacement, value)
            if value != value2:
                state._lastHits += hits
                state._hasChanged = True
                state._lines[start._line] = state._lines[start._line][0:start._col] + \
                    value2 + state._lines[end._line][end._col:]
        else:
            startIx = start._line
            if start._col > 0:
                value = state._lines[start._line][start._col:]
                value2, hits = what.subn(replacement, value)
                if value != value2:
                    state._lastHits += hits
                    state._hasChanged = True
                    state._lines[start._line] = state._lines[start._line][0:start._col] + value2
                startIx += 1
            for ix in range(startIx, end._line):
                value = state._lines[ix]
                value2, hits = what.subn(replacement, value)
                if value != value2:
                    state._lastHits += hits
                    state._hasChanged = True
                    state._lines[ix] = value2
            if end._col > 0:
                value = state._lines[end._line][0:end._col]
                value2, hits = what.subn(replacement, value)
                if value != value2:
                    state._lastHits += hits
                    state._hasChanged = True
                    state._lines[end._line] = value2 + \
                        state._lines[end._line][end._col:]

    def check(self):
        '''Tests the compiled rules, e.g. existence of labels.
        @return: None OK otherwise: the error message
        '''
        self._labels = {}
        ix = -1
        for rule in self._rules:
            ix += 1
            if rule._ruleType == '%':
                self._labels[rule._param] = ix
        for rule in self._rules:
            if rule._flowControl is not None:
                label = rule._flowControl._onSuccess
                if label.startswith('%') and label not in self._labels:
                    self._logger.error(
                        'unknown label (on success) {}'.format(label))
                    self._errorCount += 1
                label = rule._flowControl._onError
                if label.startswith('%') and label not in self._labels:
                    self._logger.error(
                        'unknown label (on error): {}'.format(label))
                    self._errorCount += 1
                if rule._ruleType == 'jump' and rule._param._text is not None and rule._param._text not in self._labels:
                    self._logger.error(
                        'unknown jump target: {}'.format(rule._text))
                    self._errorCount += 1
        rc = self._errorCount == 0
        return rc

    @staticmethod
    def describe():
        '''Describes the rule syntax.
        '''
        print(r'''A "rule" describes a single action: find a new position, set a marker/register, display...
A "register" is a container holding a string with a single uppercase letter as name, e.g. 'A'
A "marker" is a position in the text with a lowercase letter as name, e.g. "a"
A "label" is named position in the rule list delimited by '%', e.g. '%eve_not_found%'
Legend:
    D is any printable ascii character (delimiter) except blank and ':', e.g. '/' or "X"
    R is a uppercase character A..Z (register name), e.g. "Z"
    m is a lowercase ascii char a..z (marker name), e.g. "f"
    G is a decimal number, e.g. 0 or 12 (group number)
    cursor: the current position
Rules:
a label:
    <label>:
a regular expression for searching forwards:
    >D<expression>D[<range>]<search-options>
    FD<expression>D[<range>]<search-options>
a regular expression for searching backwards:
    <D<expression>D[<range>]<search-options>
    BD<expression>D[<range>]<search-options>
<search-option>:
    <lines> search only in the next/previous <lines> lines, e.g. >/Joe/8
    :<cols> search only in the next/previous <cols> columns, e.g. </Eve/:30
    i ignore case
    e position is behind the found pattern. Example: lines: ["abcd"] rule: >/bc/e cursor: 0-3
an absolute line/column <line>:<col>
    line and col are numbers starting with 1, e.g. 24:2
a relative line/column count [+-]<line>:[+-]<col>
    line and col can be positive or negative or 0, negative means backwards
an anchor: <anchor>
    'bol': begin of line 'eol': end of line
    'bonl': begin of next line 'eonl': end of next line
    'bopl': end of previous line 'eopl': end of previous line
    'bof': begin of file 'eof': end of file
<command>:
    add-R-m   adds the content from marker m until cursor onto register R
    add-R-S   adds the content of register S onto the register R
    add-R:D<text>D[<text-options>]
        add the text onto register R
    cut-m     deletes the content from marker m to the cursor
    cut-R-m   deletes the content from marker m to the cursor and store it into register R
    expr-R:D<operator><operand>D
        calculate R = R <operator> <operand>
        <operator>:
            '+', '-', '*', '/', '%'
        <operand>:
            a decimal number or $<register>
        Examples: expr-A:"*32" expr-Z:"+$F"
    group-G-R stores the group G of the last regular expression into register R
    insert-R  inserts the content of register R at the cursor. cursor is moved behind the insertion.
    insert:D<content>D[<text-options>]
        put the <content> at the cursor. cursor is moved behind the insertion.
    jump-m   cursor is get from marker m
    jump:<label>   next rule to process is behind label <label>
    mark-m  sets the marker m
    print-m  displays the content from marker m to the cursor
    print-R  displays the register R
    print:D<text>D<text-option>
        displays the <text>
    replace:D<expression>D<replacement>D[<repl-options>]
        replaces <expression> with <replacement> in the current line
    replace-m:D<expression>D<replacement>D[<repl-options>]
        replaces <expression> with <replacement> from marker m to cursor
    replace-R:D<expression>D<replacement>D[<repl-options>]
        replaces <expression> with <replacement> in register R
        <repl-option>:
            c=<count> the count of replacements in one line, e.g. c=12
            e=<char> esc char used as prefix of the register placeholder
                example: e=$ Than $A will be replaced in <expression> and <replacement>
                by the content of register 'A'
    set-R-m stores the content from marker m to register R
    set-R:D<text>D[<text-options>]
        stores the <text> into register R, e.g. set-A:"Hi!"
    state-R:D<variable>D
        store the variable into register R, e.g. state-A row
        <variable>:
            row: the cursor line number (1..N)
            col: the cursor column (1..N)
            rows: number of lines
            size-R: the length of the content of register R
            rows-R: the number of lines in register R
            hits: the number of hits of the last replacement command
    swap-m    swaps cursor and marker m
    <text-option>:
        e=<char>
            esc char used as prefix of the register placeholder. More info see replace
<flow-control>:
    Note: "successful" means: a pattern is found (search) or reposition is inside the range etc.
    Note: default behaviour: success:continue and error:error
    success:<reaction>
        reaction is done if the rule is finished with success
    error:<reaction>
        reaction is done if the rule is finished without success
    <reaction>:
    continue
        continues with the next rule
    stop
        stop processing
    error
        stop processing with an error message
    %<label>%
        continue processing at label %<label>%
Examples:
>/jonny/:80i success:stop >/eve/4 error:stop print "eve found but not jonny"
    search "jonny" but only in the next 80 columns, ignore case
    stop if found. If not found: search "eve", but only 4 lines
    stop without error if not found. if found display "eve found but not jonny"
>/Address:/ error:error >/EMail:/s
    if "Address" is not found, the result is "not found"
    otherwise if "EMail" is found behind, the new base.SearchRule.Position is at "Email:" if not the new position is "Address"
10:0 error:%missingLines% >/Name:\s+/ label-n >/[A-Za-z ]+/ print-N-n success:stop;%missingLines% print:"less than 10 lines"
    searches for a name starting in line 10. Prints an informative message if line 10 does not exist
10:0 >/Firstname:\s+/e label-f >/[A-Za-z ]+/e store-F-n
print:"Full name: " print-F print:" " print-N
    this example searches for firstname and name below line 10 and display them
''')

    @staticmethod
    def parseAnchor(match):
        '''Parses and stores an anchor.
        'bol': begin of line 'eol': end of line
        'bonl': begin of next line 'eonl': end of next line
        'bopl': end of previous line 'eopl': end of previous line
        'bof': top of file 'eof': end of file
        @param match: the match of the regular expression
        '''
        rule = match.group(0)
        parts = rule.split(';')
        name = parts[0].strip()
        rule = base.SearchRule.SearchRule('anchor', name)
        return rule

    def parseCommand(self, rule):
        '''Parses a command.
        A command is a rule except searching or repositioning:
        @see SearchRuleList.describe() for details.
        @param rule: the rule to parse
        @return: True: success False: error
        '''
        def isRegister(name):
            return name is not None and 'A' <= name[0] <= 'Z'

        def isMarker(name):
            return name is not None and 'a' <= name[0] <= 'z'

        def isGroup(name):
            return name is not None and '0' <= name[0] <= '9'

        def getText(param):
            text = None
            esc = None
            if param.startswith(':'):
                param = param[1:]
            if param != '':
                sep = param[0]
                ixEnd = param.find(sep, 1)
                if ixEnd > 0:
                    text = param[1:ixEnd]
                    rest = param[ixEnd + 1:]
                    if rest.startswith('e='):
                        esc = rest[2]
            return (text, esc)
        match = SearchRuleList.__reCommand.match(rule)
        success = True
        if match is None:
            success = self.parseError('missing command name')
        else:
            name = match.group(1)
            var1 = None if match.lastindex < 2 else match.group(2)[1:]
            var2 = None if match.lastindex < 3 else match.group(3)[1]
            params = rule[len(match.group(0)):].lstrip()
            text, esc = getText(params)
            if name == 'add':
                # add-R-m
                # add-R-S
                # add-R D<text>D
                if isRegister(var2) and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, register2=var2))
                elif isMarker(var2) and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, marker=var2))
                elif var2 is None and text is not None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: add-R-m or add_R-S or add-R DtextD expected')
            elif name == 'cut':
                # cut-m
                # cut-R-m
                if isMarker(var1) and var2 is None and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(marker=var1))
                elif isRegister(var1) and isMarker(var2) and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        marker=var2, register=var1))
                elif isRegister(var2) and isMarker(var1) and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        marker=var1, register=var2))
                else:
                    success = self.parseError(
                        'invalid syntax: cut-m or cut-R-m expected')
            elif name == 'expr':
                # expr-R-S:D<operator>D
                #    calculate R = R <operator> S
                #    <operator>:
                #        '+', '-', '*', '/', '%'
                # expr-R:D<operator><constant>D
                #    calculate R = R <operator> <constant>
                matcher = SearchRuleList.__reRuleExprParams.match(text)
                if matcher is None:
                    success = self.parseError(
                        '<operator><operand> expected, not "{}"'.format(text))
                elif isRegister(var1) and var2 is None and text is not None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, text=text, escChar='$'))
                else:
                    success = self.parseError(
                        'invalid syntax: expr-R:"<operator><operand>" expected')
            elif name == 'group':
                # group-G-R
                if isGroup(var1) and isRegister(var2) and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        group=int(var1), register=var2))
                else:
                    success = self.parseError(
                        'invalid syntax: group-G-R expected')
            elif name == 'insert':
                # insert-R
                # insert D<content>D
                if isRegister(var1) and var2 is None and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(register=var1))
                elif var1 is None and var2 is None:
                    self.appendCommand(
                        name, base.SearchRule.CommandData(text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: insert-R or insert DtextD expected')
            elif name == 'jump':
                # jump-m
                # jump-L
                if isMarker(var1) and var2 is None:
                    self.appendCommand(name, base.SearchRule.CommandData(marker=var1))
                elif var1 is None and params != '' and params.startswith(':%') and params[-1] == '%':
                    self.appendCommand(name, base.SearchRule.CommandData(text=params[1:]))
                else:
                    success = self.parseError(
                        'invalid syntax: jump-m or jump:<label> expected')
            elif name == 'mark':
                # mark-m
                if isMarker(var1) and var2 is None:
                    self.appendCommand(name, base.SearchRule.CommandData(marker=var1))
                else:
                    success = self.parseError(
                        'invalid syntax: mark-m expected')
            elif name == 'print':
                # print-m
                # print-R
                # print D<text>D display text
                if isMarker(var1) and var2 is None and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(marker=var1))
                elif isRegister(var1) and var2 is None and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(register=var1))
                elif var1 is None and var2 is None and text is not None:
                    self.appendCommand(
                        name, base.SearchRule.CommandData(text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: print-m or print-R or print DtextD expected"')
            elif name == 'replace':
                # replace-m D<expression>D<replacement>D
                # replace-R D<expression>D<replacement>D
                what = None
                if len(params) > 3:
                    sep = params[0]
                    ix1 = params.find(sep, 1)
                    ix2 = params.find(sep, ix1 + 1)
                    if ix1 < 0 or ix2 < 0:
                        what = params[1:ix1]
                        replacement = params[ix1 + 1:ix2]
                elif isMarker(var1) and var2 is None and what is not None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        marker=var1, text=what, text2=replacement))
                elif isRegister(var1) and var2 is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, text=what, text2=replacement))
                else:
                    success = self.parseError(
                        'invalid syntax: replace-m:DwhatDwithD or replace-R:DwhatDwithD expected')
            elif name == 'set':
                # set-R-m
                # set-R D<text>D
                if isRegister(var1) and isMarker(var2) and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, marker=var2))
                elif isRegister(var1) and var2 is None and text is not None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: set-R-m or set-R DtextD expected')
            elif name == 'swap':
                # swap-m
                if isMarker(var1) and var2 is None and text is None:
                    self.appendCommand(name, base.SearchRule.CommandData(marker=var1))
                else:
                    success = self.parseError(
                        'invalid syntax: swap-m expected')
            elif name == 'state':
                # state-R:D<variable>D
                var3 = None if text is None or SearchRuleList.__reRuleStateParam.match(
                    text) is None else text
                if isRegister(var1) and var2 is None and var3 is not None:
                    self.appendCommand(name, base.SearchRule.CommandData(
                        register=var1, text=var3))
                else:
                    success = self.parseError(
                        'invalid syntax: state-R:"{row|col|rows|size-R|rows-R}" expected')
            else:
                success = self.parseError(
                    'unknown name {} in {}'.format(name, rule))
        return success

    def parseError(self, message):
        '''Logs a parser error.
        @param message: the error message
        @return: False (for chaining)
        '''
        self._logger.error('{}: {} rule: {}'.format(
            self._col, message, self._currentRule))
        self._errorCount += 1
        return False

    def parseRules(self, rules):
        '''Parses the rules given as string and put it in a prepared form into the list
        @param rules: the rules as string,
            Example: '>/logfile:/ -2:0 bol':
            search forwards "logfile:" go backward 2 line 0 column, go to begin of line
        '''
        self._col = 0
        rules = rules.lstrip('\t\n\r ;')
        while rules != '':
            currentRule = None
            lengthCommand = None
            ready = False
            if rules.startswith('replace'):
                lengthCommand = self.parseRuleReplace(rules)
                ready = True
            if not ready:
                match = SearchRuleList.__reRule.match(rules)
                if match is None:
                    break
                else:
                    singleRule = self._currentRule = match.group(0)
                    lengthCommand = len(singleRule)
                    ruleType = singleRule[0]
                    if ruleType in ('<', '>', 'F', 'B'):
                        sep = singleRule[1]
                        ixEnd = singleRule.find(sep, 2)
                        param = SearchData()
                        msg = param.setData(
                            singleRule[2:ixEnd], singleRule[ixEnd + 1:])
                        if msg is not None:
                            self.parseError(msg)
                        if ruleType == 'F':
                            ruleType = '>'
                        elif ruleType == 'B':
                            ruleType = '<'
                        currentRule = base.SearchRule.SearchRule(ruleType, param)
                    elif ruleType == '%':
                        # label:
                        currentRule = base.SearchRule.SearchRule(ruleType, singleRule[0:-1])
                    elif '0' <= ruleType <= '9':
                        currentRule = base.SearchRule.SearchRule(
                            '+', [int(match.group(1)), int(match.group(2)), ':'])
                    elif ruleType in ('+', '-'):
                        # reposition:
                        factor = 1 if ruleType == '+' else -1
                        currentRule = base.SearchRule.SearchRule('+', [factor * int(match.group(1)),
                                                 factor * int(match.group(2)), '+'])
                    elif singleRule.startswith('bo') or singleRule.startswith('eo'):
                        currentRule = SearchRuleList.parseAnchor(match)
                    else:
                        self.parseCommand(singleRule)
            if currentRule is not None:
                self._rules.append(currentRule)
            if lengthCommand == 0:
                break
            self._col += lengthCommand
            rules = rules[lengthCommand:].lstrip('\t\n\r ;')
            matcher = SearchRuleList.__reFlowControl.match(rules)
            if matcher is not None:
                controls = matcher.group(0)
                if self._rules:
                    self._rules[len(self._rules) -
                                1]._flowControl.setControl(controls)
                length = len(controls)
                self._col += length
                rules = rules[length:].lstrip('\t\n\r ;')
        if rules != '':
            self.parseError('not recognized input: ' + rules)
        rc = self._errorCount == 0
        return rc

    def parseRuleReplace(self, rules):
        '''Parses the 'replace' command.
        @param rules: the rules starting with 'replace'...
        @return: the length of the replace command
        '''
        rc = len('replace')
        # .......A.........  A..1.....12..2..3..3..4...4
        # replace(?:-[a-zA-Z])?:([^\s])(.+)\1(.*)\1(e=.)?')
        matcher = SearchRuleList.__reRuleReplace.match(rules)
        if matcher is None:
            self.parseError('wrong syntax for replace: ' +
                            base.StringUtils.limitLength(rules, 40))
        else:
            name = None if rules[7] != '-' else rules[8]
            register = None if name is None or name > 'Z' else name
            marker = None if name is None or name < 'a' else name
            what = matcher.group(2)
            replacement = matcher.group(3)
            options = matcher.group(4)
            escChar = None if options is None or options == '' else options[2]
            param = base.SearchRule.CommandData(register, escChar, marker, what, replacement)
            rule = base.SearchRule.SearchRule('replace', param)
            self._rules.append(rule)
            rc = len(matcher.group(0))
        return rc

    def startTrace(self, filename, append=False):
        '''Starts tracing the rule execution.
        @param filename: the name of the trace file
        @param append: True: the trace will be appended
        '''
        self._fpTrace = open(filename, 'a' if append else 'w')
        self._fpTrace.write('= start\n')

    def stopTrace(self):
        '''Stops tracing the rule execution.
        @param filename: the name of the trace file
        @param append: True: the trace will be appended
        '''
        if self._fpTrace is not None:
            self._fpTrace.close()
            self._fpTrace = None

    def trace(self, index, after, state):
        '''Traces the state applying the current rule.
        @param index: index in _rules
        @param after: True: called after processing the rule
        @param state: the base.SearchRule.ProcessState instance
        '''
        rule = self._rules[index]
        rc = rule.state(after, state)
        if after:
            success = 'success' if state._success else 'error'
            self._fpTrace.write('{:03d}: {} {}\n    {}\n'.format(
                index, success, rule.toString(), rc))


class SearchData:
    '''Data for seaching (forward and backward)
    '''
    __reRange = re.compile(r':?(\d+)')

    def __init__(self):
        '''Constructor:
        @param igoreCase: searching 'a' finds 'A' and 'a'
        @param useEnd: True: the cursor is set behind the found string
            False: the cursor is set at the beginning of the found string
        '''
        self._ignoreCase = None
        self._useEnd = None
        self._rangeColumns = None
        self._rangeLines = None
        self._regExpr = None

    def setData(self, string, options):
        '''Sets the variables by inspecting the string and the options.
        @param string: the search string (regular expression)
        @param options: the search options, e.g. 'i' for ignore case
        @return: None: success otherwise: an error message
        '''
        rc = None
        match = SearchData.__reRange.match(options)
        if match is not None:
            if options.startswith(':'):
                self._rangeColumns = int(match.group(1))
            else:
                self._rangeLines = int(match.group(1))
            options = options[len(match.group(0)):]
        options = options.rstrip()
        while options != '':
            if options.startswith('i'):
                self._ignoreCase = True
            elif options.startswith('e'):
                self._useEnd = True
            else:
                rc = 'unknown search option: ' + options[0]
                break
            options = options[1:].rstrip()
        self._regExpr = re.compile(
            string, base.Const.IGNORE_CASE if self._ignoreCase else 0)
        return rc

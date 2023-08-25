'''
SearchRuleList.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re

from base import Const
from base import StringUtils
from text import SearchRule
from base import Logger


class SearchRuleList:
    '''A list of rules to find a new position or do some other things.
    @see describe() for detailed description.
    '''
    # ..........................rule
    # .........................1
    reRule = re.compile(r'%[a-zA-Z_]\w*%:'
                        #        rule
                        # ........A
                        + r'|(?:[be]of|[be]o[pn]?l'
                        # ...........line........col
                          # .............1...1......2...2
                          + r'|[+-]?(\d+):[+-]?(\d+)'
                          # ..............sep.....sep rows/cols
                          # ..............3..3........C.......C
                          + r'|[<>FB](\S).+?\3\s?(?::?\d+)?\s?[ie]{0,2}'
                          # .command.name
                          # .......4E
                          + r'|((?:add|cut|expr|group|insert|jump'
                          # ........................................./name
                          # .........................................E
                          + r'|mark|print|replace|set|state|swap)'
                          # ..suffix1 name...............suffix2.........text.delim......txt-opt /t /command
                          # ......F...G........... ....GF.H...........H.I...5.....5.....J......J.I.4
                          + r'(?:-(?:[a-zA-Z]|\d\d?))?(?:-[a-zA-Z])?(?::([^\s]).*?\5(?:e=\S)?)?)'
                          # .......A
                          + r')')
    reRuleExprParams = re.compile(r'[-+/*%](\$[A-Z]|\d+)?')
    # .........................1......12..............2.3.........3
    reCommand = re.compile(r'([a-z]+)(-[a-zA-Z]|-\d+)?(-[a-zA-Z])?')
    reRuleStateParam = re.compile(r'rows?|col|size-[A-Z]|rows-[A-Z]|hits')
    reFlowControl = re.compile(
        r'(success|error):(continue|error|stop|%\w+%)')
    # ....................................A.........  A..1......12...2..3..3..4...........4
    reRuleReplace = re.compile(
        r'replace(?:-[a-zA-Z])?:([^\s])(.+?)\1(.*?)\1(e=.|,|c=\d+)*')
    # x=re.compile(r'replace:([^\s])(.+)\1(.*)\1(e=.)?')

    def __init__(self, logger: Logger.Logger, rules=None):
        '''Constructor.
        @param rules: None or the rules as string
            Example: '>/logfile:/ -2:0 bol':
            search forwards "logfile:" go backward 2 line 0 column, go to begin of line
        '''
        self.logger = logger
        self.col = 0
        self.currentRule = ''
        self.errorCount = 0
        self.rules = []
        self.labels = {}
        self.markers = {}
        self.fpTrace = None
        self.maxLoops = None
        if rules is not None:
            self.parseRules(rules)

    def appendCommand(self, name: str, commandData: SearchRule.CommandData):
        '''Stores the command data in the _rules.
        Stores markers defined by "mark".
        Tests used markers for a previous definition.
        @param name: the name of the command, e.g. 'add'. Will be used as _ruleType
        @param commandData: an instance of SearchRule.CommandData
        '''
        if name == 'mark':
            self.markers[commandData.marker] = self.col
        elif commandData.marker is not None and commandData.marker not in self.markers:
            self.parseError(
                f'marker {commandData.marker} was not previously defined')
        self.rules.append(SearchRule.SearchRule(name, commandData))

    def apply(self, state: SearchRule.ProcessState):
        '''Executes the internal stored rules in a given list of lines inside a range.
        @param state: IN/OUT IN: the context to search OUT: the state at the end of applying the rule list
        '''
        ix = 0
        count = 0
        maxCount = len(state.lines) * state.maxLoops
        while ix < len(self.rules):
            if count >= maxCount:
                state.logger.error(
                    f'SearchRule.SearchRule.apply(): to many loops: {self.maxLoops}')
                break
            item = self.rules[ix]
            if self.fpTrace is not None:
                ixTrace = ix
                self.trace(ixTrace, False, state)
            flowControl = self.rules[ix].flowControl
            ix += 1
            if item.ruleType == '>':
                item.searchForward(state)
            elif item.ruleType == '<':
                item.searchBackward(state)
            elif item.ruleType == '%':
                # label
                pass
            elif item.ruleType in ('anchor', '+'):
                item.reposition(state)
            elif item.ruleType >= 'p':
                self.applyCommand2(item, state)
            else:
                ix2 = self.applyCommand1(item, state)
                if ix2 is not None:
                    ix = ix2
            if self.fpTrace is not None:
                self.trace(ixTrace, True, state)
            if flowControl is not None:
                reaction = flowControl.onSuccess if state.success else flowControl.onError
                if reaction == 'c':
                    pass
                elif reaction == 's':
                    break
                elif reaction == 'e':
                    self.logger.error('{} stopped with error')
                    break
                elif reaction in self.labels:
                    ix = self.labels[reaction] + 1

    def applyCommand1(self, rule: SearchRule.SearchRule, state: SearchRule.ProcessState):
        '''Executes the action named 'a*' to 'p*' (exclusive)
        @param processState: IN/OUT IN: the context to search OUT: the state at the end of applying the rule list
        @return: None: normal processing otherwise: the index of the next rule to process
        '''
        rc = None
        name = rule.ruleType
        checkPosition = False
        if name == 'add':
            # add-R-m
            # add-R-S
            # add-R D<text>D
            if rule.param.marker is not None:
                text = state.textToMarker(rule.param.marker)
            elif rule.param.register2 is not None:
                text = state.getRegister(rule.param.register2)
            elif rule.param.text is not None:
                text = rule.param.getText(state)
            else:
                state.logger.error('add: nothing to do')
                text = ''
            state.putToRegister(rule.param.register, text, append=True)
        elif name == 'cut':
            # cut-m
            # cut-R-m
            if rule.param.register is not None:
                text = state.textToMarker(rule.param.marker)
                state.putToRegister(rule.param.register, text)
            state.deleteToMarker(rule.param.marker)
        elif name == 'expr':
            # expr-R:"+4"
            value = StringUtils.asInt(
                state.getRegister(rule.param.register), 0)
            param = rule.param.getText(state)
            value2 = StringUtils.asInt(param[1:], 0)
            operator = param[0]
            if operator == '+':
                value += value2
            elif operator == '-':
                value -= value2
            elif operator == '*':
                value *= value2
            elif operator == '/':
                if value2 == 0:
                    state.success = self.logger.error(
                        'division by 0 is not defined')
                else:
                    value //= value2
            elif operator == '%':
                if value2 == 0:
                    state.success = self.logger.error(
                        'modulo 0 is not defined')
                else:
                    value %= value2
            state.registers[rule.param.register] = str(value)
        elif name == 'insert':
            # insert-R
            # insert D<content>D
            text = ''
            if rule.param.register is not None:
                text = state.getRegister(rule.param.register)
            elif rule.param.text is not None:
                text = rule.param.getText(state)
            state.insertAtCursor(text)
        elif name == 'group':
            # group-G-R
            state.success = state.lastMatch is not None and state.lastMatch.lastindex <= rule.param.group
            if state.success:
                text = '' if state.lastMatch.lastindex < rule.param.group else state.lastMatch.group(
                    rule.param.group)
                state.putToRegister(rule.param.register, text)
        elif name == 'jump':
            if rule.param.marker is not None:
                state.cursor.clone(state.getMarker(rule.param.marker))
                checkPosition = True
            else:
                rc = self.labels[rule.param.text]
        elif name == 'mark':
            state.setMarker(rule.param.marker)
        else:
            state.logger.error('applyCommand1: unknown command')
        if checkPosition:
            state.success = state.inRange()
        return rc

    def applyCommand2(self, rule: SearchRule.SearchRule, state: SearchRule.ProcessState):
        '''Executes the actions named 'p*' to 'z*' (inclusive)
        @param processState: IN/OUT IN: the context to search OUT: the state at the end of applying the rule list
        '''
        name = rule.ruleType
        if name == 'print':
            state.success = True
            if rule.param.register is not None:
                print(state.getRegister(rule.param.register))
            elif rule.param.marker is not None:
                print(state.textToMarker(rule.param.marker))
            elif rule.param.text is not None:
                print(rule.param.getText(state))
        elif name == 'replace':
            param = rule.param
            if param.register is not None:
                replaced, state.lastHits = re.subn(
                    param.text, param.text2, state.getRegister(param.register))
                state.registers[param.register] = replaced
            elif param.marker is not None:
                SearchRuleList.applyReplaceRegion(state.cursor, state.getMarker(param.marker),
                                                  re.compile(param.text), param.text2, state)
            else:
                # replace in the current line:
                line = state.lines[state.cursor.line]
                replaced, state.lastHits = re.subn(
                    param.text, param.text2, line)
                if line != replaced:
                    state.hasChanged = True
                    state.lines[state.cursor.line] = replaced
        elif name == 'set':
            if rule.param.marker is not None:
                text = state.textToMarker(rule.param.marker)
            elif rule.param.register2 is not None:
                text = state.textToMarker(rule.param.marker)
            elif rule.param.text is not None:
                text = rule.param.getText(state)
            else:
                state.logger.error('set: nothing to do')
                text = ''
            state.putToRegister(rule.param.register, text)
        elif name == 'state':
            name = rule.param.text
            if name == 'row':
                value = state.cursor.line + 1
            elif name == 'col':
                value = state.cursor.col + 1
            elif name == 'rows':
                value = len(state.lines)
            elif name.startswith('size-'):
                value = len(state.getRegister(name[5]))
            elif name.startswith('rows-'):
                value = state.getRegister(name[5]).count('\n')
            elif name == 'hits':
                value = state.lastHits
            else:
                value = '?'
            state.registers[rule.param.register] = str(value)
        elif name == 'swap':
            marker = state.getMarker(rule.param.marker)
            if marker is None:
                state.success = False
                state.logger.error(
                    f'swap: marker {rule.param.marker} is not defined')
            else:
                state.tempRange.clone(state.cursor)
                state.cursor.clone(marker)
                marker.clone(state.tempRange)
                state.success = state.inRange()
        else:
            self.logger.error(
                f'unknown command {name} in {rule.ruleType}')

    @staticmethod
    def applyReplaceRegion(start, end, what, replacement: str, state: SearchRule.ProcessState):
        '''Replaces inside the region.
        @param start: first bound of the region
        @param end: second bound of the region
        @param what: the regular expression to search
        @param replacement: the string to replace
        @param state: a SearchRule.ProcessState instance
        '''
        if start.compare(end) > 0:
            start, end = end, start
        state.lastHits = 0
        if start.line == end.line:
            value = state.lines[start.line][start.col:end.col]
            value2, hits = what.subn(replacement, value)
            if value != value2:
                state.lastHits += hits
                state.hasChanged = True
                state.lines[start.line] = state.lines[start.line][0:start.col] + \
                    value2 + state.lines[end.line][end.col:]
        else:
            startIx = start.line
            if start.col > 0:
                value = state.lines[start.line][start.col:]
                value2, hits = what.subn(replacement, value)
                if value != value2:
                    state.lastHits += hits
                    state.hasChanged = True
                    state.lines[start.line] = state.lines[start.line][0:start.col] + value2
                startIx += 1
            for ix in range(startIx, end.line):
                value = state.lines[ix]
                value2, hits = what.subn(replacement, value)
                if value != value2:
                    state.lastHits += hits
                    state.hasChanged = True
                    state.lines[ix] = value2
            if end.col > 0:
                value = state.lines[end.line][0:end.col]
                value2, hits = what.subn(replacement, value)
                if value != value2:
                    state.lastHits += hits
                    state.hasChanged = True
                    state.lines[end.line] = value2 + \
                        state.lines[end.line][end.col:]

    def check(self):
        '''Tests the compiled rules, e.g. existence of labels.
        @return: None OK otherwise: the error message
        '''
        self.labels = {}
        ix = -1
        for rule in self.rules:
            ix += 1
            if rule.ruleType == '%':
                self.labels[rule.param] = ix
        for rule in self.rules:
            if rule.flowControl is not None:
                label = rule.flowControl.onSuccess
                if label.startswith('%') and label not in self.labels:
                    self.logger.error(
                        f'unknown label (on success) {label}')
                    self.errorCount += 1
                label = rule.flowControl.onError
                if label.startswith('%') and label not in self.labels:
                    self.logger.error(
                        f'unknown label (on error): {label}')
                    self.errorCount += 1
                if rule.ruleType == 'jump' and rule.param.text is not None and rule.param.text not in self.labels:
                    self.logger.error(
                        f'unknown jump target: {rule.text}')
                    self.errorCount += 1
        rc = self.errorCount == 0
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
    otherwise if "EMail" is found behind, the new SearchRule.Position is at "Email:" if not the new position is "Address"
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
        rule = SearchRule.SearchRule('anchor', name)
        return rule

    def parseCommand(self, rule: SearchRule.SearchRule):
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
        match = SearchRuleList.reCommand.match(rule)
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
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, register2=var2))
                elif isMarker(var2) and text is None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, marker=var2))
                elif var2 is None and text is not None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: add-R-m or add_R-S or add-R DtextD expected')
            elif name == 'cut':
                # cut-m
                # cut-R-m
                if isMarker(var1) and var2 is None and text is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(marker=var1))
                elif isRegister(var1) and isMarker(var2) and text is None:
                    self.appendCommand(name, SearchRule.CommandData(
                        marker=var2, register=var1))
                elif isRegister(var2) and isMarker(var1) and text is None:
                    self.appendCommand(name, SearchRule.CommandData(
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
                matcher = SearchRuleList.reRuleExprParams.match(text)
                if matcher is None:
                    success = self.parseError(
                        f'<operator><operand> expected, not "{text}"')
                elif isRegister(var1) and var2 is None and text is not None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, text=text, escChar='$'))
                else:
                    success = self.parseError(
                        'invalid syntax: expr-R:"<operator><operand>" expected')
            elif name == 'group':
                # group-G-R
                if isGroup(var1) and isRegister(var2) and text is None:
                    self.appendCommand(name, SearchRule.CommandData(
                        group=int(var1), register=var2))
                else:
                    success = self.parseError(
                        'invalid syntax: group-G-R expected')
            elif name == 'insert':
                # insert-R
                # insert D<content>D
                if isRegister(var1) and var2 is None and text is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(register=var1))
                elif var1 is None and var2 is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: insert-R or insert DtextD expected')
            elif name == 'jump':
                # jump-m
                # jump-L
                if isMarker(var1) and var2 is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(marker=var1))
                elif var1 is None and params != '' and params.startswith(':%') and params[-1] == '%':
                    self.appendCommand(
                        name, SearchRule.CommandData(text=params[1:]))
                else:
                    success = self.parseError(
                        'invalid syntax: jump-m or jump:<label> expected')
            elif name == 'mark':
                # mark-m
                if isMarker(var1) and var2 is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(marker=var1))
                else:
                    success = self.parseError(
                        'invalid syntax: mark-m expected')
            elif name == 'print':
                # print-m
                # print-R
                # print D<text>D display text
                if isMarker(var1) and var2 is None and text is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(marker=var1))
                elif isRegister(var1) and var2 is None and text is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(register=var1))
                elif var1 is None and var2 is None and text is not None:
                    self.appendCommand(
                        name, SearchRule.CommandData(text=text, escChar=esc))
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
                    self.appendCommand(name, SearchRule.CommandData(
                        marker=var1, text=what, text2=replacement))
                elif isRegister(var1) and var2 is None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, text=what, text2=replacement))
                else:
                    success = self.parseError(
                        'invalid syntax: replace-m:DwhatDwithD or replace-R:DwhatDwithD expected')
            elif name == 'set':
                # set-R-m
                # set-R D<text>D
                if isRegister(var1) and isMarker(var2) and text is None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, marker=var2))
                elif isRegister(var1) and var2 is None and text is not None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, text=text, escChar=esc))
                else:
                    success = self.parseError(
                        'invalid syntax: set-R-m or set-R DtextD expected')
            elif name == 'swap':
                # swap-m
                if isMarker(var1) and var2 is None and text is None:
                    self.appendCommand(
                        name, SearchRule.CommandData(marker=var1))
                else:
                    success = self.parseError(
                        'invalid syntax: swap-m expected')
            elif name == 'state':
                # state-R:D<variable>D
                var3 = None if text is None or SearchRuleList.reRuleStateParam.match(
                    text) is None else text
                if isRegister(var1) and var2 is None and var3 is not None:
                    self.appendCommand(name, SearchRule.CommandData(
                        register=var1, text=var3))
                else:
                    success = self.parseError(
                        'invalid syntax: state-R:"{row|col|rows|size-R|rows-R}" expected')
            else:
                success = self.parseError(
                    f'unknown name {name} in {rule}')
        return success

    def parseError(self, message: str):
        '''Logs a parser error.
        @param message: the error message
        @return: False (for chaining)
        '''
        self.logger.error(f'{self.col}: {message} rule: {self.currentRule}')
        self.errorCount += 1
        return False

    def parseRules(self, rules):
        '''Parses the rules given as string and put it in a prepared form into the list
        @param rules: the rules as string,
            Example: '>/logfile:/ -2:0 bol':
            search forwards "logfile:" go backward 2 line 0 column, go to begin of line
        '''
        self.col = 0
        rules = rules.lstrip('\t\n\r ;')
        while rules != '':
            currentRule = None
            lengthCommand = None
            ready = False
            if rules.startswith('replace'):
                lengthCommand = self.parseRuleReplace(rules)
                ready = True
            if not ready:
                match = SearchRuleList.reRule.match(rules)
                if match is None:
                    break
                singleRule = self.currentRule = match.group(0)
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
                    currentRule = SearchRule.SearchRule(ruleType, param)
                elif ruleType == '%':
                    # label:
                    currentRule = SearchRule.SearchRule(
                        ruleType, singleRule[0:-1])
                elif '0' <= ruleType <= '9':
                    currentRule = SearchRule.SearchRule(
                        '+', [int(match.group(1)), int(match.group(2)), ':'])
                elif ruleType in ('+', '-'):
                    # reposition:
                    factor = 1 if ruleType == '+' else -1
                    currentRule = SearchRule.SearchRule('+', [factor * int(match.group(1)),
                                                              factor * int(match.group(2)), '+'])
                elif singleRule.startswith('bo') or singleRule.startswith('eo'):
                    currentRule = SearchRuleList.parseAnchor(match)
                else:
                    self.parseCommand(singleRule)
            if currentRule is not None:
                self.rules.append(currentRule)
            if lengthCommand == 0:
                break
            self.col += lengthCommand
            rules = rules[lengthCommand:].lstrip('\t\n\r ;')
            matcher = SearchRuleList.reFlowControl.match(rules)
            if matcher is not None:
                controls = matcher.group(0)
                if self.rules:
                    self.rules[len(self.rules) -
                               1].flowControl.setControl(controls)
                length = len(controls)
                self.col += length
                rules = rules[length:].lstrip('\t\n\r ;')
        if rules != '':
            self.parseError('not recognized input: ' + rules)
        rc = self.errorCount == 0
        return rc

    def parseRuleReplace(self, rules):
        '''Parses the 'replace' command.
        @param rules: the rules starting with 'replace'...
        @return: the length of the replace command
        '''
        rc = len('replace')
        # .......A.........  A..1.....12..2..3..3..4...4
        # replace(?:-[a-zA-Z])?:([^\s])(.+)\1(.*)\1(e=.)?')
        matcher = SearchRuleList.reRuleReplace.match(rules)
        if matcher is None:
            self.parseError('wrong syntax for replace: ' +
                            StringUtils.limitLength(rules, 40))
        else:
            name = None if rules[7] != '-' else rules[8]
            register = None if name is None or name > 'Z' else name
            marker = None if name is None or name < 'a' else name
            what = matcher.group(2)
            replacement = matcher.group(3)
            options = matcher.group(4)
            escChar = None if options is None or options == '' else options[2]
            param = SearchRule.CommandData(
                register, escChar, marker, what, replacement)
            rule = SearchRule.SearchRule('replace', param)
            self.rules.append(rule)
            rc = len(matcher.group(0))
        return rc

    def startTrace(self, filename: str, append: bool=False):
        '''Starts tracing the rule execution.
        @param filename: the name of the trace file
        @param append: True: the trace will be appended
        '''
        # pylint: disable-next=consider-using-with
        self.fpTrace = open(filename, 'a' if append else 'w', encoding='utf-8')
        self.fpTrace.write('= start\n')

    def stopTrace(self):
        '''Stops tracing the rule execution.
        @param filename: the name of the trace file
        @param append: True: the trace will be appended
        '''
        if self.fpTrace is not None:
            self.fpTrace.close()
            self.fpTrace = None

    def trace(self, index: int, after: bool, state: SearchRule.ProcessState):
        '''Traces the state applying the current rule.
        @param index: index in _rules
        @param after: True: called after processing the rule
        @param state: the SearchRule.ProcessState instance
        '''
        rule = self.rules[index]
        rc = rule.state(after, state)
        if after:
            success = 'success' if state.success else 'error'
            self.fpTrace.write(f'{index:03d}: {success} {rule.toString()}\n    {rc}\n')


# pylint: disable-next=too-few-public-methods
class SearchData:
    '''Data for seaching (forward and backward)
    '''
    reRange = re.compile(r':?(\d+)')

    def __init__(self):
        '''Constructor:
        @param igoreCase: searching 'a' finds 'A' and 'a'
        @param useEnd: True: the cursor is set behind the found string
            False: the cursor is set at the beginning of the found string
        '''
        self.ignoreCase = None
        self.useEnd = None
        self.rangeColumns = None
        self.rangeLines = None
        self.regExpr = None

    def setData(self, string: str, options: str):
        '''Sets the variables by inspecting the string and the options.
        @param string: the search string (regular expression)
        @param options: the search options, e.g. 'i' for ignore case
        @return: None: success otherwise: an error message
        '''
        rc = None
        match = SearchData.reRange.match(options)
        if match is not None:
            if options.startswith(':'):
                self.rangeColumns = int(match.group(1))
            else:
                self.rangeLines = int(match.group(1))
            options = options[len(match.group(0)):]
        options = options.rstrip()
        while options != '':
            if options.startswith('i'):
                self.ignoreCase = True
            elif options.startswith('e'):
                self.useEnd = True
            else:
                rc = 'unknown search option: ' + options[0]
                break
            options = options[1:].rstrip()
        self.regExpr = re.compile(
            string, Const.IGNORE_CASE if self.ignoreCase else 0)
        return rc

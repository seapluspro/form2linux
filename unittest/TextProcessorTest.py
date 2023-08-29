'''
TextProcessorTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import unittest
from base import FileHelper
from base import MemoryLogger
from text import TextProcessor

def inDebug(): return False

class TextProcessorTest(unittest.TestCase):

    def setUp(self):
        self._trace = FileHelper.tempFile('rules.log', 'trace')
        self._logger = MemoryLogger.MemoryLogger(4)

    def testBasics(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        self.assertEqual(0, processor.logger.errors())

    def testReplace(self):
        if inDebug(): return
        content = '''# simple example? complete example?
[Test]
intVar = 993
strVar = "abc $strVar"
'''
        processor = TextProcessor.TextProcessor(self._logger)
        processor.setContent(content)
        self.assertEqual(1, processor.replace('strVar', 'stringVar'))
        self.assertEqual('''# simple example? complete example?
[Test]
intVar = 993
stringVar = "abc $stringVar"
''', '\n'.join(processor.lines))

        processor.setContent(content)
        self.assertEqual(3, processor.replace('([a-z]+)Var', 'var_%1', '%', countHits=True))
        self.assertEqual('''# simple example? complete example?
[Test]
var_int = 993
var_str = "abc $var_str"
''', '\n'.join(processor.lines))

        processor.setContent(content)
        self.assertEqual(1, processor.replace('example?', 'sample?', noRegExpr=True))
        self.assertEqual('''# simple sample? complete sample?
[Test]
intVar = 993
strVar = "abc $strVar"
''', '\n'.join(processor.lines))

        processor.setContent(content)
        self.assertEqual(2, processor.replace('example?', 'sample?', noRegExpr=True, countHits=True))
        self.assertEqual('''# simple sample? complete sample?
[Test]
intVar = 993
strVar = "abc $strVar"
''', '\n'.join(processor.lines))

    def testReplaceEscActive(self):
        #if inDebug(): return
        content = '''123<newline>äöüß
<esc-char>xyz
'''
        processor = TextProcessor.TextProcessor(self._logger)
        processor.setContent(content)
        self.assertEqual(1, processor.replace('<newline>', '\\n', escActive=True))
        self.assertEqual(1, processor.replace('<esc-char>', '\\t\\u0045\\U00000046\\x47', escActive=True))
        current = '\n'.join(processor.lines)
        self.assertEqual('''123
äöüß
\tEFGxyz
''', current)

    def testRuleSearchForward(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('Hello World!')
        processor.executeRules(r'>/world/i')
        self.assertEqual(0, processor.cursor('line'))
        self.assertEqual(6, processor.cursor('col'))

    def testRuleSearchBackward(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\nHello World!\nHi!')
        processor.executeRules(r'eof;</O/ie')
        self.assertEqual(1, processor.cursor('line'))
        self.assertEqual(8, processor.cursor('col'))

    def testRuleAnchors(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\nHello World!\nHi!')
        processor.executeRules(r'eof;eopl')
        self.assertEqual(3, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'eof;bof')
        self.assertEqual(0, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'bof;>/W/ bol')
        self.assertEqual(1, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'bof;>/W/;eol')
        self.assertEqual(2, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'bof >/W/;bonl')
        self.assertEqual(2, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'bof >/W/;eonl')
        self.assertEqual(3, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'bof >/W/;bopl')
        self.assertEqual(0, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

        processor.executeRules(r'bof >/W/;eopl')
        self.assertEqual(1, processor.cursor('line'))
        self.assertEqual(0, processor.cursor('col'))

    def testRuleReposition(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\ndef\nHello World!\nHi\nGreetings!')
        processor.executeRules(r'bof >/W/ +2:1')
        self.assertEqual(2+2, processor.cursor('line'))
        self.assertEqual(6+1, processor.cursor('col'))

        processor.executeRules(r'bof >/W/ -2:1')
        self.assertEqual(2-2, processor.cursor('line'))
        self.assertEqual(6-1, processor.cursor('col'))

        processor.executeRules(r'bof 2:3')
        self.assertEqual(2, processor.cursor('line'))
        self.assertEqual(3, processor.cursor('col'))


    def testRuleMarkSwap(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\ndef\nHello World!\nHi\nGreetings!')
        processor.executeRules(r'bof >/W/;mark-b;-2:4;swap-b')
        self.assertEqual(2, processor.cursor('line'))
        self.assertEqual(6, processor.cursor('col'))

    def testRuleSet(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\ndef\nHello World!\nHi\nGreetings!')
        processor.executeRules(r'bof >/W/;mark-z;>/!/e;set-Q-z set-A:"!Q!BA"e=!')
        self.assertEqual('World!', processor.lastState.getRegister('Q'))
        self.assertEqual('World!A', processor.lastState.getRegister('A'))

    def testRuleAdd(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\ndef\nHello World!\nHi\nGreetings!')
        processor.executeRules(r'set-X:"+" bof >/W/ mark-z >/!/ set-A-z add-A:".!X."e=! add-A-A')
        self.assertEqual('World.+.World.+.', processor.lastState.getRegister('A'))

    def testRuleCut(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('a\n123\nZ')
        processor.executeRules(r'bof >/2/;mark-b;+0:1;cut-b')
        self.assertEqual('a\n13\nZ', '\n'.join(processor.lines))

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'bof >/b/;mark-b;>/3/;cut-b-Q')
        self.assertEqual('a3\nZ', '\n'.join(processor.lines))
        self.assertEqual('b\n12', processor.lastState.getRegister('Q'))

    def testRuleInsert(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'bof >/b/;mark-b;>/2/e;set-A-b;insert-A')
        self.assertEqual('ab\n12b\n123\nZ', '\n'.join(processor.lines))
        self.assertEqual(2, processor.cursor('line'))
        self.assertEqual(2, processor.cursor('col'))

        processor.setContent('a\n123\nZ')
        processor.executeRules(r'set-D:"$" set-E:":" bof >/2/;mark-f;insert:"?EFoo?D"e=?')
        self.assertEqual('a\n1:Foo$23\nZ', '\n'.join(processor.lines))
        self.assertEqual(1, processor.cursor('line'))
        self.assertEqual(6, processor.cursor('col'))

    def testRuleGroup(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'bof >/(\d+)/;group-1-Z')
        self.assertEqual('123', processor.lastState.getRegister('Z'))

    def testRulePrint(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'set-Z:"&" bof >/2/;mark-g;</b/;set-X-g;print-g;print:"%Z%Zreg-x: "e=%;print-X')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)

    def testRuleReplace(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'1:0 replace:/\d+/#/')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual('#', processor.lines[1])

        processor.setContent('ab')
        processor.executeRules(r'set-R:"a123b" replace-R:/\d+/#/')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual('a#b', processor.lastState.getRegister('R'))

        processor.setContent('abc\n123456\nxyz')
        processor.executeRules(r'>/2/ mark-a >/5/ replace-a:/\d/#/')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual('1###56', processor.lines[1])

        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('abc\n123456\nxyz')
        processor.executeRules(r'>/c/ mark-a >/z/ replace-a:/./#/')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual('ab#\n######\n##z', '\n'.join(processor.lines))

    def testRuleJump(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'bof >/b/ jump:%X% +2:1 %X%:')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual(0, processor.cursor('line'))
        self.assertEqual(1, processor.cursor('col'))

        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'>/b/ mark-f >/3/ jump-f')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual(0, processor.cursor('line'))
        self.assertEqual(1, processor.cursor('col'))

    def testFlowControlOnSuccess(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('ab\n123\nZ')
        processor.executeRules(r'bof;success:%x%; +1:0 %x%: +1:0')
        self.assertEqual(1, processor.cursor('line'))

    def testRuleExpr(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab')
        # ............................................5..........2..........16..........5
        processor.executeRules(r'set-A:"5" expr-B:"+$A" expr-B:"-3" expr-B:"*8" expr-B:"/3"')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual('5', processor.lastState.getRegister('B'))

    def testRuleState(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('ab\n1234567\n# end of file')
        # ............................................5..........2..........16..........5
        processor.executeRules(r'1:4 state-A:"row" state-B:"col" state-C:"rows" set-Z:"$A:$B:$C"e=$')
        self.assertTrue(processor.lastState is not None and processor.lastState.success)
        self.assertEqual('2:5:3', processor.lastState.getRegister('Z'))

    def testInsertOrReplace(self):
        if inDebug(): return
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace

        processor.setContent('#! /bin/sh\n  abc=123\nx')
        processor.insertOrReplace(r'\s*abc\s*=\s*\d+', '  abc=456')
        self.assertEqual(3, len(processor.lines))
        self.assertEqual('  abc=456', processor.lines[1])

        processor.insertOrReplace(r'\s*xyz\s*=\s*\d+', 'xyz=Hi', '/bin/sh')
        self.assertEqual(4, len(processor.lines))
        self.assertEqual('xyz=Hi', processor.lines[1])

        processor.insertOrReplace(r'\s*k\s*=\s*\d+', 'k=99', 'end of file', above=True)
        self.assertEqual(5, len(processor.lines))
        self.assertEqual('k=99', processor.lines[4])

        processor.insertOrReplace(r'LLL=', 'LLL=blub', 'not available', above=True)
        self.assertEqual(6, len(processor.lines))
        self.assertEqual('LLL=blub', processor.lines[5])

    def testAdaptVariable(self):
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('''# a file
max=4
min = 3
string = "Hello World"
''')
        status = TextProcessor.ReplaceStatus()
        self.assertFalse(processor.hasChanged)
        self.assertTrue(processor.adaptVariable('max', '99', status))
        self.assertTrue(status.hasChanged)
        self.assertTrue(status.hasFound)
        self.assertEqual(processor.lines[1], 'max=99')
        self.assertTrue(processor.hasChanged)
        processor.hasChanged = False
        status.clear()
        self.assertFalse(status.hasChanged)
        self.assertFalse(status.hasFound)
        self.assertTrue(processor.adaptVariable('min', '10', status))
        self.assertTrue(status.hasChanged)
        self.assertTrue(status.hasFound)
        self.assertEqual(processor.lines[2], 'min = 10')
        self.assertTrue(processor.hasChanged)
        status.clear()
        processor.hasChanged = False
        self.assertTrue(processor.adaptVariable('string', '"Servus beinand"', status))
        self.assertTrue(status.hasChanged)
        self.assertTrue(status.hasFound)
        self.assertEqual(processor.lines[3], 'string = "Servus beinand"')
        self.assertTrue(processor.hasChanged)
        status.clear()
        processor.hasChanged = False

        self.assertTrue(processor.adaptVariable('max', '99', status))
        self.assertFalse(status.hasChanged)
        self.assertTrue(status.hasFound)
        self.assertEqual(processor.lines[1], 'max=99')
        self.assertFalse(processor.hasChanged)
        status.clear()
        processor.hasChanged = False
        self.assertFalse(processor.adaptVariable('unknown', '99', status))
        self.assertFalse(status.hasChanged)
        self.assertFalse(status.hasFound)
        self.assertEqual(processor.lines[1], 'max=99')
        self.assertFalse(processor.hasChanged)

    def testInsertByAnchor(self):
        processor = TextProcessor.TextProcessor(self._logger)
        processor.traceFile = self._trace
        processor.setContent('''# a file
max=4
min = 3
string = "Hello World"
''')
        processor.insertByAnchor(r'max', 'line1')
        processor.insertByAnchor(r'min', 'line2', True)
        processor.insertByAnchor(r'unknown', 'line3', True)
        self.assertEqual('\n'.join(processor.lines), '''# a file
max=4
line1
line2
min = 3
string = "Hello World"
line3''')

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.testName']
    tester = TextProcessorTest()
    tester.run()

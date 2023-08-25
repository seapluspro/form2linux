'''
StringUtilsTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import unittest
import os
import re
from base import StringUtils
from base import FileHelper
from base import MemoryLogger

def inDebug(): return False

class StringUtilsTest(unittest.TestCase):

    def testJoin(self):
        if inDebug(): return
        self.assertEqual('1 2 3', StringUtils.join(' ', [1,2,3]))
        self.assertEqual('1,B,[]', StringUtils.join(',', [1, 'B', []]))
        self.assertEqual('A.B.C', StringUtils.join('.', ['A', 'B', 'C']))
        self.assertEqual('', StringUtils.join('.', None))

    def testToFile(self):
        if inDebug(): return
        fn = '/tmp/stringutils.tmp'
        if os.path.exists(fn):
            os.unlink(fn)
        content = 'line1\nline2'
        StringUtils.toFile(fn, content)
        self.assertTrue(os.path.exists(fn))
        self.assertTrue(FileHelper.fileContains(fn, 'line1'))
        self.assertTrue(FileHelper.fileContains(fn, 'line2'))

    def testToFileMode(self):
        if inDebug(): return
        fn = FileHelper.tempFile('modetest.txt', 'unittest.2')
        StringUtils.toFile(fn, 'Hi', fileMode=0o570)
        status = os.stat(fn)
        self.assertEqual(0o570, status.st_mode % 0o1000)

    def testToFileError(self):
        if inDebug(): return
        fn = '/tmp/not-existing-dir/stringutils.tmp'
        if os.path.exists(fn):
            os.unlink(fn)
        content = 'line1\nline2'
        logger = MemoryLogger.MemoryLogger(4)
        StringUtils.setLogger(logger)
        StringUtils.toFile(fn, content)
        self.assertFalse(os.path.exists(fn))
        self.assertEqual(1, logger._errors)
        self.assertTrue(logger.firstErrors()[0].find(r'cannot write to ') >= 0)

    def testFromFile(self):
        if inDebug(): return
        fn = '/tmp/stringutils.tmp'
        content = 'xline1\nxline2'
        StringUtils.toFile(fn, content)
        current = StringUtils.fromFile(fn)
        self.assertEqual(content, current)

    def testFromFileSep(self):
        if inDebug(): return
        fn = '/tmp/stringutils.tmp'
        content = 'xline1\nxline2'
        StringUtils.toFile(fn, content)
        current = StringUtils.fromFile(fn, '\n')
        self.assertEqual(content.split('\n'), current)

    def testTailOfWord(self):
        if inDebug(): return
        self.assertEqual('x', StringUtils.tailOfWord('-ax', '-a'))
        self.assertEqual('x', StringUtils.tailOfWord('-b -ax', '-a'))
        self.assertEqual('x', StringUtils.tailOfWord('-ax -b', '-a'))
        self.assertEqual('x', StringUtils.tailOfWord('-c -ax -b', '-a'))
        self.assertEqual('x', StringUtils.tailOfWord('-ax\t -b', '-a'))
        self.assertEqual('x', StringUtils.tailOfWord('y \t-ax\t -b', '-a'))

        self.assertEqual(None, StringUtils.tailOfWord('--find-a-ax', '-a'))
        self.assertEqual(None, StringUtils.tailOfWord('-b\t-c -d', '-a'))

    def testFormatSize(self):
        if inDebug(): return
        self.assertEqual('120 Byte', StringUtils.formatSize(120))
        self.assertEqual('123.456 KB', StringUtils.formatSize(123456))
        self.assertEqual('123.456 MB', StringUtils.formatSize(123456*1000))
        self.assertEqual('12.346 MB', StringUtils.formatSize(123456*100))
        self.assertEqual('1.235 MB', StringUtils.formatSize(123456*10))
        self.assertEqual('123.456 GB', StringUtils.formatSize(123456*1000*1000))
        self.assertEqual('123.456 TB', StringUtils.formatSize(123456*1000*1000*1000))

    def testHasContent(self):
        if inDebug(): return
        filename = FileHelper.tempFile('example.txt', 'stringutiltest')
        StringUtils.toFile(filename, '')
        self.assertFalse(StringUtils.hasContent(filename))
        StringUtils.toFile(filename, '# comment')
        self.assertFalse(StringUtils.hasContent(filename))
        StringUtils.toFile(filename, '# comment\n\t   \n\n#comment2')
        self.assertFalse(StringUtils.hasContent(filename))
        self.assertFalse(StringUtils.hasContent(filename + '.not.existing'))
        StringUtils.toFile(filename, '\t// comment\n\t   \n\n//comment2')
        self.assertFalse(StringUtils.hasContent(filename, '//'))

        StringUtils.toFile(filename, r'\t// comment\n\t   \n\//comment2')
        self.assertTrue(StringUtils.hasContent(filename, '#'))
        StringUtils.toFile(filename, '# has content!\n\na=3')
        self.assertTrue(StringUtils.hasContent(filename, '#'))

    def testFirstMatch(self):
        if inDebug(): return
        aList = ['# a=2', '#', 'b=3', '\t name = Jonny Cash ']
        regExpr = re.compile(r'^\s*(\w+)\s*=\s*(.*?)\s*$')
        matcher = StringUtils.firstMatch(aList, regExpr)
        self.assertNotEqual(None, matcher)
        self.assertEqual('b', matcher.group(1))
        self.assertEqual('3', matcher.group(2))

        matcher = StringUtils.firstMatch(aList, regExpr, 3)
        self.assertNotEqual(None, matcher)
        self.assertEqual('name', matcher.group(1))
        self.assertEqual('Jonny Cash', matcher.group(2))

    def testGrepInFile(self):
        if inDebug(): return
        filename = FileHelper.tempFile('grep.txt', 'stringutiltest')
        StringUtils.toFile(filename, """# Test
a = 1
# öäü b = 2
c=333
""")
        regExpr = re.compile(r'^\s*(\w+)\s*=\s*(.*?)\s*$')
        found = StringUtils.grepInFile(filename, regExpr)
        self.assertEqual(2, len(found))
        self.assertEqual('a = 1', found[0])
        self.assertEqual('c=333', found[1])

        found = StringUtils.grepInFile(filename, regExpr, 1)
        self.assertEqual(1, len(found))
        self.assertEqual("a = 1", found[0])

    def testGrepInFileGroup(self):
        if inDebug(): return
        filename = FileHelper.tempFile('grep.txt', 'stringutiltest')
        StringUtils.toFile(filename, """# Test
a = 1
# öäü b = 2
c=333
""")
        regExpr = re.compile(r'^\s*\w+\s*=\s*(.*?)\s*$')
        found = StringUtils.grepInFile(filename, regExpr, None, 1)
        self.assertEqual(2, len(found))
        self.assertEqual('1', found[0])
        self.assertEqual('333', found[1])

        found = StringUtils.grepInFile(filename, regExpr, 1)
        self.assertEqual(1, len(found))
        self.assertEqual("a = 1", found[0])

    def testLimitItemLength_WithoutElipsis(self):
        if inDebug(): return
        source = ['1', '22', '333', '4444']
        result = StringUtils.limitItemLength(source, 2)
        self.assertEqual(source[0], '1')
        self.assertEqual(source[3], '4444')
        self.assertEqual(len(source), len(result))
        for ix in range(len(source)):
            self.assertEqual(source[ix][0:2], result[ix])
        result = StringUtils.limitItemLength(source, 0)
        self.assertEqual('', ''.join(result))

    def testLimitItemLength(self):
        if inDebug(): return
        source = ['abcd1', 'abcd22', 'abcd333', 'abcd4444']
        result = StringUtils.limitItemLength(source, 5)
        self.assertEqual(source[0], 'abcd1')
        self.assertEqual(source[3], 'abcd4444')
        self.assertEqual(len(source), len(result))
        for ix in range(len(source)):
            if ix ==  0:
                self.assertEqual(source[ix], result[ix])
            else:
                self.assertEqual(source[ix][0:2] + '...', result[ix])
        result = StringUtils.limitItemLength(source, 0)
        self.assertEqual('', ''.join(result))

    def testToFloatAndTypeDate(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('2019.10.23')
        self.assertEqual(1571781600.0, value)
        self.assertEqual('date', dataType)
        [value, dataType] = StringUtils.toFloatAndType('1970-01-01')
        self.assertEqual(-3600.0, value)
        self.assertEqual('date', dataType)

    def testToFloatAndTypeTime(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('01:02:03')
        self.assertEqual(1*3600+2*60+3, value)
        self.assertEqual('time', dataType)
        [value, dataType] = StringUtils.toFloatAndType('2:17')
        self.assertEqual(2*3600+17*60, value)
        self.assertEqual('time', dataType)

    def testToFloatAndTypeDateTime(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('2019.10.23T01:02:03')
        self.assertEqual(1571785323.0, value)
        self.assertEqual('datetime', dataType)
        [value, dataType] = StringUtils.toFloatAndType('1970-01-02 5:17')
        self.assertEqual(101820.0, value)
        self.assertEqual('datetime', dataType)

    def testToFloatAndTypeHex(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('0x1234')
        self.assertEqual(float(0x1234), value)
        self.assertEqual('int', dataType)
        [value, dataType] = StringUtils.toFloatAndType('0XABCDEF0123456')
        self.assertEqual(float(0xABCDEF0123456), value)
        self.assertEqual('int', dataType)
        [value, dataType] = StringUtils.toFloatAndType('0Xabcdef0')
        self.assertEqual(float(0xABCDEF0), value)
        self.assertEqual('int', dataType)

    def testToFloatAndTypeOct(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('0o1234')
        self.assertEqual(float(0o1234), value)
        self.assertEqual('int', dataType)
        [value, dataType] = StringUtils.toFloatAndType('0o12345670')
        self.assertEqual(float(0o12345670), value)
        self.assertEqual('int', dataType)

    def testToFloatAndTypeInt(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('1234')
        self.assertEqual(1234.0, value)
        self.assertEqual('int', dataType)
        [value, dataType] = StringUtils.toFloatAndType('987654321')
        self.assertEqual(987654321.0, value)
        self.assertEqual('int', dataType)

    def testToFloatAndTypeFloat(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('1234.0')
        self.assertEqual(1234.0, value)
        self.assertEqual('float', dataType)
        [value, dataType] = StringUtils.toFloatAndType('987654321.0')
        self.assertEqual(987654321.0, value)
        self.assertEqual('float', dataType)
        [value, dataType] = StringUtils.toFloatAndType('1.23E+44')
        self.assertEqual(1.23E+44, value)
        self.assertEqual('float', dataType)

    def testToFloatAndTypeError(self):
        if inDebug(): return
        [value, dataType] = StringUtils.toFloatAndType('host3')
        self.assertEqual('float (or int or date(time)) expected, found: host3', value)
        self.assertEqual('undef', dataType)

    def testToFloatDate(self):
        if inDebug(): return
        value = StringUtils.toFloat('2019.10.23')
        self.assertEqual(1571781600.0, value)
        value = StringUtils.toFloat('1970-01-01')
        self.assertEqual(-3600.0, value)

    def testToFloatTime(self):
        if inDebug(): return
        value = StringUtils.toFloat('01:02:03')
        self.assertEqual(1*3600+2*60+3, value)
        value = StringUtils.toFloat('2:17')
        self.assertEqual(2*3600+17*60, value)

    def testToFloatDateTime(self):
        if inDebug(): return
        value = StringUtils.toFloat('2019.10.23T01:02:03')
        self.assertEqual(1571785323.0, value)
        value = StringUtils.toFloat('1970-01-02 5:17')
        self.assertEqual(101820.0, value)

    def testToFloatHex(self):
        if inDebug(): return
        value = StringUtils.toFloat('0x1234')
        self.assertEqual(float(0x1234), value)
        value = StringUtils.toFloat('0XABCDEF0123456')
        self.assertEqual(float(0xABCDEF0123456), value)
        value = StringUtils.toFloat('0Xabcdef0')
        self.assertEqual(float(0xABCDEF0), value)

    def testToFloatOct(self):
        if inDebug(): return
        value = StringUtils.toFloat('0o1234')
        self.assertEqual(float(0o1234), value)
        value = StringUtils.toFloat('0o12345670')
        self.assertEqual(float(0o12345670), value)

    def testToFloatInt(self):
        if inDebug(): return
        value = StringUtils.toFloat('1234')
        self.assertEqual(1234.0, value)
        value = StringUtils.toFloat('987654321')
        self.assertEqual(987654321.0, value)

    def testToFloatFloat(self):
        if inDebug(): return
        value = StringUtils.toFloat('1234.0')
        self.assertEqual(1234.0, value)
        value = StringUtils.toFloat('987654321.0')
        self.assertEqual(987654321.0, value)
        value = StringUtils.toFloat('1.23E+44')
        self.assertEqual(1.23E+44, value)

    def testToFloatError(self):
        if inDebug(): return
        value = StringUtils.toFloat('host3')
        self.assertEqual('float (or int or date(time)) expected, found: host3', value)

    def testAsFloat(self):
        if inDebug(): return
        self.assertEqual(321.0, StringUtils.asFloat('321'))
        self.assertEqual(-321.0, StringUtils.asFloat('-321'))
        self.assertEqual(801.0, StringUtils.asFloat('0x321'))
        self.assertEqual(1.35E-2, StringUtils.asFloat('1.35E-2'))
        self.assertEqual(0.0, StringUtils.asFloat('0'))
        self.assertEqual(None, StringUtils.asFloat('1.35E-'))
        self.assertEqual(-1.0, StringUtils.asFloat('', -1.0))

    def testAsInt(self):
        if inDebug(): return
        self.assertEqual(321, StringUtils.asInt('321'))
        self.assertEqual(0x321, StringUtils.asInt('0x321'))
        self.assertEqual(0o321, StringUtils.asInt('0321'))
        self.assertEqual(-33, StringUtils.asInt('-33', 777))
        self.assertEqual(77, StringUtils.asInt('99x', 77))
        self.assertEqual(777, StringUtils.asInt('x2', 777))
        self.assertEqual(-349, StringUtils.asInt('-349'))
        self.assertEqual(+123, StringUtils.asInt('+123', 777))
        self.assertEqual(None, StringUtils.asInt('-3', None, signIsAllowed=False))
        self.assertEqual(None, StringUtils.asInt('+333', None, signIsAllowed=False))


    def testRegExprCompile(self):
        if inDebug(): return
        rexpr = StringUtils.regExprCompile(r'\d', None, None, True)
        self.assertNotEqual(None, rexpr.match('7'))
        rexpr = StringUtils.regExprCompile('Hi', None, None, False)
        self.assertNotEqual(None, rexpr.match('hi'))

    def testRegExprCompileError(self):
        if inDebug(): return
        logger = MemoryLogger.MemoryLogger(True)
        rexpr = StringUtils.regExprCompile('*.txt', 'test of wrong pattern', logger)
        self.assertEqual(None, rexpr)
        logger.contains('error in regular expression in test of wrong pattern: nothing to repeat at position 0')
        rexpr = StringUtils.regExprCompile('(*.txt', 'test of wrong pattern')
        self.assertEqual(None, rexpr)

    def testMinimizeArrayUtfError(self):
        if inDebug(): return
        list1 = [b'\xffabcdefghijklmnopqrstuvwxyz01234567890', b'abcdefghijklmnopqrstuvwxyz01234567890\xff']
        logger = MemoryLogger.MemoryLogger(True)
        rc = StringUtils.minimizeArrayUtfError(list1, logger)
        self.assertEqual(2, len(rc))
        self.assertEqual(1, rc[0].find('abcdefghijklmnopqrstuvwxyz01234567890'))
        self.assertEqual(0, rc[1].find('abcdefghijklmnopqrstuvwxyz01234567890'))

    def testSecondsToString(self):
        if inDebug(): return
        self.assertEqual('00:00:00', StringUtils.secondsToString(0))
        self.assertEqual('03:04:15', StringUtils.secondsToString(3*3600+4*60+15))
        self.assertEqual('124:59:33', StringUtils.secondsToString(124*3600+59*60+33))

    def testIndentLines(self):
        if inDebug(): return
        lines = '  abc\n  def'
        self.assertEqual(' abc\n def', StringUtils.indentLines(lines, 1))
        self.assertEqual('abc\ndef', StringUtils.indentLines(lines, 0))
        self.assertEqual('   abc\n   def', StringUtils.indentLines(lines, 3, ' '))
        self.assertEqual('\tabc\n\tdef', StringUtils.indentLines(lines, 1, '\t'))
        self.assertEqual('...abc\n...def', StringUtils.indentLines(lines, 1, '...'))

    def testLimitLength(self):
        if inDebug(): return
        self.assertEqual('abcd', StringUtils.limitLength('abcd', 4))
        self.assertEqual('a..', StringUtils.limitLength('abcd', 3))
        self.assertEqual('ab', StringUtils.limitLength('ab..', 2))
        self.assertEqual('a', StringUtils.limitLength('ab..', 1))
        self.assertEqual('', StringUtils.limitLength('abcd', 0))

    def testLimitLength2(self):
        if inDebug(): return
        self.assertEqual('ab..cd', StringUtils.limitLength2('ab1234cd', 6))
        self.assertEqual('ab..cd', StringUtils.limitLength2('ab12345cd', 6))
        self.assertEqual('a..cd', StringUtils.limitLength2('ab1234cd', 5))
        self.assertEqual('a..cd', StringUtils.limitLength2('ab12345cd', 5))
        self.assertEqual('abcd', StringUtils.limitLength2('abcd', 4))
        self.assertEqual('acd', StringUtils.limitLength2('abcd', 3))
        self.assertEqual('ad', StringUtils.limitLength2('abcd', 2))
        self.assertEqual('d', StringUtils.limitLength2('abcd', 1))
        self.assertEqual('', StringUtils.limitLength2('abcd', 0))

    def testParseSize(self):
        if inDebug(): return
        errors = []
        self.assertEqual(12, StringUtils.parseSize('12', errors))
        self.assertEqual(1, StringUtils.parseSize('1B', errors))
        self.assertEqual(33000, StringUtils.parseSize('33k', errors))
        self.assertEqual(12*1024, StringUtils.parseSize('12Ki', errors))
        self.assertEqual(4*1000*1000, StringUtils.parseSize('4mb', errors))
        self.assertEqual(4*1024*1024, StringUtils.parseSize('4MiByte', errors))
        self.assertEqual(6*1000*1000*1000, StringUtils.parseSize('6G', errors))
        self.assertEqual(6*1024*1024*1024, StringUtils.parseSize('6GiByte', errors))
        self.assertEqual(99*1000*1000*1000*1000, StringUtils.parseSize('99tbyte', errors))
        self.assertEqual(99*1024*1024*1024*1024, StringUtils.parseSize('99Ti', errors))
        self.assertEqual(0, len(errors))
        #self.log('expecting x errors:')
        self.assertEqual(None, StringUtils.parseSize('', errors))
        self.assertEqual('size cannot be empty', errors[0])
        self.assertEqual(None, StringUtils.parseSize('3x', errors))
        self.assertEqual('not a valid size 3x. Expected <number>[<unit>], e.g. 10Mi', errors[1])
        self.assertEqual(None, StringUtils.parseSize('9mbx', errors))
        self.assertEqual('not a valid size 9mbx. Expected <number>[<unit>], e.g. 10Mi', errors[2])
        self.assertEqual(None, StringUtils.parseSize('9Gibyt', errors))
        self.assertEqual('not a valid size 9Gibyt. Expected <number>[<unit>], e.g. 10Mi', errors[3])

    def testParseDateTime(self):
        if inDebug(): return
        errors = []
        self.assertNotEqual(None, StringUtils.parseDateTime('3.7.2020', errors, True))
        self.assertNotEqual(None, StringUtils.parseDateTime('3.7.2020', errors))
        self.assertNotEqual(None, StringUtils.parseDateTime('2020.01.31', errors, True))
        self.assertNotEqual(None, StringUtils.parseDateTime('2020.01.31', errors))
        self.assertNotEqual(None, StringUtils.parseDateTime('3.7.2020-2:04', errors))
        self.assertNotEqual(None, StringUtils.parseDateTime('2020.01.31 15:3', errors))
        self.assertEqual('2020-07-03 00:00:00', str(StringUtils.parseDateTime('3.7.2020', errors, True)))
        self.assertEqual('2020-01-02 00:00:00', str(StringUtils.parseDateTime('2020.1.2', errors, False)))
        self.assertEqual('2020-07-03 07:03:00', str(StringUtils.parseDateTime('3.7.2020-7:3', errors)))
        self.assertEqual('2020-01-02 22:33:44', str(StringUtils.parseDateTime('2020.1.2 22:33:44', errors)))
        self.assertEqual(0, len(errors))

    def testParseDateTimeErrors(self):
        if inDebug(): return
        errors = []
        self.assertEqual(None, StringUtils.parseDateTime('3.7.202O', errors))
        self.assertEqual('not a date: 3.7.202O', errors[0])
        self.assertEqual(None, StringUtils.parseDateTime('x3.7.2020', errors))
        self.assertEqual('not a date: x3.7.2020', errors[1])
        self.assertEqual(None, StringUtils.parseDateTime('31.6.2020', errors))
        self.assertEqual('day is out of range for month: 31.6.2020', errors[2])
        self.assertEqual(None, StringUtils.parseDateTime('09.02.1980 12:44', errors, dateOnly=True))
        self.assertEqual('unexpected tail of a date: 12:44', errors[3])
        self.assertEqual(None, StringUtils.parseDateTime('1998.09.02-13:49', errors, dateOnly=True))
        self.assertEqual('unexpected tail of a date: 13:49', errors[4])

    def testEscChar(self):
        if inDebug(): return
        self.assertEqual('\\\\', StringUtils.escChars('\\'))
        self.assertEqual('\\n', StringUtils.escChars('\n'))
        self.assertEqual('\\\\\\n\\r\\t\\b', StringUtils.escChars('\\\n\r\t\b'))

    def testUnescChar(self):
        if inDebug(): return
        self.assertEqual('J', StringUtils.unescChars('\\x4A'))
        self.assertEqual('E', StringUtils.unescChars('\\x45'))
        self.assertEqual('\\', StringUtils.unescChars('\\\\'))
        self.assertEqual('\n', StringUtils.unescChars(r'\n'))
        self.assertEqual('\\\n\r\t\bEäöü', StringUtils.unescChars(r'\\\n\r\t\b\x45äöü'))
        self.assertEqual('\U00000046', StringUtils.unescChars(r'\U00000046'))
        self.assertEqual('F', StringUtils.unescChars(r'\U00000046'))
        self.assertEqual('\u0047', StringUtils.unescChars(r'\u0047'))
        self.assertEqual('G', StringUtils.unescChars(r'\u0047'))

    def testIsBinaryString(self):
        if inDebug(): return
        self.assertFalse(StringUtils.isBinary('abc\r\n\v\f\tbluböäüÖÄÜß'))
        self.assertFalse(StringUtils.isBinary(None))
        self.assertTrue(StringUtils.isBinary('abc\x00def'))
        self.assertTrue(StringUtils.isBinary('abc\x01def'))
        self.assertTrue(StringUtils.isBinary('abc\x01def', 4))
        self.assertFalse(StringUtils.isBinary('abc\x01def', 3))

    def testIsBinaryBytes(self):
        if inDebug(): return
        self.assertFalse(StringUtils.isBinary('abc\r\n\v\f\tbluböäüÖÄÜß'.encode('utf-8')))
        self.assertFalse(StringUtils.isBinary(None))
        self.assertTrue(StringUtils.isBinary(b'abc\x00def'))
        self.assertTrue(StringUtils.isBinary(b'abc\x01def', 4))
        self.assertFalse(StringUtils.isBinary(b'abc\x01def', 3))

    def testFileToText(self):
        if inDebug(): return
        fn = FileHelper.tempFile('filetest.data', 'unittest.2')
        content = '\tHi\v\f\r\n'
        StringUtils.toFile(fn, content)
        self.assertEqual(content, StringUtils.fileToText(fn))
        content = 'a\nb\nc'
        StringUtils.toFile(fn, content)
        self.assertEqual('a,b,c', ','.join(StringUtils.fileToText(fn, '\n')))
        content = 'abc\x01'
        StringUtils.toFile(fn, content)
        self.assertEqual(content, StringUtils.fileToText(fn, binaryTestLength=3, ignoreBinary=True))
        self.assertEqual('', StringUtils.fileToText(fn, binaryTestLength=4, ignoreBinary=True))
        self.assertEqual('', StringUtils.fileToText(fn, maxLength=3))
        
if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.testName']
    tester = StringUtilsTest()
    tester.run()

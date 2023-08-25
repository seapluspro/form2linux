'''
StringUtils.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import os
import datetime
import codecs
from typing import Sequence

from base import Const
from base import FileHelper
from base import LinuxUtils
from base import Logger
from base import MemoryLogger
from base import StringUtils

# .................................1.....1....2.....2....3.....3
REG_EXPR_DATE = re.compile(r'^(\d{4})[.-](\d\d?)[.-](\d\d?)')
REG_EXPR_DATE2 = re.compile(r'^(\d\d?)[.](\d\d?)[.](\d{4})')
# ...................................1.....1.2....2 a..3.....3a
REG_EXPR_TIME = re.compile(r'^(\d\d?):(\d\d?)(?::(\d\d?))?$')
REG_EXPR_INT = re.compile(r'^0[xX]([0-9a-fA-F]+)|0o([0-7]+)|(\d+)$')
REG_EXPR_SIZE = re.compile(
    r'^(\d+)((?:[kmgt]i?)?(?:b(?:ytes?)?)?)?$', Const.IGNORE_CASE)
# REG_EXPR_ESC =
# re.compile(r'(\\U........|\\u....|\\x..|\\[0-7]{1,3}|\\N\{[^}]+\}|\\[\\'"abfnrtv])',
# Const.RE_UNICODE)
REG_EXPR_ESC = re.compile(r'''(\\U[0-9a-fA-F]{8}|\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F][0-9a-fA-F]|\\[0-7]{1,3}'
    + '|\\N\{[^}]+\}|\\[\\'"abfnrtv])''', Const.RE_UNICODE)
#    ( \\U........      # 8-digit hex escapes
#    | \\u....          # 4-digit hex escapes
#    | \\x..            # 2-digit hex escapes
#    | \\[0-7]{1,3}     # Octal escapes
#    | \\N\{[^}]+\}     # Unicode characters by name
#    | \\[\\'"abfnrtv]  # Single-character escapes


def _error(msg: str, logger: Logger.Logger=None):
    if logger is None:
        logger = MemoryLogger.MemoryLogger.globalLogger()
    logger.error(msg)


def arrayContains(lines: Sequence[str], regExpr):
    '''Tests whether at least one line of the array lines contains a given regular expression.
    @param lines: array of text lines
    @param regExpr: a string or a regexpr object
    @return: True: at least one item of lines contains the regular expression regExpr
    '''
    if isinstance(regExpr, str):
        regExpr = re.compile(regExpr)
    found = False
    for line in lines:
        if regExpr.search(line) is not None:
            found = True
            break
    return found


def asFloat(value: str, defaultValue: float=None) -> float:
    '''Tests whether a value is an floating point number. If not the defaultValue is returned. Otherwise the float is returned.
    @param value: string value to test
    @param defaultValue: the return value if value is not an float
    @return: defaultValue: the value is not an integer Otherwise: the value as float
    '''
    rc = defaultValue
    try:
        rc = float(value)
    except ValueError:
        # may be a hex number...
        rc = asInt(value, defaultValue)
        if rc is not None:
            rc = float(rc)
    return rc


def asInt(value, defaultValue: int=None, signIsAllowed: bool=True) -> int:
    '''Tests whether a value is an integer. If not the defaultValue is returned. Otherwise the integer is returned.
    @param value: string value to test
    @param defaultValue: the return value if value is not an integer
    @param signIsAllowed: False: a preceeding '-' or '+' in value is an error
    @return: defaultValue: the value is not an integer Otherwise: the value as integer
    '''
    rc = defaultValue
    if value is not None:
        if isinstance(value, int):
            rc = value
        else:
            negative = value.startswith('-')
            if signIsAllowed and (negative or value.startswith('+')):
                value = value[1:]
            matcher = REG_EXPR_INT.match(value)
            if matcher is None:
                rc = defaultValue
            else:
                if value.startswith('0x') or value.startswith('0X'):
                    rc = int(matcher.group(1), 16)
                elif value.startswith('0'):
                    rc = int(value, 8)
                else:
                    rc = int(value)
                # pylint: disable-next=invalid-unary-operand-type
                rc = -rc if negative else rc
    return rc

# pylint: disable-next=unused-argument
def avoidWarning(unusedVariable):
    '''This function is used to avoid the warning "variable not used".
    @param unusedVariable: variable to "hide"
    '''
    # Nothing to do


def escChars(text: str):
    '''Return the text with escaped meta characters like \n, \t, \\.
    Inversion: @see unescChars()
    @todo: handle more cases, performance optimization
    @param text: text to convert
    @return: the text with escaped chars.
    '''
    rc = text.replace('\\', '\\\\').replace('\n', '\\n').replace(
        '\r', '\\r').replace('\t', '\\t').replace('\b', '\\b').replace('\a', '\\a')
    return rc


def fileToText(filename: str, sep: str=None, binaryTestLength: int=4096,
               ignoreBinary: bool=False, maxLength: int=10*1000*1000):
    '''Reads a (possible binary) file into a string.
    @param filename: the name of the file to read
    @param sep: None or the split separator
    @param binaryTestLength: the test whether the file is binary is done with this length
    @param ignoreBinary: True: if a file is binary the result is empty
    @param maxLength: if the file length is larger than that the result is empty
    @return the content of the file: If sep is None: a string. Otherwise an array of strings (lines)
    '''
    rc = ''
    statInfo = os.stat(filename)
    if statInfo is not None and statInfo.st_size <= maxLength:
        with open(filename, 'rb') as fp:
            content = fp.read()
            if content and (not ignoreBinary or not StringUtils.isBinary(content, binaryTestLength)):
                rc = toString(content, 'bytes')
    if sep is not None:
        rc = rc.split(sep)
    return rc


def firstMatch(aList: Sequence[str], regExpr, start: int=0):
    r'''Return the matching object of the first matching line of a given line list.
    @param aList: an array of lines to inspect
    @param regExpr: a compiled regular expression, e.g. re.compile(r'^\w+ =\s(.*)$')
    @param start: the first line index to start searching
    @return: None: nothing found
        otherwise: the matching object of the hit
    '''
    matcher = None
    while start < len(aList):
        matcher = regExpr.search(aList[start])
        if matcher is not None:
            break
        start += 1
    return matcher


def formatSize(size: int) -> str:
    '''Formats the filesize with minimal length.
    @param size: size in bytes
    @return: a string with a number and a unit, e.g. '103 kByte'
    '''
    if size < 1000:
        rc = str(size) + ' Byte'
    else:
        if size < 1000000:
            unit = 'KB'
            size /= 1000.0
        elif size < 1000000000:
            unit = 'MB'
            size /= 1000000.0
        elif size < 1000000000000:
            unit = 'GB'
            size /= 1000000000.0
        else:
            unit = 'TB'
            size /= 1000000000000.0
        rc = f'{size:.3f} {unit}'
    return rc


def fromFile(filename: str, sep: str=None):
    '''Returns the file content as a string. Only UTF-8 is allowed.
    @see fileToText() for other encodings
    @param filename: the name of the file to read
    @param sep: None or the split separator
    @param content: the content of the file. If sep is None: a string. Otherwise an array
    '''
    rc = ''
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as fp:
            try:
                rc = fp.read()
            except UnicodeDecodeError as exc:
                _error(f'{filename}: {exc}')
    if sep is not None:
        rc = rc.split(sep)
    return rc


def grepInFile(filename: str, regExpr, limit: int=None, group: int=None) -> Sequence[str]:
    r'''Returns all lines of a given file matching a given regular expression.
    @param filename: the name of the file to inspect
    @param regExpr: a compiled regular expression, e.g. re.compile(r'^\w+ =')
    @param limit: the maximal count of returned lines
    @param group: None or: the content of the group (defined by the group-th parenthesis) will be returned
    @return: a list of found lines or groups (see group), may be empty
    '''
    rc = []
    if isinstance(regExpr, str):
        regExpr = re.compile(regExpr)
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as fp:
            for line in fp:
                line = line.strip()
                matcher = regExpr.search(line)
                if matcher is not None:
                    if group is not None:
                        rc.append(matcher.group(group))
                    else:
                        rc.append(line)
                    if limit is not None:
                        limit -= 1
                        if limit <= 0:
                            break
    return rc


def hasContent(filename: str, beginOfComment: str='#') -> bool:
    '''Tests whether a file has a content without empty lines or comment lines.
    @param beginOfComment    this string starts a comment line
    @return: True: there are lines which are not empty and not comments.
    '''
    rc = False
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as fp:
            for line in fp:
                line = line.strip()
                if line != '' and not line.startswith(beginOfComment):
                    rc = True
                    break
    return rc


def indentLines(lines: Sequence[str], indention: int, indentStep=' ') -> str:
    '''Indents some lines given as string.
    @param lines: a string with some lines delimited by '\n'
    @param indention: the number of indention steps of the output
    @param indentStep: the string representing one indention step, e.g. '\t'
    @return: a string with the list of lines with the given indention
    '''
    lines = lines.split('\n')
    lines2 = []
    for line in lines:
        lines2.append(indentStep * indention + line.lstrip())
    rc = '\n'.join(lines2)
    return rc


def isBinary(text: str, testLength: int=4096) -> bool:
    '''Tests whether the text is binary.
    @param text: a str or a bytes instance
    @param testLength: the test is done only in prefix of text in this length
    @return True: the text is binary
    '''
    rc = False
    if text is not None:
        piece = text[0:testLength]
        theType = type(piece)
        if theType == str:
            if '\x00' in piece:
                rc = True
            else:
                for cc in piece:
                    if cc < ' ' and cc not in ('\r', '\n', '\v', '\t', '\f'):
                        rc = True
                        break
        elif theType == bytes:
            if b'\x00' in piece:
                rc = True
            else:
                for aByte in piece:
                    if aByte < 0x20 and not 9 <= aByte <= 13:
                        rc = True
                        break
        else:
            rc = True
    return rc


def join(separator: str, args) -> str:
    '''Joins all entries of a list into a string.
    @param separator: the separator between the list items
    @param args: list to join. Items may be not strings
    @return: a string with all items of args separated by separator
    '''
    rc = ''
    if args is not None:
        for item in args:
            if rc != '':
                rc += separator
            rc += str(item)
    return rc


def limitItemLength(array: Sequence[str], maxLength: int, elipsis: str='...') -> Sequence[str]:
    '''Copies the input array and limits each item to the given maximum.
    @param array:    source array
    @param maxLength: the maximal length of each item of the result
    @param suffix: the suffix for limited items, e.g. '...'
    @return: the copy of the array with limited items
    '''
    rc = []
    lenElipsis = len(elipsis)
    for item in array:
        if len(item) > maxLength:
            if maxLength >= lenElipsis:
                item = item[0:maxLength - lenElipsis] + elipsis
            else:
                item = item[0:maxLength]
        rc.append(item)
    return rc


def limitLength(string: str, maxLength: int, ellipsis: str='..') -> str:
    '''Returns the string or the head of the string if it is too long.
    @param string: the string to inspect
    @param maxLength: if the length of string is longer the result is the head of the string with this length
    @param ellipsis: a string at the end of the result to mark of a cut, e.g. ".."
    @result: the string or the head of the string if it is longer than maxLength
    '''
    rc = string
    if len(string) > maxLength:
        lenElipsis = 0 if ellipsis is None else len(ellipsis)
        if lenElipsis + 1 <= maxLength:
            rc = string[0:maxLength - lenElipsis] + ellipsis
        else:
            rc = string[0:maxLength]
    return rc


def limitLength2(string: str, maxLength: int, ellipsis: str='..') -> str:
    '''Returns the string or the head and tail of the string if it is too long.
    @param string: the string to inspect
    @param maxLength: if the length of string is longer the result is the head of the string with this length
    @param ellipsis: a string at the end of the result to mark of a cut, e.g. ".."
    @result: the string or the head of the string if it is longer than maxLength
    '''
    if maxLength == 0:
        rc = ''
    else:
        rc = string
        if len(string) > maxLength:
            lenElipsis = 0 if ellipsis is None else len(ellipsis)
            if lenElipsis + 2 <= maxLength:
                half = (maxLength - lenElipsis) // 2
                rc = string[0:half] + (ellipsis if ellipsis is not None else '') + \
                    string[-(maxLength - half - lenElipsis):]
            else:
                half = maxLength // 2
                rc = string[0:half] + string[-(maxLength - half):]
    return rc


def minimizeArrayUtfError(lines: Sequence[str], logger: Logger.Logger=None) -> Sequence[str]:
    '''Converts a string array of bytes into an array of UTF-8 strings.
    It minimizes the part which can not be converted.
    @param lines: a list of byte lines
    @param logger: None or the error logger
    @param logError: True: conversion errors will be logged
    '''
    rc = []
    for line in lines:
        try:
            rc.append(line.decode('utf-8'))
        except UnicodeDecodeError:
            rc.append(minimizeStringUtfError(line, logger))
    return rc


def minimizeStringUtfError(line: str, logger: Logger.Logger=None) -> str:
    '''Converts a string of bytes into an UTF-8 string.
    It minimizes the part which can not be converted.
    @param lines: a list of byte lines
    @param logger: None or the error logger
    '''
    def convert(part):
        try:
            rc = part.decode('utf-8')
        except UnicodeDecodeError:
            if logger is not None:
                logger.error('cannot decode: ' +
                             part.decode('ascii', 'ignore')[0:80])
            rc = None
        return rc
    rc = ''
    if len(line) < 10:
        part = convert(line)
        if part is not None:
            rc += part
        else:
            try:
                rc = line.decode('latin-1')
            except:
                rc = line.decode('ascii')
    else:
        half = int(len(line) / 2)
        part = convert(line[0:half])
        if part is not None:
            rc += part
        else:
            rc += minimizeStringUtfError(line[0:half], logger)
        part = convert(line[half:])
        if part is not None:
            rc += part
        else:
            rc += minimizeStringUtfError(line[half:], logger)
    return rc


def parseDateTime(text: str, errors: Sequence[str], dateOnly: bool=False):
    '''Parses a string representing a date or a datetime.
    @param text: the text to parse
    @param errors: IN/OUT: a list: error message will be appended here
    @param dateOnly: True: only dates are allowed
    @return: None: text is not a date
        a DateTime instance
    '''
    rc = None
    matcher = REG_EXPR_DATE.match(text)
    if matcher is not None:
        length = len(matcher.group(0))
        try:
            rc = datetime.datetime(int(matcher.group(1)), int(
                matcher.group(2)), int(matcher.group(3)))
            text = text[length:]
            if text and text[0] in ('-', '/', 'T', '\t', ' '):
                text = text[1:]
        except ValueError as exc:
            errors.append(str(exc) + ': ' + text)
    else:
        matcher = REG_EXPR_DATE2.match(text)
        if matcher is None:
            errors.append(f'not a date: {text}')
        else:
            length = len(matcher.group(0))
            try:
                rc = datetime.datetime(int(matcher.group(3)), int(
                    matcher.group(2)), int(matcher.group(1)))
                text = text[length:]
                if text and text[0] in ('-', '/', 'T', '\t', ' '):
                    text = text[1:]
            except ValueError as exc:
                errors.append(str(exc) + ': ' + text)
    if not dateOnly and rc is not None and len(text) >= 3:
        matcher = REG_EXPR_TIME.match(text)
        if matcher is not None:
            sec = 0 if matcher.lastindex < 3 else int(matcher.group(3))
            delta = datetime.timedelta(hours=int(matcher.group(
                1)), minutes=int(matcher.group(2)), seconds=sec)
            rc = rc + delta
            text = text[len(matcher.group(0)):]
    if rc is not None and text != '':
        rc = None
        errors.append(f'unexpected tail of a date: {text}')
    return rc


def parseSize(size: str, errors: Sequence[str]) -> int:
    '''Parses string with a filesize syntax.
    @param size: the string with the size to process, e.g. '44kiByte'
    @param errors: OUT: error messages will be appended to this list
    @return: None: wrong syntax otherwise: the size as integer
    '''
    rc = None
    if size == '':
        errors.append('size cannot be empty')
    else:
        matcher = REG_EXPR_SIZE.match(size)
        if matcher is None:
            errors.append(
                f'not a valid size {size}. Expected <number>[<unit>], e.g. 10Mi')
        else:
            rc = int(matcher.group(1))
            if matcher.lastindex > 1:
                factor = 1
                unit = matcher.group(2).lower()
                if unit.startswith('ki'):
                    factor = 1024
                elif unit.startswith('k'):
                    factor = 1000
                elif unit.startswith('mi'):
                    factor = 1024 * 1024
                elif unit.startswith('m'):
                    factor = 1000 * 1000
                elif unit.startswith('gi'):
                    factor = 1024 * 1024 * 1024
                elif unit.startswith('g'):
                    factor = 1000 * 1000 * 1000
                elif unit.startswith('ti'):
                    factor = 1024 * 1024 * 1024 * 1024
                elif unit.startswith('t'):
                    factor = 1000 * 1000 * 1000 * 1000
                rc *= factor
    return rc


def regExprCompile(pattern: str, location: str,
                   logger: Logger.Logger=None, isCaseSensitive: bool=False):
    '''Compiles a regular expression.
    @param pattern: a regular expression.
    @param logger: for error logging
    @param isCaseSensitive: true: the case is relevant
    @return: None: error occurred Otherwise: the re.RegExpr instance
    '''
    rc = None
    try:
        rc = re.compile(
            pattern, 0 if isCaseSensitive else Const.IGNORE_CASE)
    except re.error as exc:
        msg = f'error in regular expression in {location}: {exc}'
        _error(msg, logger)
    return rc


def secondsToString(seconds: int) -> str:
    '''Converts a number of seconds into a human readable string, e.g. '00:34:22'
    @param seconds: the seconds to convert
    @return: a string like '0:34:22'
    '''
    rc = f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'
    return rc


def setLogger(logger: Logger.Logger):
    '''Sets the global logger.
    @deprecated: use MemoryLogger.globalLogger()
    '''
    avoidWarning(logger)


def toFile(filename: str, content: str, separator: str='',
           fileMode: int=None, user: int=None, group: int=None, ensureParent: bool=False):
    '''Writes a string into a file.
    @param filename: the name of the file to write
    @param content: the string to write
    @param fileMode: None or the access rights of the file, e.g. 0o755
    @param user: None or the user name or user id to set (chown)
    @param gid: None or the group name or group id to set (chown)
    @param ensureParent: True: the parent directory is created if needed
    '''
    if ensureParent:
        parent = os.path.dirname(filename)
        if parent != '':
            FileHelper.ensureDirectory(parent)
    if isinstance(content, list):
        content = separator.join(content)
    mode = 'wb' if isinstance(content, bytes) else 'w'
    try:
        with open(filename, mode) as fp:
            fp.write(content)
        if fileMode is not None:
            os.chmod(filename, fileMode)
        if user is not None or group is not None:
            os.chown(filename, LinuxUtils.userId(
                user, -1), LinuxUtils.groupId(group, -1))
    except OSError as exc:
        _error(f'cannot write to {filename}: {exc} [{type(exc)}]')


def toFloat(value) -> float:
    '''Converts a string into a float.
    Possible data types: int, date, datetime, float.
    Value of date/datetime: seconds since 1.1.1970
    Value of time: seconds since midnight
    @param value: the string to convert
    @return [float, dataType] or [error_message, dataType]
    '''
    if isinstance(value, float):
        rc = value
    elif isinstance(value, int):
        rc = float(value)
    else:
        if not isinstance(value, str):
            value = str(value)
        matcher = REG_EXPR_DATE.match(value)
        if matcher is not None:
            length = len(matcher.group(0))
            value = value[length + 1:]
            rc = datetime.datetime(int(matcher.group(1)), int(
                matcher.group(2)), int(matcher.group(3))).timestamp()
            matcher = REG_EXPR_TIME.match(value)
            if matcher is not None:
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                secs = (hours * 60 + mins) * 60
                rc += secs
                if matcher.group(3):
                    rc += int(matcher.group(3))
        else:
            matcher = REG_EXPR_TIME.match(value)
            if matcher is not None:
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                rc = (hours * 60 + mins) * 60
                if matcher.group(3):
                    rc += int(matcher.group(3))
            else:
                rc = asFloat(value)
                if rc is None:
                    rc = 'float (or int or date(time)) expected, found: ' + value
    return rc


def toFloatAndType(value):
    '''Converts a string into a float.
    Possible data types: int, date, datetime, float.
    Value of date/datetime: seconds since 1.1.1970
    Value of time: seconds since midnight
    @param value: the string to convert
    @return [float, dataType] or [error_message, dataType]
    '''
    dataType = 'undef'
    if isinstance(value, float):
        dataType = 'float'
        rc = value
    else:
        matcher = REG_EXPR_DATE.match(value)
        if matcher is not None:
            dataType = 'date'
            length = len(matcher.group(0))
            value = value[length + 1:]
            rc = datetime.datetime(int(matcher.group(1)), int(
                matcher.group(2)), int(matcher.group(3))).timestamp()
            matcher = REG_EXPR_TIME.match(value)
            if matcher is not None:
                dataType += 'time'
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                secs = (hours * 60 + mins) * 60
                rc += secs
                if matcher.group(3):
                    rc += int(matcher.group(3))
        else:
            matcher = REG_EXPR_TIME.match(value)
            if matcher is not None:
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                dataType = 'time'
                rc = (hours * 60 + mins) * 60
                if matcher.group(3):
                    rc += int(matcher.group(3))
            else:
                matcher = REG_EXPR_INT.match(value)
                if matcher is not None:
                    dataType = 'int'
                    if matcher.group(3):
                        rc = float(matcher.group(3))
                    elif matcher.group(1):
                        rc = float(int(value[2:], 16))
                    elif matcher.group(2):
                        rc = float(int(value, 8))
                else:
                    try:
                        rc = float(value)
                        dataType = 'float'
                    except ValueError:
                        rc = f'float (or int or date(time)) expected, found: {value}'
    return [rc, dataType]


def toString(value, dataType: str=None, floatPrecision: int=None) -> str:
    '''Converts a numeric value into a string.
    @param value: a numeric value
    @param dataType: None: derive it from value otherwise: 'date', 'datetime', 'time', 'float', 'int'
    @param floatPrecision: None or if the type is a float, the number of digits behind the point
    @return: the value as string
    '''
    if dataType is None:
        dataType = type(value)
    if dataType == 'bytes':
        try:
            rc = value.decode('utf-8')
        except UnicodeDecodeError:
            rc = value.decode('latin_1')
            if rc == '':
                rc = value.decode('ascii')
    elif dataType == 'date':
        date = datetime.datetime.fromtimestamp(value)
        rc = date.strftime('%Y.%m.%d')
    elif dataType == 'datetime':
        if isinstance(value, str) and value.find(':') >= 0:
            rc = value
        else:
            date = datetime.datetime.fromtimestamp(value)
            rc = date.strftime('%Y.%m.%d %H:%M')
    elif dataType == 'time':
        if isinstance(value, str) and value.find(':') >= 0:
            rc = value
        else:
            rc = f'{value / 3600:2d}:{value % 3600 / 60:2d}'
    elif floatPrecision is not None:
        if isinstance(value, str):
            value = float(value)
        #aFormat = '{' + ':.{}f'.format(floatPrecision) + '}'
        # ':.{floatPrecision}f'
        aFormat = f'{{:.{floatPrecision}f}}'
        rc = aFormat.format(value)
    else:
        rc = f'{value}'
    return rc


def tailOfWord(words: str, wordPrefix: str) -> str:
    '''Returns the part of a word behind the word prefix.
    Example: words: "-e! -m" wordPrefix: "-e" result: "!"
    @param words: a string with words separated by space or tab
    @param wordPrefix: the word starting with this prefix will be searched
    @return: None: word prefix not found
            the word suffix
    '''
    rc = None
    if words.startswith(wordPrefix):
        ixStart = 0
    else:
        ixStart = words.find(wordPrefix)
        if ixStart > 0 and not words[ixStart - 1].isspace():
            ixStart = words.find(' ' + wordPrefix)
            if ixStart < 0:
                ixStart = words.find('\t' + wordPrefix)
    if ixStart >= 0:
        ixStart += len(wordPrefix)
        ixEnd = words.find(' ', ixStart)
        ixEnd2 = words.find('\t', ixStart)
        if ixEnd < 0 or 0 < ixEnd2 < ixEnd:
            ixEnd = ixEnd2
        if ixEnd < 0:
            ixEnd = len(words)
        rc = words[ixStart:ixEnd]
    return rc


def unescChars(text: str):
    '''Returns the text without escaped meta characters like \n, \t, \\.
    Inversion: @see escChar()
    @param text: text to convert
    @return: the text with unescaped chars
    '''
    def decodeMatch(match):
        return codecs.decode(match.group(0), 'unicode-escape')

    rc = REG_EXPR_ESC.sub(decodeMatch, text)
    return rc


if __name__ == '__main__':
    pass

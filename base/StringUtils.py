'''
StringUtils.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import os
import datetime

# .................................1.....1....2.....2....3.....3
stringUtilRexprDate = re.compile(r'^(\d{4})[.-](\d\d?)[.-](\d\d?)')
# ...................................1.....1.2....2 a..3.....3a
stringUtilRexprTime = re.compile(r'^(\d\d?):(\d\d?)(?::(\d\d?))?$')
stringUtilRexprInt = re.compile(r'^0[xX]([0-9a-fA-F]+)|0([0-7]+)|(\d+)$')

def arrayContains(lines, regExpr):
    '''Tests whether at least one line of the array lines contains a given regular expression.
    @param lines: array of text lines
    @param regExpr: a string or a regexpr object
    @return: True: at least one item of lines contains the regular expression regExpr
    '''
    if type(regExpr) == str:
        regExpr = re.compile(regExpr)
    found = False
    for line in lines:
        if regExpr.search(line) != None:
            found = True
            break
    return found

def asInt(value, defaultValue = None):
    '''Tests whether a value is an integer. If not the defaultValue is returned. Othewise the integer is returned.
    @param value: string value to test
    @return: defaultValue: the value is not an integer Otherwise: the value as integer
    '''
    matcher = stringUtilRexprInt.match(value)
    if matcher == None:
        rc = defaultValue
    else:
        if value.startswith('0x') or value.startswith('0X'):
            rc = int(matcher.group(1), 16)
        elif value.startswith('0'):
            rc = int(value, 8)
        else:
            rc = int(value)
    return rc

def escChars(text):
    '''Return the text with escaped meta characters like \n, \t, \\.
    @param text: text to convert
    @return: the text with escaped chars.
    '''
    text = text.replace('\\', '\\\\')
    text = text.replace('\t', '\\t')
    text = text.replace('\n', '\\n')
    return text

def firstMatch(aList, regExpr, start=0):
    '''Return the matching object of the first matching line of a given line list.
    @param aList: an array of lines to inspect
    @param regExpr: a compiled regular expression, e.g. re.compile(r'^\w+ =\s(.*)$')
    @param start: the first line index to start searching
    @return: None: nothing found
        otherwise: the matching object of the hit
    '''
    matcher = None
    while start < len(aList):
        matcher = regExpr.search(aList[start])
        if matcher != None:
            break
        start += 1
    return matcher

def formatSize(size):
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
        rc = '{:.3f} {:s}'.format(size, unit)
    return rc

def fromFile(filename, sep = None):
    '''Reads the content of a file.
    @param filename: the name of the file to read
    @param sep: None or the split separator
    @param content: the content of the file. If sep == None: a string. Otherwise an array
    '''
    rc = ''
    if os.path.exists(filename):
        with open(filename, 'r') as fp:
            rc = fp.read()
    if sep != None:
        rc = rc.split(sep)
    return rc

def grepInFile(filename, regExpr, limit = None, group = None):
    '''Returns all lines of a given file matching a given regular expression.
    @param filename: the name of the file to inspect
    @param regExpr: a compiled regular expression, e.g. re.compile(r'^\w+ =')
    @param limit: the maximal count of returned lines
    @param group: None or: the content of the group (defined by the group-th parenthesis) will be returned
    @return: a list of found lines or groups (see group), may be empty
    '''
    rc = []
    if type(regExpr) == str:
        regExpr = re.compile(regExpr)
    if os.path.exists(filename):
        with open(filename, 'r') as fp:
            for line in fp:
                line = line.strip()
                matcher = regExpr.search(line)
                if matcher != None:
                    if group != None:
                        rc.append(matcher.group(group))
                    else:
                        rc.append(line)
                    if limit != None:
                        limit -= 1
                        if limit <= 0:
                            break
    return rc

def hasContent(filename, beginOfComment = '#'):
    '''Tests whether a file has a content without empty lines or comment lines.
    @param beginOfComment    this string starts a comment line
    @return: True: there are lines which are not empty and not comments.
    '''
    rc = False
    if os.path.exists(filename):
        with open(filename, 'r') as fp:
            for line in fp:
                line = line.strip()
                if line != '' and not line.startswith(beginOfComment):
                    rc = True
                    break
    return rc

def join(separator, args):
    '''Joins all entries of a list into a string.
    @param separator: the separator between the list items
    @param args: list to join. Items may be not strings
    @return: a string with all items of args separated by separator
    '''
    rc = ''
    if args != None:
        for item in args:
            if rc != '':
                rc += separator
            rc += str(item)
    return rc

def limitItemLength(array, maxLength, elipsis = '...'):
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
                item = item[0:maxLength-lenElipsis] + elipsis
            else:
                item = item[0:maxLength]
        rc.append(item)
    return rc

def minimizeArrayUtfError(lines, logger = None):
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

def minimizeStringUtfError(line, logger = None):
    '''Converts a string of bytes into an UTF-8 string.
    It minimizes the part which can not be converted.
    @param lines: a list of byte lines
    @param logger: None or the error logger
    '''
    rc = ''
    def convert(part):
        try:
            rc = part.decode('utf-8')
        except UnicodeDecodeError as exc:
            if logger != None:
                logger.error('cannot decode: ' + part.decode('ascii', 'ignore')[0:80])
            rc = None
    if len(line) < 10:
        part = convert(line)
        if part != None:
            rc += part
        else:
            try:
                rc = line.decode('latin-1')
            except:
                rc = line.decode('ascii')
    else:
        half = int(len(line) / 2)
        part = convert(line[0:half])
        if part != None:
            rc += part
        else:
            rc += minimizeStringUtfError(line[0:half], logger)
        part = convert(line[half:])
        if part != None:
            rc += part
        else:
            rc += minimizeStringUtfError(line[half:], logger)
    return rc

def regExprCompile(pattern, location, logger = None, isCaseSensitive = False):
    '''Compiles a regular expression.
    @param pattern: a regular expression.
    @param logger: for error logging
    @param isCaseSensitive: true: the case is relevant
    @return: None: error occurred Otherwise: the re.RegExpr instance
    '''
    rc = None
    try:
        rc = re.compile(pattern, 0 if isCaseSensitive else re.I)
    except Exception as exc:
        msg = 'error in regular expression in {}: {}'.format(location, str(exc))
        if logger == None:
            print('+++ ' + msg)
        else:
            logger.error(msg)
    return rc

def toFile(filename, content, separator=''):
    '''Writes a string into a file.
    @param filename: the name of the file to write
    @param content: the string to write
    '''
    if type(content) == list:
        content = separator.join(content)
    mode = 'wb' if type(content) == bytes else 'w'
    with open(filename, mode) as fp:
        fp.write(content)

def toFloat(value):
    '''Converts a string into a float.
    Possible data types: int, date, datetime, float.
    Value of date/datetime: seconds since 1.1.1970
    Value of time: seconds since midnight
    @param value: the string to convert
    @return [float, dataType] or [error_message, dataType] 
    '''
    if type(value) == float:
        rc = value
    else:
        if type(value) != str:
            value = str(value)
        matcher = stringUtilRexprDate.match(value)
        if matcher != None:
            length = len(matcher.group(0))
            value = value[length+1:]
            rc = datetime.datetime(int(matcher.group(1)), int(matcher.group(2)), int(matcher.group(3))).timestamp()
            matcher = stringUtilRexprTime.match(value)
            if matcher != None:
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                secs = (hours * 60 + mins)*60
                rc += secs
                if matcher.group(3):
                    rc += int(matcher.group(3))
        else:
            matcher = stringUtilRexprTime.match(value)
            if matcher != None:
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                rc = (hours * 60 + mins)*60
                if matcher.group(3):
                    rc += int(matcher.group(3))
            else:
                matcher = stringUtilRexprInt.match(value)
                if matcher != None:
                    if matcher.group(3):
                        rc = float(matcher.group(3))
                    elif matcher.group(1):
                        rc = float(int(value[2:], 16))
                    elif matcher.group(2):
                        rc = float(int(value, 8))
                else:
                    try:
                        rc = float(value)
                    except ValueError:
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
    if type(value) == float:
        dataType = 'float' 
        rc = value
    else:
        matcher = stringUtilRexprDate.match(value)
        if matcher != None:
            dataType = 'date'
            length = len(matcher.group(0))
            value = value[length+1:]
            rc = datetime.datetime(int(matcher.group(1)), int(matcher.group(2)), int(matcher.group(3))).timestamp()
            matcher = stringUtilRexprTime.match(value)
            if matcher != None:
                dataType += 'time'
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                secs = (hours * 60 + mins)*60
                rc += secs
                if matcher.group(3):
                    rc += int(matcher.group(3))
        else:
            matcher = stringUtilRexprTime.match(value)
            if matcher != None:
                hours, mins = int(matcher.group(1)), int(matcher.group(2))
                dataType = 'time'
                rc = (hours * 60 + mins)*60
                if matcher.group(3):
                    rc += int(matcher.group(3))
            else:
                matcher = stringUtilRexprInt.match(value)
                if matcher != None:
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
                        rc = 'float (or int or date(time)) expected, found: ' + value
    return [rc, dataType]

def toString(value, dataType, floatPrecision = None):
    '''Converts a numeric value into a string.
    @param value: a numeric value
    @param dataType: 'date', 'datetime', 'time', 'float', 'int'
    @param floatPrecision: None or if the type is a float, the number of digits behind the point
    @return: the value as string
    '''
    if dataType == 'date':
        date = datetime.datetime.fromtimestamp(value)
        rc = date.strftime('%Y.%m.%d')
    elif dataType == 'datetime':
        if type(value) == str and value.find(':') >= 0:
            rc = value
        else:
            date = datetime.datetime.fromtimestamp(value)
            rc = date.strftime('%Y.%m.%d %H:%M')
    elif dataType == 'time':
        if type(value) == 'str' and value.find(':') >= 0:
            rc = value
        else:
            rc = '{:2d}:{:2d}'.format(value / 3600, value % 3600 / 60)
    elif floatPrecision != None:
        if type(value) == str:
            value = float(value)
        aFormat = '{' + ':.{}f'.format(floatPrecision) + '}'
        rc = aFormat.format(value)
    else:
        rc = '{}'.format(value)
    return rc

def tailOfWord(words, wordPrefix):
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
        if ixStart > 0 and not words[ixStart-1].isspace():
            ixStart = words.find(' ' + wordPrefix)
            if ixStart < 0:
                ixStart = words.find('\t' + wordPrefix)
    if ixStart >= 0:
        ixStart += len(wordPrefix)
        ixEnd = words.find(' ', ixStart)
        ixEnd2 = words.find('\t', ixStart)
        if ixEnd < 0 or ixEnd2 > 0 and ixEnd2 < ixEnd:
            ixEnd = ixEnd2
        if ixEnd < 0:
            ixEnd = len(words)
        rc = words[ixStart:ixEnd]
    return rc

def unescChars(text):
    '''Returns the text without escaped meta characters like \n, \t, \\.
    @param text: text to convert
    @return: the text with unescaped chars
    '''
    text = text.replace('\\n', '\n')
    text = text.replace('\\t', '\t')
    text = text.replace('\\\\', '\\')
    return text

if __name__ == '__main__':
    pass
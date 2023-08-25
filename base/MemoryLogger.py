'''
FileLogger.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
from base import Const
from base import Logger
from base import StringUtils

class MemoryLogger(Logger.Logger):
    '''Implements a logger storing the logging messages in an internal array.
    '''

    def __init__(self, verboseLevel: int=0, verboseListMinLevel: int=99):
        '''Constructor.
        @param verboseLevel: > 0: the messages will be printed (to stdout)
        @param verboseListMinLevel: messages with a higher level will be stored
        '''
        Logger.Logger.__init__(self, verboseLevel)
        self._lines = []
        self._listMinLevel = verboseListMinLevel

    def clear(self):
        '''Clears all messages and error messages.
        '''
        Logger.Logger.__init__(self, self._verboseLevel)
        self._lines = []
        self._firstErrors = []
        self._errors = 0

    def contains(self, string: str, errorsToo: bool=False) -> bool:
        '''Tests whether the log contains a given string.
        @param string: string to search
        @param errorsToo: the errors will inspected too
        @return: True: the log (or the errors) contains the string
        '''
        rc = False
        for line in self._lines:
            if not errorsToo and line.startswith('+++'):
                continue
            if line.find(string) >= 0:
                rc = True
                break
        if not rc and errorsToo:
            for line in self._firstErrors:
                if line.find(string) >= 0:
                    rc = True
                    break
        return rc

    def derive(self, logger: Logger, messagesToo: bool=False):
        '''Transfers error to another logger.
        '''
        for item in self._firstErrors:
            logger.error(item)
        if messagesToo:
            for item in self._lines:
                logger.log(item, 4)

    def getMessages(self):
        '''Returns the internal messages as array.
        @return: array of messages
        '''
        return self._lines

    @staticmethod
    def globalLogger():
        '''Returns a global logger.
        '''
        logger = Logger.Logger.globalLogger()
        if logger is None:
            logger = MemoryLogger(Const.LEVEL_DETAIL)
        return logger

    def log(self, message: str, minLevel=Const.LEVEL_SUMMARY) -> bool:
        '''Logs a message.
        @param message: the message to log
        @param minLevel: the logging is done only if _verboseLevel >= minLevel
        @return: True: OK
        '''
        if self._verboseLevel >= minLevel:
            print(message)
        if self._listMinLevel >= minLevel:
            self._lines.append(message)
        return True

    def matches(self, pattern: str, flags: int=0, errorsToo: bool=False) -> bool:
        r'''Tests whether the log contains a given regular expression.
        @param pattern: reg expression to search, e.g. r'\d+'
        @param flags: flags of the method re.compile(), e.g. re.I (for ignore case)
        @param errorsToo: the errors will inspected too
        @return: True: the log contains the string
        '''
        rc = False
        regExpr = StringUtils.regExprCompile(
            pattern, 'memory logger pattern', None, flags == 0)
        if regExpr is not None:
            for line in self._lines:
                if not errorsToo and line.startswith('+++'):
                    continue
                if regExpr.search(line):
                    rc = True
                    break
        if not rc and errorsToo:
            for line in self._firstErrors:
                if regExpr.search(line):
                    rc = True
                    break
        return rc


if __name__ == '__main__':
    pass

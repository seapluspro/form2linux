'''
Logger.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import base.Const

class Logger:
    '''Base class of the loggers.
    The derived class must implement the method log(message)
    '''
    def __init__(self, verboseLevel):
        '''Constructor.
        @param verboseLevel: logging is done only if minLevel < verboseLevel. minLevel is a parameter of log() 
        '''
        self._verboseLevel = verboseLevel
        self._logDebug = True
        self._logInfo = True
        self._errors = 0
        self._maxErrors = 20
        self._firstErrors = []
        self._errorFilter = None
        self._mirrorLogger = None
        self._inUse = False

    def debug(self, message):
        '''Logs a debugging message.
        @param message: the message to log
        @return: True
        '''
        if self._mirrorLogger is not None:
            self._mirrorLogger.debug(message)
        if self._logDebug:
            self._inUse = True
            self.log(message)
            self._inUse = False
        return True

    def error(self, message):
        '''Logs a message.
        @param message: the error message to log
        @return: False
        '''
        if self._mirrorLogger is not None:
            self._mirrorLogger.error(message)
        filtered = self._errorFilter is not None
        if filtered:
            if isinstance(self._errorFilter, str):
                filtered = message.find(self._errorFilter) >= 0
            else:
                filtered = self._errorFilter.search(message) is not None
        if not filtered:
            self._inUse = True
            self.log('+++ ' + message)
            self._errors += 1
            if self._errors < self._maxErrors:
                self._firstErrors.append(message)
            self._inUse = False
        return False

    def info(self, message):
        '''Logs an info message.
        @param message: the message to log
        @return: True
        '''
        if self._mirrorLogger is not None:
            self._mirrorLogger.info(message)
        if self._logInfo:
            self._inUse = True
            self.log(message)
            self._inUse = False
        return True

    def log(self, message=None, minLevel=base.Const.LEVEL_SUMMARY):
        '''Logs a message.
        @param message: the string to log
        @param level: logging will be done only if level >= self._verboseLevel
        '''
        raise NotImplementedError('BaseLogger.log(): must be overriden')

    def setMirror(self, logger):
        '''Sets a "mirror" logger: all messages are logged to the mirror too
        @param logger: the mirror logger
        '''
        if self._mirrorLogger is not None:
            logger.setLogger(self._mirrorLogger)
        self._mirrorLogger = logger

    def setErrorFilter(self, excluded, mirrorsToo=True):
        '''Sets the error filter: if the pattern matches the error is ignored (not logged)
        @param excluded: string: a substring of the ignored error
                re.RegExpression: a compiled regular expression of the ignored errors
        @param mirrorsToo: True: the filter is used for the mirror loggers too
        '''
        self._errorFilter = excluded
        if mirrorsToo and self._mirrorLogger is not None:
            self._mirrorLogger.setErrorFilter(excluded)

    def transferErrors(self, logger):
        '''Transfers the error from another logger.
        @param logger: the source of the errors to transfer
        '''
        self._errors += logger._errors
        self._firstErrors += logger._firstErrors


if __name__ == '__main__':
    pass

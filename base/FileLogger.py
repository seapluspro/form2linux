'''
FileLogger.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import datetime
import os
from base import Const
from base import Logger

class FileLogger(Logger.Logger):
    '''A logging manager storing the log messages into a file.
    '''
    def __init__(self, logfile: str, verboseLevel: int):
        '''Constructor.
        @param logfile: the file for logging
        @param verboseLevel: > 0: logging to stdout too
        '''
        Logger.Logger.__init__(self, verboseLevel)
        self._logfile = logfile
        # Test accessability:
        try:
            with open(self._logfile, 'a', encoding='utf-8'):
                pass
            os.chmod(self._logfile, 0o666)
        except OSError as exc:
            msg = f'+++ cannot open logfile {self._logfile}: {exc}'
            print(msg)
            self.error(msg)

    def log(self, message: str, minLevel=Const.LEVEL_SUMMARY) -> bool:
        '''Logs a message.
        @param message: the message to log
        @param minLevel: the logging is done only if _verboseLevel >= minLevel
        @return: true: OK false: error on log file writing
        '''
        rc = False
        try:
            if not self._inUse and self._mirrorLogger is not None:
                self._mirrorLogger.log(message)
            now = datetime.datetime.now()
            message = now.strftime('%Y.%m.%d %H:%M:%S ') + message
            if self._verboseLevel >= minLevel:
                print(message)
            with open(self._logfile, 'a', encoding='utf-8') as fp:
                rc = True
                fp.write(message + '\n')
        except OSError as exc:
            print(str(exc))
        return rc


if __name__ == '__main__':
    pass

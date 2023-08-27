'''
Builder.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import os.path
import shutil
import fnmatch
import subprocess
import time
from text import JsonUtils
from base import Const
from base import MemoryLogger
from base import ProcessHelper
from base import StringUtils
from base import FileHelper

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''

    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = f'E: {msg}'

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg

class GlobalOptions:
    '''Stores the global program arguments.
    '''
    def __init__(self, verbose: bool, dry: bool, needsRoot: bool):
        '''Constructor.
        @param verbose: True: show info messages
        @param dry: say what to do but do not
        @param needsRoot: the task need root rights
        '''
        self.verbose = verbose
        self.dry = dry
        self.needsRoot = needsRoot

class BuilderStatus:
    '''Stores the logger. Needed for unittests.
    '''
    _lastLogger = None
    @staticmethod
    def setLogger(logger):
        '''Sets the logger
        @param logger: the new "global" logger
        '''
        BuilderStatus._lastLogger = logger
    @staticmethod
    def lastLogger():
        '''Return the last created logger.
        @return the last created logger
        '''
        return BuilderStatus._lastLogger

def lastLogger():
    '''Returns the last created instance of a logger.
    '''
    return BuilderStatus.lastLogger()

class Builder:
    '''Base class of all manager classes of form2linux.
    '''
    def __init__(self, needsRoot: bool, options: GlobalOptions):
        '''Constructor.
        @param verbose: <em>True</em>: info messages will be displayed
        @param dry: <em>True</em>: says what to do, but do not change data
        '''
        self._verboseLevel = 3
        self._verbose = options.verbose
        self._dry = options.dry
        self._needsRoot = needsRoot
        self._options = options
        if options.needsRoot != None:
            self._needsRoot = options.needsRoot
        self._variables = {}
        self._wrongFilenameChars = r'[\s;:,?* (){}\[\]]'
        self._root = None
        self._errors = []
        self._dirs = []
        self._files = {}
        self._links = {}
        self._baseDirectory = ''
        self._logger = MemoryLogger.MemoryLogger(Const.LEVEL_DETAIL)
        BuilderStatus.setLogger(self._logger)
        self._processHelper = ProcessHelper.ProcessHelper.__init__(self, self._logger)
        self._standardDirectories = ('boot', 'dev', 'etc', 'etc/default', 'home', 'lib',
                                     'media', 'opt', 'run', 'sys',
                                     'tmp',
                                     'usr', 'usr/bin', 'usr/lib', 'usr/sbin', 'usr/share',
                                     'var', 'var/cache', 'var/lib', 'var/spool',
                                     )

    def error(self, message):
        '''Logs an error.
        @param message: the error message
        '''
        self._logger.error(message)

    def checkDirectories(self):
        '''Tests the entries of the "Directory" section.
        '''
        dirs = self.valueOf('Directories', 'a')
        regExpr = re.compile(r'([:\s$])')
        for item in dirs:
            name = self.replaceVariables(item)
            self.checkPattern('Directories', name, None, self._wrongFilenameChars)
            if name.startswith('/'):
                name = name[1:]
            self._dirs.append(name)

    def checkFiles(self):
        '''Tests the entries of the "Files" section.
        '''
        files = self.valueOf('Files', 'm')
        for file in files:
            target = files[file]
            name = self.replaceVariables(file)
            if self.hasWildcard(name):
                subdir = os.path.dirname(name)
                if not os.path.isdir(subdir):
                    raise CLIError(f'missing directory of file: {name}')
            elif not os.path.exists(name):
                raise CLIError(f'missing file: {name}')
            self._files[name] = target

    def checkLinks(self):
        '''Tests the entries of the "Links" section.
        '''
        files = self.valueOf('Links', 'm')
        regExpr = re.compile(r'([:\s$])')
        for file in files:
            name = self.replaceVariables(file)
            self.checkPattern(f'Links.{file} (source)', name, None, self._wrongFilenameChars)
            target = self.replaceVariables(files[file])
            self.checkPattern(f'Links.{file} (target)', target, None, self._wrongFilenameChars)
            self._links[name] = target

    def checkLinksLate(self):
        '''Tests the entries of the "Links" section after all data are available.
        '''
        for file in self._links:
            full = os.path.join(self._baseDirectory, file)
            if not os.path.exists(full):
                self.error(f'missing link source: {full}')

    def checkNodePattern(self, path: str, pattern: str, wrongCharacters: str=None, errorMessage: str=None) -> str:
        '''Checks a string with regular expressions.
        @param path: the path in the Json tree, e.g. "Person Name"
        @param pattern: None or the pattern that must match
        @param wrongCharacters: None or the characters that must not occur
        @param errorMessage: None or the error message
        @raise CLIError: on error 
        @return: the correct value found at the path
        '''
        value = self.valueOf(path)
        if pattern is not None and re.search(pattern, value) is None:
            if errorMessage is None:
                errorMessage = f'''"{path.replace(' ', '.')}": wrong syntax: {value}'''
            raise CLIError(errorMessage)
        if wrongCharacters is not None:
            matcher = re.search(wrongCharacters, value)
            if matcher is not None:
                CLIError(f'''"{path.replace(' ', '.')}": wrong character "{matcher.group(0)}" in {value}''')
        return value

    def checkPattern(self, name: str, value: str, pattern: str, wrongCharacters: str=None, errorMessage: str=None):
        '''Checks a string with regular expressions.
        @param value: the string to test
        @param name: the name of the value to test
        @param pattern: None or the pattern that must match
        @param wrongCharacters: None or the characters that must not occur
        @param errorMessage: None or the error message
        @raise CLIError: on error 
        '''
        if pattern is not None and re.search(pattern, value) is None:
            if errorMessage is None:
                errorMessage = f'"{name}": wrong syntax: {value}'
            raise CLIError(errorMessage)
        if wrongCharacters is not None:
            matcher = re.search(wrongCharacters, value)
            if matcher is not None:
                CLIError(f'"{name}": wrong character "{matcher.group(0)}" in {value}')

    def copyFile(self, source: str, target: str):
        '''Copies a file if the dry mode is not on.
        @param source: the file to copy
        @param target: the target name
        '''
        if self._dry:
            print(f'sudo cp -a {source} {target}')
        else:
            shutil.copy2(source, target)

    def copyManyFiles(self, source: str, targetDirectory: str):
        '''Copies all files matching a pattern if the dry mode is not on.
        @param source: the file to copy (with wildcards)
        @param targetDirectory: the file will be copied there
        '''
        baseSource = os.path.dirname(source)
        pattern = os.path.basename(source)
        for node in os.listdir(baseSource):
            if fnmatch.fnmatch(node, pattern):
                fullSource = os.path.join(baseSource, node)
                fullTarget = os.path.join(targetDirectory, node)
                self.info(f'{fullSource} -> {fullTarget}')
                self.copyFile(fullSource, fullTarget)

    def ensureDirectory(self, path: str, asRoot: bool=None):
        '''Creates a directory if it does not exists.
        @param path: the name of the directory
        @param asRoot: <em>True</em>: the command must be executed as root
        '''
        if asRoot is None:
            asRoot = self._needsRoot
        if not os.path.exists(path):
            if self.canWrite(asRoot):
                FileHelper.ensureDirectory(path)
            else:
                self.log(f'sudo mkdir -p {path}')

    def finishVariables(self):
        '''Does the things if all variables are inserted: expand the variables in the values.
        '''
        for counter in range(2):
            for key in self._variables:
                self._variables[key] = self.replaceVariables(self._variables[key])
        if counter > 2:
            self.error('Ups')

    def handleDirectories(self):
        '''Handles the directories: all files will be copied.
        '''
        # pylint: disable-next=consider-using-dict-items
        for item in self._dirs:
            subDir = os.path.join(self._baseDirectory, self.replaceVariables(item))
            if not os.path.exists(subDir):
                self.info(f'creating  {subDir}/')
                self.makeDirectory(subDir)
            elif not os.path.isdir(subDir):
                self.error(f'not a directory: {subDir}')

    def handleFiles(self):
        '''Handles the directories: all files will be copied.
        '''
        for item, value in self._files.items():
            source = self.replaceVariables(item)
            hasWildcard = self.hasWildcard(source)
            target = os.path.join(self._baseDirectory, self.replaceVariables(value))
            if target.endswith('/'):
                baseTarget = target[0:-1]
                nodeTarget = os.path.basename(source)
                target += nodeTarget
            elif hasWildcard:
                baseTarget = target
            else:
                baseTarget = os.path.dirname(target)
                nodeTarget = os.path.basename(target)
            if not os.path.isdir(baseTarget):
                self.makeDirectory(baseTarget)
            if not hasWildcard:
                target = os.path.join(baseTarget, nodeTarget)
                self.info(f'{source} -> {target}')
                self.copyFile(source, target)
            else:
                self.copyManyFiles(source, baseTarget)

    def hasWildcard(self, pattern: str) -> bool:
        '''Tests whether a given pattern has at least one wildcard.
        @param pattern: the string to inspect
        @return <em>True</em>: the string has wildcards
        '''
        rc = re.search(r'[*?\[\]]', pattern)
        return rc

    def info(self, message):
        '''Logs an error.
        @param message: the message to log
        '''
        if self._verbose:
            self._logger.info(message)

    def log(self, message):
        '''Logs a message.
        @param message: the message to log
        '''
        self._logger.info(message)

    def makeDirectory(self, name):
        '''Makes a directory (recursive) if the dry mode is not on.
        @param name: the name of the directory to create
        '''
        if self._dry:
            self.log(f'mkdir -p {name}')
        else:
            os.makedirs(name, 0o777)

    def needsRoot(self, needsRoot: bool):
        '''Tests whether being root is needed.
        @param needsRoot: <em>None</em>: use the default value. <em>True</em>: action needs being root
        @return: <em>True</em>: action needs being root
        '''
        rc = needsRoot
        if rc is None:
            rc = self._needsRoot
        return rc

    def canWrite(self, asRoot: bool):
        '''Tests whether being root is needed.
        @param asRoot: <em>None</em>: use the default value. <em>True</em>: action needs being root
        @return: <em>True</em>: action needs being root
        '''
        #if not self._dry and (not asRoot or os.geteuid() == 0):
        rc = not self._dry and (not self.needsRoot(asRoot) or os.geteuid() == 0)
        return rc

    def replaceVariables(self, value: str) -> str:
        '''Tests whether the value contains a variable. In this case it will be replaced by the variable value.
        @param value: the string to inspect
        @return the value with expanded variables
        '''
        if value is not None and isinstance(value, str) and value.find('%(') >= 0:
            for key, value2 in self._variables.items():
                variable = f'%({key})'
                value = value.replace(variable, value2)
        return value

    def runProgram(self, command: str, asRoot: bool=None, verbose: bool=True, outputFile: str=None):
        '''Runs a program if it possible or print the command if not.
        @param command: the command to execute
        @param asRoot: <em>True</em>: the command must be executed as root
        @param verbose: <em>True</em>: show the command
        @param outputFile: <em>None</em> or the file where the program output is stored
        '''
        if self.canWrite(asRoot):
            output = subprocess.check_output(command.split(' '))
            if outputFile is not None:
                StringUtils.toFile(outputFile, output.decode('utf-8'))
            elif verbose and output != b'':
                self.log(output.decode('utf-8'))
        else:
            out = '' if outputFile is None else f' >{outputFile}'
            self.log(f'sudo {command}{out}')

    def saveFile(self, filename, asRoot: bool=None):
        '''Renames a file to a file with a unique name.
        @param filename: the file to save
        @param asRoot: the file can only be written as root
        '''
        if os.path.exists(filename):
            unique = int(time.time())
            self.runProgram(f'mv -v {filename} {filename}.{unique}', True, True)

    def setVariable(self, name, value):
        '''Sets a variable.
        @param name: the variable's name
        @param value: the variable's value
        '''
        self._variables[name] = value

    def valueOf(self, path: str, nodeType: str='s') -> str:
        '''Gets a node of a Json tree.
        @param path: a blank separated list of access nodes
        @param nodeType: the node must have that node type
        @return the value of the node with expanded variables
        '''
        value = JsonUtils.nodeOfJsonTree(self._root, path, nodeType, False)
        value = self.replaceVariables(value)
        return value

    def writeFile(self, filename: str, contents: str, asRoot: bool=None):
        '''Writes a file as root or print a message.
        @param filename: the name of the file to write
        @param contents: the contents of the file
        @param asRoot: the file can only be written as root
        '''
        if self.canWrite(asRoot):
            StringUtils.toFile(filename, contents)
        else:
            self.log(f'# would write to {filename}')

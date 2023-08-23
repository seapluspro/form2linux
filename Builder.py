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
import text.jsonutils as jsonutils
import base.MemoryLogger
import base.ProcessHelper

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''

    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = 'E: %s' % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg

class BuilderStatus:
    '''Stores the logger. Needed for unittests.
    '''
    _lastLogger = None
    @staticmethod
    def setLogger(logger):
        BuilderStatus._lastLogger = logger
    @staticmethod
    def lastLogger():
        return BuilderStatus._lastLogger

def lastLogger():
    '''Returns the last created instance of a logger.
    '''
    return BuilderStatus.lastLogger()

class Builder:
    '''Base class of all manager classes of form2linux.
    '''
    def __init__(self, verbose: bool, dry: bool):
        '''Constructor.
        @param verbose: <em>True</em>: info messages will be displayed
        @param dry: <em>True</em>: says what to do, but do not change data
        '''
        self._verboseLevel = 3
        self._verbose = verbose
        self._variables = {}
        self._root = None
        self._errors = []
        self._dirs = []
        self._files = {}
        self._links = {}
        self._baseDirectory = ''
        self._dry = dry
        self._logger = base.MemoryLogger.MemoryLogger(1)
        BuilderStatus.setLogger(self._logger)
        self._processHelper = base.ProcessHelper.ProcessHelper(self._logger)
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
            match = regExpr.match(name)
            if match is not None:
                raise CLIError(f'wrong character "{match.group(1)}" in directory name: {item}')
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
            match = regExpr.match(name)
            if match is not None:
                raise CLIError(f'wrong character "{match.group(1)}" in link source: {file}')
            target = self.replaceVariables(files[file])
            match = regExpr.match(name)
            if match is not None:
                raise CLIError(f'wrong character "{match.group(1)}" in link target: {target}')
            self._links[name] = target

    def checkLinksLate(self):
        '''Tests the entries of the "Links" section after all data are available.
        '''
        for file in self._links:
            full = os.path.join(self._baseDirectory, file)
            if not os.path.exists(full):
                self.error(f'missing link source: {full}')

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

    def finishVariables(self):
        '''Does the things if all variables are inserted: expand the variables in the values.
        '''
        for no in range(2):
            for key in self._variables:
                self._variables[key] = self.replaceVariables(self._variables[key])
        if no > 2:
            self.error('Ups')

    def handleDirectories(self):
        '''Handles the directories: all files will be copied.
        '''
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
        for item in self._files:
            source = self.replaceVariables(item)
            hasWildcard = self.hasWildcard(source)
            target = os.path.join(self._baseDirectory, self.replaceVariables(self._files[item]))
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

    def replaceVariables(self, value: str) -> str:
        '''Tests whether the value contains a variable. In this case it will be replaced by the variable value.
        @param value: the string to inspect
        @return the value with expanded variables
        '''
        if value is not None and type(value) is str and value.find('%(') >= 0:
            for key in self._variables:
                variable = f'%({key})'
                value = value.replace(variable, self._variables[key])
        return value

    def makeDirectory(self, name):
        '''Makes a directory (recursive) if the dry mode is not on.
        @param name: the name of the directory to create
        '''
        if self._dry:
            self.log(f'mkdir -p {name}')
        else:
            os.makedirs(name, 0o777)

    def runProgram(self, command: str, asRoot: bool=True, verbose: bool=True):
        '''Runs a program if it possible or print the command if not.
        @param command: the command to execute
        @param asRoot: <em>True</em>: the command must be executed as root
        @param verbose: <em>True</em>: show the command
        '''
        if not self._dry and (not asRoot or os.geteuid() == 0):
            output = subprocess.check_output(command.split(' '))
            if verbose and output != b'':
                self.log(output.decode('utf-8'))
        else:
            self.log(f'sudo {command}')

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
        value = jsonutils.nodeOfJsonTree(self._root, path, nodeType, False)
        value = self.replaceVariables(value)
        return value



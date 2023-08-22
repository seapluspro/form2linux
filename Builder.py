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

class Builder:
    def __init__(self, verbose: bool, dry: bool):
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
        self._processHelper = base.ProcessHelper.ProcessHelper(self._logger)
        self._standardDirectories = ('boot', 'dev', 'etc', 'etc/default', 'home', 'lib',
                                     'media', 'opt', 'run', 'sys',
                                     'tmp',
                                     'usr', 'usr/bin', 'usr/lib', 'usr/sbin', 'usr/share',
                                     'var', 'var/cache', 'var/lib', 'var/spool',
                                     )

    def error(self, message):
        self._logger.error(message)

    def checkDirectories(self):
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
        for file in self._links:
            full = os.path.join(self._baseDirectory, file)
            if not os.path.exists(full):
                self.error(f'missing link source: {full}')

    def copyFile(self, source: str, target: str):
        if self._dry:
            print(f'sudo cp -a {source} {target}')
        else:
            shutil.copy2(source, target)

    def copyManyFiles(self, source: str, targetDirectory: str):
        baseSource = os.path.dirname(source)
        pattern = os.path.basename(source)
        for node in os.listdir(baseSource):
            if fnmatch.fnmatch(node, pattern):
                fullSource = os.path.join(baseSource, node)
                fullTarget = os.path.join(targetDirectory, node)
                self.info(f'{fullSource} -> {fullTarget}')
                self.copyFile(fullSource, fullTarget)

    def finishVariables(self):
        for no in range(2):
            for key in self._variables:
                self._variables[key] = self.replaceVariables(self._variables[key])
        if no > 2:
            self.error('Ups')

    def handleDirectories(self):
        for item in self._dirs:
            subDir = os.path.join(self._baseDirectory, self.replaceVariables(item))
            if not os.path.exists(subDir):
                self.info(f'creating  {subDir}/')
                self.makeDirectory(subDir)
            elif not os.path.isdir(subDir):
                self.error(f'not a directory: {subDir}')

    def handleFiles(self):
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
        rc = re.search(r'[*?\[\]]', pattern)
        return rc

    def info(self, message):
        if self._verbose:
            self._logger.info(message)

    def log(self, message):
        self._logger.info(message)

    def replaceVariables(self, value: str) -> str:
        if value is not None and type(value) is str and value.find('%(') >= 0:
            for key in self._variables:
                variable = f'%({key})'
                value = value.replace(variable, self._variables[key])
        return value

    def makeDirectory(self, name):
        if self._dry:
            self.log(f'mkdir -p {name}')
        else:
            os.makedirs(name, 0o777)

    def runProgram(self, command: str, asRoot: bool=True, verbose: bool=True):
        if not asRoot or os.geteuid() == 0:
            output = subprocess.check_output(command.split(' '))
            if verbose:
                self.log(output)
        else:
            self.log(f'sudo {command}')

    def setVariable(self, name, value):
        self._variables[name] = value

    def valueOf(self, path: str, nodeType: str='s') -> str:
        value = jsonutils.nodeOfJsonTree(self._root, path, nodeType, False)
        value = self.replaceVariables(value)
        return value



#! /usr/bin/python3
# encoding: utf-8
'''
form2linux -- shortdesc

form2linux is a command line tool which can some Linux task specified by a form in Json format.

It offers some sub commands:
<ul>
<li>package
    <ul><li>example: prints a example configuration file. Use it as template for a new project.</li<
    <li>check: checks the configuration file</li>
    <li>build: builds the debian package</li>
    </ul>
</li>
<li>service
    <ul><li>example: prints a example configuration file. Use it as template for a new project.</li<
    <li>check: checks the configuration file</li>
    <li>install: build service configuration file and install the service.</li>
    </ul>
</li>
</ul>
@author:     SeaPlusPro

@license:    CC0 Universal

@contact:    seapluspro@gmail.com
@deffield    updated: Updated
'''

import sys
import re
import os
import shutil
import text.jsonutils as jsonutils
import base.MemoryLogger
import base.ProcessHelper
import json
import subprocess
import fnmatch
import pwd
import grp
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter


__all__ = []
__version__ = 0.1
__date__ = '2023-08-20'
__updated__ = '2023-08-20'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = 'E: %s' % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg


class Form2Linux:
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
                target += os.path.dirname(source)
            elif hasWildcard:
                baseTarget = target
            else:
                baseTarget = os.path.dirname(target)
            if not os.path.isdir(baseTarget):
                self.makeDirectory(baseTarget)
            if not hasWildcard:
                target = os.path.join(baseTarget, os.path.basename(source))
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

class DebianBuilder (Form2Linux):
    def __init__(self, verbose: bool, dry: bool):
        Form2Linux.__init__(self, verbose, dry)
        self._verbose = verbose
        self._package = None
        self._version = None
        self._architecture = None
        self._replaces = None
        self._maintainer = None
        self._depends = {}
        self._suggests = []
        self._homepage = None
        self._description = None
        self._notes = []
        self._provides = None
        self._sizeFiles = 0
        self._installedDirs = []
        self._postInstall = None

    def build(self, configuration: str):
        self.check(configuration)
        self._baseDirectory = f'{self._package}-{self._version}'
        self.buildDirectories()
        self.buildFiles()
        self.buildOtherFiles()
        self.checkLinksLate()
        output = subprocess.check_output(['/usr/bin/dpkg', '-b', self._baseDirectory, 
                                          f'{self._baseDirectory}_{self._architecture}.deb'])
        self.log(output.decode('utf-8'))

    def buildDirectories(self):
        if os.path.exists(self._baseDirectory):
            self.info(f'removing {self._baseDirectory}')
            shutil.rmtree(self._baseDirectory)
        if os.path.exists(self._baseDirectory):
            self.error(f'cannot clear base directory: {self._baseDirectory}')
        else:
            self.info(f'creating {self._baseDirectory}/')
            self.makeDirectory(self._baseDirectory)
        self._dirs.append('DEBIAN')
        self.handleDirectories()

    def buildControl(self):
        name = f'{self._baseDirectory}/DEBIAN/control'
        depends = ''
        for item in self._depends:
            if depends == '':
                depends = 'Depends: '
            else:
                depends += ', '
            depends += item
            version = self._depends[item]
            if version != '':
                depends += f' ({version})'
        if depends != '':
            depends = f'\n{depends}'
        suggests = ''
        if len(self._suggests) > 0:
            suggests = f'\nSuggests: {", ".join(self._suggests)}'
        desc = self._description
        for note in self._notes:
            desc += f' {note}\n'
        replaces = '' if self._replaces == '' else f'\nReplaces: {self._replaces}'
        with open(name, 'w') as fp:
            fp.write(f'''Package: {self._package}
Version: {self._version}
Architecture: {self._architecture}{replaces}
Maintainer: {self._maintainer}{depends}{suggests}
Installed-size: {(self._sizeFiles + 1023) // 1024}
Homepage: {self._homepage}
Description: {desc}''')
            self.info(f'written: {name}')

    def buildFiles(self):
        self.handleFiles()
        self.findFiles(self._baseDirectory)
        self.info(f'installed size: {self._sizeFiles}')
        self.buildControl()

    def buildPostInstall(self):
        sumLength = (0 if self._postInstall == '' else 1) + len(self._installedDirs) + len(self._links)
        if sumLength > 0:
            name = f'{self._baseDirectory}/DEBIAN/postinst'
            with open(name, 'w') as fp:
                fp.write('''#! /bin/bash
set -e
PATH=/usr/bin:/bin:/usr/sbin:/sbin
''')
                if len(self._installedDirs) > 0:
                    for item in self._installedDirs:
                        fp.write(f'test -d /{item} || mkdir -p /{item}\n')
                if len(self._links) > 0:
                    for item in self._links:
                        target = self._links[item]
                        partsTarget = target.split('/')
                        partsSource = item.split('/')
                        # Remove common prefix:
                        while len(partsTarget) > 0 and len(partsSource) > 0 and partsTarget[0] == partsSource[0]:
                            del partsTarget[0]
                            del partsSource[0]
                        relLink = '../' * (len(partsTarget) - 1) + '/'.join(partsSource)
                        fp.write(f'test -L /{target} || ln -s /{target} {relLink}\n')
                if self._postInstall != '':
                    with open(self._postInstall, 'r') as fp2:
                        contents = fp2.read()
                        lines = 1 + contents.count('\n')
                        self.info(f'read: {self._postInstall} with {lines} line(s)')
                    fp.write(contents)
                self.info(f'written: {name}')
            os.chmod(name, 0o775)
            
    def buildOtherFiles(self):
        self.buildPostInstall()

    def check(self, configuration: str):
        self.log(f'current directory: {os.getcwd()}')
        with open(configuration, 'r') as fp:
            data = fp.read()
            try:
                self._root = root = json.loads(data)
                path = 'Project:m Directories:a Files:m Links:m PostInstall:s'
                jsonutils.checkJsonMapAndRaise(root, path, True, 'Variables:m')
                project = root['Project']
                path = 'Package:s Version:s Architecture:s Provides:s Replaces:s Suggests:a Maintainer:s ' + \
                    'Depends:m Homepage:s Description:s Notes:a'
                jsonutils.checkJsonMapAndRaise(project, path, True, 'Variables')
                variables = root['Variables']
                for name in variables:
                    self.setVariable(name, variables[name])
                self.finishVariables()
                self._package = self.valueOf('Project Package')
                if not re.match(r'^[\w-]+$', self._package):
                    raise CLIError(f'wrong Project.Package: {self._package}')
                self._version = self.valueOf('Project Version')
                if not re.match(r'^\d+\.\d+\.\d+$', self._version):
                    raise CLIError(f'wrong Project.Version: {self._version}')
                self._architecture = self.valueOf('Project Architecture')
                if not re.match(r'^(amd64|arm64|all)$', self._architecture):
                    raise CLIError(f'wrong Project.Architecture: {self._architecture}')
                self._maintainer = self.valueOf('Project Maintainer')
                self._postInstall = self.valueOf('PostInstall')
                if self._postInstall != '' and not os.path.exists(self._postInstall):
                    raise CLIError(f'PostInstall file not found: {self._postInstall}')
                depends = self.valueOf('Project Depends', 'm')
                for key in depends:
                    value = depends[key]
                    if value != '':
                        if not re.match(r'^[<>=]* ?\d+\.\d+', value):
                            raise CLIError(f'wrong Project.Dependency: {key}: {value}')
                    self._depends[key] = value
                self._provides = self.valueOf('Project Provides')
                if self._provides == '' or self._provides == '*':
                    self._provides = self._package
                self._replaces = self.valueOf('Project Replaces')
                self._homepage = self.valueOf('Project Homepage')
                if not re.match(r'^https?://', self._homepage):
                    raise CLIError('wrong Project.Homepage: {self._homepage}')
                self._description = self.valueOf('Project Description')
                notices = self.valueOf('Project Notes', 'a')
                for notice in notices:
                    self._notes.append(notice)
                self.log(f'= configuration syntax is OK: {configuration}')
                self.checkFiles()
                self.checkDirectories()
                self.checkLinks()
                #self.checkLinks()
            except Exception as exc:
                self.error(f'{exc}')

    def findFiles(self, base):
        nodes = os.listdir(base)
        prefixLength = len(self._baseDirectory) + 1
        for node in nodes:
            full = os.path.join(base, node)
            if os.path.isdir(full):
                if node != 'DEBIAN':
                    self._installedDirs.append(full[prefixLength:])
                    self.findFiles(full)
            elif base != self._baseDirectory:
                self._sizeFiles += os.path.getsize(full)

class ServiceBuilder (Form2Linux):
    def __init__(self, verbose: bool, dry: bool):
        Form2Linux.__init__(self, verbose, dry)
        self._name = None
        self._file = None
        self._description = None
        self._user = None
        self._group = None
        self._workingDirectory = None
        self._environment = None
        self._execStart = None
        self._execReload = None
        self._syslogId = None
        self._output = None
        self._error = None
        self._restart = None
        self._restartSec = None

    def buildFile(self):
        with open(self._file, 'w') as fp:
            group = '' if self._group == '' else f'\nGroup={self._group}'
            reload = f'ExecReload={self._execReload}'
            if self._execReload == '':
                reload = f'# {reload}'
            fp.write(f'''[Unit]
Description={self._description}
After=syslog.target
[Service]
Type=simple
User={self._user}{group}
WorkingDirectory={self._workingDirectory}
EnvironmentFile={self._environment}
ExecStart={self._execStart}
{reload}
SyslogIdentifier={self._syslogId}
StandardOutput={self._output}
StandardError={self._error}
Restart={self._restart}
RestartSec={self._restartSec}
[Install]
WantedBy=multi-user.target
''')
            self.info(f'written: {self._file}')

    def check(self, configuration: str):
        with open(configuration, 'r') as fp:
            data = fp.read()
            try:
                self._root = root = json.loads(data)
                path = 'Service:m Directories:a Files:m Links:m'
                jsonutils.checkJsonMapAndRaise(root, path, True, 'Variables:m')
                service = root['Service']
                path = 'Name:s Description:s File:s User:s Group:s WorkingDirectory:s EnvironmentFile:s' + \
                    ' ExecStart:s ExecReload:s SyslogIdentifier:s StandardOutput:s StandardError:s Restart:s RestartSec:i'
                jsonutils.checkJsonMapAndRaise(service, path, True)
                variables = root['Variables']
                for name in variables:
                    self.setVariable(name, variables[name])
                self.finishVariables()
                self._name = self.valueOf('Service Name')
                if not re.match(r'^[\w-]+$', self._name):
                    raise CLIError(f'wrong Service.Name: {self._name}')
                self._file = self.valueOf('Service File')
                if re.search(r'\s', self._file):
                    raise CLIError(f'wrong Service.File: {self._file}')
                self._description = self.valueOf('Service Description')
                self._user = self.valueOf('Service User')
                if self._user == '':
                    self._user = 'nobody'
                if not re.match(r'^[\w-]+$', self._user):
                    raise CLIError(f'wrong Service.User: {self._user}')
                self._group = self.valueOf('Service Group')
                if self._group != '' and not re.match(r'^[\w-]+$', self._group):
                    raise CLIError(f'wrong Service.Group: {self._group}')
                self._environment = self.valueOf('Service EnvironmentFile')
                if re.search(r'\s', self._environment):
                    raise CLIError(f'wrong Service.EnvironmentFile: {self._environment}')
                self._execStart = self.valueOf('Service ExecStart')
                self._execReload = self.valueOf('Service ExecReload')
                self._syslogId = self.valueOf('Service SyslogIdentifier')
                self._output = self.valueOf('Service StandardOutput')
                self._error = self.valueOf('Service StandardError')
                self._restart = self.valueOf('Service Restart')
                self._restartSec = self.valueOf('Service RestartSec', 'i')
                self.log(f'= configuration syntax is OK: {configuration}')
                self.checkFiles()
                self.checkDirectories()
                self.checkLinks()
                #self.checkLinks()
            except Exception as exc:
                self.error(f'{exc}')

    def install(self, configuration: str):
        self.check(configuration)
        self.handleFiles()
        self.handleDirectories()
        self.buildFile()
        self.prepareUser()
        self.runProgram(f'systemctl enable {self._name}', True)
        self.runProgram(f'systemctl start {self._name}', True)
        self.runProgram(f'systemctl status {self._name}', True)
    
    def prepareUser(self):
        try:
            pwd.getpwnam(self._user)
        except KeyError:
            self.runProgram(f'useradd --system -m --no-user-group -s /usr/sbin/nologin {self._user}', True)
        try:
            grp.getgrnam(self._group)
        except KeyError:
            self.runProgram(f'groupadd --system {self._user}', True)

def examplePackage():
    print('''{
  "Variables": {
     "VERSION": "0.6.3",
     "BASE": "usr/share/cppknife-%(VERSION)"
  },
  "Project": {
    "Package": "cppknife",
    "Version": "%(VERSION)",
    "Architecture": "amd64",
    "Maintainer": "SeaPlusPro <seapluspro@gmail.com>",
    "Replaces": "",
    "Depends": {
      "libc6": ">= 2.36",
      "libgdal-dev": ""
      },
    "Provides": "*",
    "Suggests": [
      "cppknife-db"
      ],
    "Homepage": "https://github.com/seapluspro/cppknife",
    "Description": "Shared libraries for C++ programming and tools using that.",
    "Notes": [
      "The heart is the shared library libcppknife as a helper for fast programming a command line C++ program.",
      "Also there are the programs textknife, fileknife, geoknife, sesknife, osknife which demonstrate the usage of the library."
    ]
  },
  "Directories": [
    "usr/lib",
    "usr/local/bin",
    "usr/share",
    "%(BASE)"
    ],
  "Files": {
    "../build.release/libcppknife-%(VERSION).so": "%(BASE)/libcppknife-%(VERSION).so",
    "../build.release/libcppknifegeo-%(VERSION).so": "%(BASE)/",
    "../build.release/fileknife": "%(BASE)/",
    "../build.release/textknife": "%(BASE)/",
    "../build.release/sesknife": "%(BASE)/",
    "../basic/*.hpp": "%(BASE)/basic/",
    "../db/*.hpp": "%(BASE)/db/",
    "../core/*.hpp": "%(BASE)/core/",
    "../net/*.hpp": "%(BASE)/net/",
    "../geo/*.hpp": "%(BASE)/geo/",
    "../text/*.hpp": "%(BASE)/text/",
    "../tools/*.hpp": "%(BASE)/tools/"
  },
  "Links": {
    "%(BASE)/libcppknife-%(VERSION).so": "usr/lib/libcppknife-%(VERSION).so",
    "%(BASE)/libcppknifegeo-%(VERSION).so": "usr/lib/libcppknifegeo-%(VERSION).so",
    "%(BASE)/fileknife": "usr/local/bin/fileknife-%(VERSION)",
    "%(BASE)/textknife": "usr/local/bin/textknife-%(VERSION)",
    "%(BASE)/sesknife": "usr/local/bin/sesknife-%(VERSION)"
  },
  "PostInstall": "postinst2"
}
''')
def exampleService():
    print('''{
  "Variables": {
    "SERVICE": "examplesv",
    "USER": "nobody",
    "SCRIPT_NODE": "%(SERVICE)",
    "SCRIPT": "/usr/local/bin/%(SCRIPT_NODE)"
  },
  "Service": {
    "Name": "%(SERVICE)",
    "Description": "A example service doing nothing.",
    "File": "/etc/systemd/system/%(SERVICE).service",
    "User": "%(USER)",
    "Group": "%(USER)",
    "WorkingDirectory": "/tmp",
    "EnvironmentFile": "-/etc/%(SERVICE)/%(SERVICE).env",
    "ExecStart": "%(SCRIPT) daemon",
    "ExecReload": "%(SCRIPT) reload",
    "SyslogIdentifier": "%(SERVICE)",
    "StandardOutput": "syslog",
    "StandardError": "syslog",
    "Restart": "always",
    "RestartSec": 5
  },
  "Directories": [
    "/usr/local/bin",
    "/var/log/local",
    "/etc/%(SERVICE)"
  ],
  "Files": {
    "scripts/%(SCRIPT_NODE)": "/etc/%(SERVICE)/"
  },
  "Links": {
    "/etc/%(SERVICE)/": "/usr/local/bin/%(SERVICE)"
  }
}
''')

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    program_name = os.path.basename(argv[0])
    program_version = 'v%s' % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split('\n')[1]
    program_license = '''%s

  Created by SeePlusPro on %s.
  Copyright 2023 SeePlusPro. All rights reserved.

  Licensed under the CC0 1.0 Universal
  https://creativecommons.org/publicdomain/zero/1.0/deed.en

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

Examples:

form2linux --help

form2linux package example
form2linux package example package.json
form2linux package build package.json

form2linux service example
form2linux service example service.json
form2linux service build service.json

''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument('-v', '--verbose', dest='verbose', action='count', help='set verbosity level [default: %(default)s]')
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument('-y', '--dry', dest='dry', action="store_true", help="do not create files and directories")

        subparsersMain = parser.add_subparsers(help='sub-command help', dest='main')
        parserPackage = subparsersMain.add_parser(
            'package', help='Builds a debian package from a package description in Json format.')
        subparsersPackage = parserPackage.add_subparsers(
            help='package help', dest='package')
        
        parserExample = subparsersPackage.add_parser(
            'example', help='shows an example configuration file. Can be used for initializing a new package project.')
        parserCheck = subparsersPackage.add_parser(
            'check', help='checks the configuration file')
        parserCheck.add_argument(
            'configuration', help='the configuration file', default='project.json')
        parserBuild = subparsersPackage.add_parser(
            'build', help='builds the debian package')
        parserBuild.add_argument(
            'configuration', help='defines the properties and the contents of the Debian package.', default='package.json')

        parserService = subparsersMain.add_parser(
            'service', help='Installs a SystemD service.')
        subparsersService = parserService.add_subparsers(
            help='service help', dest='service')
        parserExampleService = subparsersService.add_parser(
            'example', help='shows an example configuration file. Can be used as template for a new service.')
        parserCheckService = subparsersService.add_parser(
            'check', help='checks the configuration file')
        parserCheckService.add_argument(
            'configuration', help='the configuration file', default='project.json')
        parserInstallService = subparsersService.add_parser(
            'install', help='Installs a systemd service defined by a Json configuration file.')
        parserInstallService.add_argument(
            'configuration', help='defines the properties of the service.', default='service.json')
        # Process arguments
        args = parser.parse_args(argv[1:])

        verbose = args.verbose
        dry = args.dry
        if args.main == 'package':
            if args.package == 'example':
                examplePackage()
            elif args.package == 'check':
                builder = DebianBuilder(verbose, dry)
                builder.check(args.configuration)
            elif args.package == 'build':
                builder = DebianBuilder(verbose, dry)
                builder.build(args.configuration)
            else:
                raise CLIError(f'unknown command: {args.package}')
        elif args.main == 'service':
            if args.service == 'example':
                exampleService()
            elif args.service == 'check':
                builder = ServiceBuilder(verbose, dry)
                builder.check(args.configuration)
            elif args.service == 'install':
                builder = ServiceBuilder(verbose, dry)
                builder.install(args.configuration)
            else:
                raise CLIError(f'unknown command: {args.package}')
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * ' '
        sys.stderr.write(program_name + ': ' + repr(e) + '\n')
        sys.stderr.write(indent + '  for help use --help')
        return 2

if __name__ == '__main__':
    sys.exit(main())
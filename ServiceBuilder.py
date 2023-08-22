'''
ServiceBuilder.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import json
import pwd
import grp
import text.jsonutils as jsonutils
from Builder import Builder, CLIError

class ServiceBuilder (Builder):
    def __init__(self, verbose: bool, dry: bool):
        Builder.__init__(self, verbose, dry)
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
                # self.checkLinks()
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


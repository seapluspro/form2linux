'''
InstallBuilder.py

Created on: 23.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import re
import os.path
import json
import pwd
import grp
import time
from typing import Sequence
from text import JsonUtils
from base import StringUtils
from base import FileHelper
from Builder import Builder, CLIError, GlobalOptions
from text import TextProcessor


class InstallBuilder (Builder):
    '''Processes the "setup" command.
    '''

    def __init__(self, options: GlobalOptions):
        '''Constructor.
        @param verbose: <em>True</em>: info messages will be displayed
        @param dry: <em>True</em>: says what to do, but do not change data
        '''
        Builder.__init__(self, True, options)
        self._baseDirectory = None
        self._packages = []
        self._mailHub = None
        self._users = []
        self._modeSmtp = None
        self._baseSmtp = None
        self._patternPackages = r'^[\w.+:-]+$'

    def buildSsmtp(self):
        '''Builds the configuration of the package ssmtp.
        '''
        needsRoot = self._baseSmtp.startswith('/etc')
        self.ensureDirectory(self._baseSmtp, needsRoot)
        full = os.path.join(self._baseSmtp, 'ssmtp.conf')
        self.saveFile(full, needsRoot)
        if self._mailHub.find('gmx') >= 0:
            rewriteDomain = 'rewriteDomain=gmx.net\nhostname=gmx.net'
        else:
            rewriteDomain = '# rewriteDomain=gmx.net\n# hostname=gmx.net'
        if self._modeSmtp == 'StartTLS':
            tls = f'UseSTARTTLS=YES'
        elif self._modeSmtp == 'TLS':
            tls = f'TLS=YES'
        contents = f'''# generated by Form2Linux
root={self._senderSmtp}
mailhub={self._mailHub}
{rewriteDomain}
FromLineOverride=YES
AuthUser={self._senderSmtp}
AuthPass={self._codeSmtp}
{tls}
TLS_CA_File=/etc/pki/tls/certs/ca-bundle.crt
'''
        self.writeFile(full, contents, needsRoot)
        full = os.path.join(self._baseSmtp, 'revaliases')
        if len(self._users) > 0:
            self.saveFile(full, needsRoot)
            contents = []
            for user in self._users:
                contents.append(f'{user}:{self._senderSmtp}:{self._mailHub}\n')
        self.writeFile(full, ''.join(contents), needsRoot)

    def checkPhp(self, form: str):
        '''Checks the input data for the method adaptUsers() and stores the data that must be inserted.
        @param form: the filename of the form with the Json configuration
        '''
        with open(form, 'r', encoding='utf-8') as fp:
            data = fp.read()
            self._root = root = json.loads(data)
            variables = root['Variables']
            for name in variables:
                self.setVariable(name, variables[name])
            self.finishVariables()
            entries = 'ConfigurationDirectory:s Repository:m Packages:a CliReplacements:a FpmReplacements:a Variables:m'
            JsonUtils.checkJsonMapAndRaise(root, entries, True, 'Comment:s')
            entries = "File:s Contents:s Initialization:a"
            JsonUtils.checkJsonMapAndRaise(root['Repository'], entries, True, 'Comment:s')
            self._baseDirectory = self.checkNodePattern('ConfigurationDirectory', None, self._wrongFilenameChars)
            self._fileRepository = self.checkNodePattern('Repository File', None, self._wrongFilenameChars)
            self._contentsRepository = self.checkNodePattern('Repository Contents', '^deb https://', None)
            self._initRepository = self.valueOf('Repository Initialization', 'a')
            packages = self.valueOf('Packages', 'a')
            for item in packages:
                item = self.replaceVariables(item)
                for name in item.split(' '):
                    self.checkPattern('Packages', name, self._patternPackages)
                    self._packages.append(name)
            # Ssmtp:
            
            self._fpmRules = []
            self._cliRules = []
            self.checkRules(root['FpmReplacements'], 'FpmReplacement', self._fpmRules)
            self.checkRules(root['CliReplacements'], 'CliReplacement', self._cliRules)

    def checkStandardHost(self, form: str):
        '''Checks the input data for the method adaptUsers() and stores the data that must be inserted.
        @param form: the filename of the form with the Json configuration
        '''
        with open(form, 'r', encoding='utf-8') as fp:
            data = fp.read()
            self._root = root = json.loads(data)
            variables = root['Variables']
            for name in variables:
                self.setVariable(name, variables[name])
            self.finishVariables()
            entries = 'ConfigurationDirectory:s Packages:a Ssmtp:m Variables:m'
            JsonUtils.checkJsonMapAndRaise(root, entries, True, 'Comment:s')
            self._baseDirectory = self.checkNodePattern('ConfigurationDirectory', None, self._wrongFilenameChars)
            packages = self.valueOf('Packages', 'a')
            for item in packages:
                item = self.replaceVariables(item)
                for name in item.split(' '):
                    self.checkPattern('Packages', name, self._patternPackages)
                    self._packages.append(name)
            # Ssmtp:
            entries = 'Directory:s Sender:s !Code:s MailHub:s Users:s Mode:s'
            JsonUtils.checkJsonMapAndRaise(root['Ssmtp'], entries, True, 'Comment:s')
            
            self._baseSmtp = self.checkNodePattern('Ssmtp Directory', None, self._wrongFilenameChars)
            self._senderSmtp = self.checkNodePattern('Ssmtp Sender', None, r'[:;/,*?]')
            if self._senderSmtp.find('@') < 0:
                raise CLIError(f'wrong Ssmtp.Sender: {self._senderSmtp} missing @')
            self._codeSmtp = self.valueOf('Ssmtp !Code')
            if self._codeSmtp == '':
                raise CLIError('empty Ssmtp.Code')
            self._mailHub = self.checkNodePattern('Ssmtp MailHub', r'^[\w.+-]+:\d+')
            users = self.valueOf('Ssmtp Users')
            for user in users.split(','):
                user = user.strip()
                self.checkPattern('Ssmtp.Users', user, None, r'[^\w.+-]')
                self._users.append(user)
            self._modeSmtp = self.valueOf('Ssmtp Mode')
            if self._modeSmtp not in ('StartTLS', 'TLS'):
                raise CLIError(f'wrong Ssmtp.Mode: {self._modeSmtp} Use StartTLS or TLS')

    def examplePhp(self, filename: str):
        '''Shows the example for the configuration of the command "standard-host".
        @param filename: None or the file to store
        '''
        self._example(filename, r'''{
  "Variables": {
    "VERSION": "8.2"
  },
  "ConfigurationDirectory": "/etc/php/%(VERSION)",
  "Repository": { 
      "File": "/etc/apt/sources.list.d/php.list", 
      "Contents": "deb https://packages.sury.org/php/ bookworm main",
      "Initialization": [
        "sudo rm -f /tmp/php.gpg",
        "wget -qO /tmp/php.gpg https://packages.sury.org/php/apt.gpg",
        "sudo cp -a /tmp/php.gpg /etc/apt/trusted.gpg.d/php.gpg"
      ]
   },
  "Comment": "php8.2-xdebug php8.2-pgsql",
  "Packages": [
      "php%(VERSION) php%(VERSION)-curl php%(VERSION)-gd php%(VERSION)-igbinary",
      "php%(VERSION)-imagick php%(VERSION)-intl php%(VERSION)-mbstring",
      "php%(VERSION)-memcached php%(VERSION)-mysql php%(VERSION)-opcache",
      "php%(VERSION)-readline php%(VERSION)-redis",
      "php%(VERSION)-msgpack php%(VERSION)-phpdbg php%(VERSION)-xml",
      "php%(VERSION)-zip"
  ],
  "FpmReplacements": [
    "memory_limit|2048M",
    "upload_max_filesize|512M",
    "max_file_uploads|100",
    "post_max_size|512M",
    "max_execution_time|600",
    "max_input_time|600",
    "default_socket_timeout|600",
    "session.save_handler|redis|^\\[Session\\]",
    "session.save_path|\"tcp://127.0.0.1:6379\"|^session.save_handler",
    "opcache.enable|1|^\\[opcache\\]",
    "opcache.memory_consumption|1024|opcache.enable",
    "opcache.interned_strings_buffer|512|^opcache.memory_consumption"
  ],
  "CliReplacements": [
    "memory_limit|2048M", 
    "upload_max_filesize|512M",
    "max_file_uploads|100",
    "post_max_size|512M",
    "max_execution_time|600",
    "max_input_time|600",
    "default_socket_timeout|600"
  ]
}
''')

    def exampleStandardHost(self, filename: str):
        '''Shows the example for the configuration of the command "standard-host".
        @param filename: None or the file to store
        '''
        self._example(filename, '''{
  "Variables": {
    "EMAIL": "any@gmx.de"
  },
  "ConfigurationDirectory": "/etc/form2linux",
  "Packages": [
      "htop iotop tmux bzip2 zip unzip rsync sudo zram-tools smartmontools wget curl",
      "nfs-common nfs-kernel-server nmap openssh-server iotop jnettop ssl-cert ca-certificates net-tools ntp",
      "ssmtp sharutils"
  ],
  "Ssmtp": {
      "Directory": "/etc/ssmtp",
      "Sender": "%(EMAIL)",
      "!Code": "",
      "MailHub": "mail.gmx.net:587",
      "Users": "root,jonny",
      "Comment": "StartTLS or TLS",
      "Mode": "StartTLS"
  }
}
''')

    def php(self, form: str):
        '''Installs php packages for a server and adapts the configuration.
        @param form: the filename of the form with Json format
        '''
        self.checkPhp(form)
        self.archiveForm('php', form)
        if not os.path.exists(self._fileRepository):
            self.phpRepository()
        self.installPackages(self._packages)
        needsRoot = self._baseDirectory.startswith('/etc')
        filename = os.path.join(self._baseDirectory, 'fpm', 'php.ini')
        self._adaptVariables(filename, self._fpmRules, needsRoot)
        filename = os.path.join(self._baseDirectory, 'cli', 'php.ini')
        self._adaptVariables(filename, self._cliRules, needsRoot)

    def phpRepository(self):
        '''Prepare the apt repository for PHP.
        '''
        StringUtils.toFile(self._fileRepository, self._contentsRepository)
        for command in self._initRepository:
            if not command.startswith('#'):
                if command.startswith('sudo'):
                    needsRoot = True
                    command = command[5:]
                else:
                    needsRoot = False
                self.runProgram(command, needsRoot, True)
        self.updatePackages()

    def standardHost(self, form):
        '''Installs standard packages for a server
        @param form: the name of the form with Json format
        '''
        self.checkStandardHost(form)
        self.archiveForm('standard-host', form)
        self.installPackages(self._packages)
        needsRoot = self._baseDirectory.startswith('/etc')
        self.ensureDirectory(self._baseDirectory, needsRoot)
        self.buildSsmtp()


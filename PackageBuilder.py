'''
FileHelper.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''

import os.path
import subprocess
import shutil
import json
import re
import text.jsonutils as jsonutils
from Builder import Builder, CLIError

class PackageBuilder (Builder):
    def __init__(self, verbose: bool, dry: bool):
        Builder.__init__(self, verbose, dry)
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
        self._postRemove = None

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
if [ "$1" = configure ]; then
''')
                if len(self._installedDirs) > 0:
                    for item in self._installedDirs:
                        if item not in self._standardDirectories:
                            fp.write(f'test -d /{item} || mkdir -p /{item}\n')
                if len(self._links) > 0:
                    for item in self._links:
                        target = self._links[item]
                        if target.endswith('/'):
                            target += os.path.basename(item)
                        partsTarget = target.split('/')
                        partsSource = item.split('/')
                        # Remove common prefix:
                        while len(partsTarget) > 0 and len(partsSource) > 0 and partsTarget[0] == partsSource[0]:
                            del partsTarget[0]
                            del partsSource[0]
                        relLink = '../' * (len(partsTarget) - 1) + '/'.join(partsSource)
                        fp.write(f'test -L /{target} && rm -f /{target}\nln -s {relLink} /{target}\n')
                if self._postInstall is not None and self._postInstall != '':
                    with open(self._postInstall, 'r') as fp2:
                        contents = fp2.read()
                        lines = 1 + contents.count('\n')
                        self.info(f'read: {self._postInstall} with {lines} line(s)')
                    fp.write(contents)
                fp.write('fi\n')
                fp.write('exit 0\n')
                self.info(f'written: {name}')

            os.chmod(name, 0o775)

    def buildPostRm(self):
        sumLength = (0 if self._postRemove == '' else 1) + len(self._installedDirs) + len(self._links)
        if sumLength > 0:
            name = f'{self._baseDirectory}/DEBIAN/postrm'
            with open(name, 'w') as fp:
                fp.write('''#! /bin/bash
set -e
PATH=/usr/bin:/bin:/usr/sbin:/sbin
''')
                if self._postRemove is not None and self._postRemove != '':
                    with open(self._postRemove, 'r') as fp2:
                        contents = fp2.read()
                        lines = 1 + contents.count('\n')
                        self.info(f'read: {self._postRemove} with {lines} line(s)')
                    fp.write(contents)
                if len(self._links) > 0:
                    for item in self._links:
                        target = self._links[item]
                        if target.endswith('/'):
                            target += os.path.basename(item)
                        fp.write(f'test -L /{target} && rm -f /{target}\n')
                if len(self._installedDirs) > 0:
                    sorted = self._installedDirs[:]
                    sorted.sort(key=lambda x: -len(x))
                    for item in sorted:
                        if item not in self._standardDirectories:
                            fp.write(f'test -d /{item} && rmdir /{item}\n')
                fp.write('exit 0\n')
                self.info(f'written: {name}')
            os.chmod(name, 0o775)

    def buildOtherFiles(self):
        self.buildPostInstall()
        self.buildPostRm()

    def check(self, configuration: str):
        self.log(f'current directory: {os.getcwd()}')
        with open(configuration, 'r') as fp:
            data = fp.read()
            self._root = root = json.loads(data)
            path = 'Project:m Directories:a Files:m Links:m PostInstall:s PostRemove:s'
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
            self._postRemove = self.valueOf('PostRemove')
            if self._postRemove != '' and not os.path.exists(self._postRemove):
                raise CLIError(f'PostRemove file not found: {self._postRemove}')
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
            # self.checkLinks()

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



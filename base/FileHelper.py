'''
FileHelper.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''

import os
import stat
import datetime
import time
import shutil
import re
import tarfile
import zipfile
import tempfile
import fnmatch

from base import Const
from base import StringUtils
from base import LinuxUtils
from base import ProcessHelper
from base import MemoryLogger
from text import TextProcessor

REG_EXPR_WILDCARDS = re.compile(r'[*?\[\]]')
GLOBAL_UNIT_TEST_MODE = None
CURRDIR_PREFIX = '.' + os.sep


def _error(message: str):
    '''Prints an error message.
    @param message: error message
    @return False: for chaining
    '''
    logger = MemoryLogger.MemoryLogger.globalLogger()
    logger.error(message)
    return False


def _log(message: str, level: int=Const.LEVEL_SUMMARY):
    '''Prints a message.
    @param message: error message
    '''
    logger = MemoryLogger.MemoryLogger.globalLogger()
    logger.log(message, level)


def changeExtendedAttributes(path: str, toAdd: str=None, toDelete: str=None):
    '''Changes the attributes of a file (using from /usr/bin/chattr).
    Important attributes: c(ompression) (no)C(OW) a(ppendOnly) (no)A(timeUpdates) (synchronous)D(irectoryUpdates)
    I(mmutable) (data)J(ournaling) S(ynchronousUpdates) u(ndeletable)
    @param path: that file will be changed
    @param toAdd: None or a list of attributes to add to the file, e.g. "cC"
    @param toDelete: None or a list of attributes to delete from the file, e.g. "cC"
    '''
    if toAdd is None and toDelete is None:
        _error(
            f'changeExtendedAttributes(): missing attributes to add/delete for {path}')
    else:
        helper = ProcessHelper.ProcessHelper(MemoryLogger.MemoryLogger.globalLogger())
        argv = ['/usr/bin/chattr']
        if toAdd:
            argv.append(f'+{toAdd}')
        if toDelete:
            argv.append(f'-{toDelete}')
        argv.append(path)
        helper.execute(argv, True)


def clearDirectory(path: str):
    '''Deletes (recursivly) all files and subdirectories of a given path.
    Note: if the path is not a directory (or it does not exists) it will not be handled as an error
    @param path: the directory to clear
    '''
    if os.path.exists(path):
        for node in os.listdir(path):
            full = path + os.sep + node
            if os.path.isdir(full):
                shutil.rmtree(full, True)
            else:
                os.unlink(full)
            if os.path.exists(full):
                _error('cannot remove: ' + full)


def createBackup(source: str, target: str=None, extension: str=None,
                 expandPlaceholders: bool=True, checkEqualNames: bool=True):
    '''Save the source as target to save a file as backup.
    @param source: the file to backup
    @param target: the "safe place" of the file
    @param expandPlaceholders: True: the following placeholders in target will be expanded:
        @see expandPathPlaceholders() for more info
    @param checkEqualNames: True: the test is done whether source != target
    '''
    if target is None:
        if extension.find('%') >= 0:
            extension = expandPlaceholders(extension, source)
        if not extension.startswith('.'):
            extension = '.' + extension
        deepRename(source, extension, deleteExisting=True)
    else:
        if expandPlaceholders and target.find('%') >= 0:
            target = expandPlaceholders(target, source)
        if os.path.isdir(target):
            target += os.sep + os.path.basename(source)
        elif target.find(os.sep) < 0:
            pass
        if checkEqualNames and os.path.realpath(source) != os.path.realpath(target):
            target += '~'
        if target.os.path.islink(source):
            pass
        else:
            moveFile(source, target)


def createFileTree(files: str, baseDirectory: str):
    '''Creates a directory tree with files specified in a text: each line contains one dir/file
    Specification: one file/dir per line (directories does not have a content)
    filename[|content[|mode[|date]]]
    If content starts with '->' a link is created
    If filename ends with / it is a directory.
    Examples:
    dir1/
    dir1/file1|this is in file|664|2020-01-22 02:44:32
    main.dir|->dir1
    @param files: the text describing the dirs/files
    @param baseDirectory: the tree begins with this directory
    '''
    lines = files.split('\n')
    for line in lines:
        if line.strip() == '':
            continue
        parts = line.split('|')
        full = baseDirectory + os.sep + parts[0]
        if parts[0].endswith('/'):
            full = full[0:-1]
            mode = int(parts[1], 8) if len(parts) > 1 else 0o777
            if not os.path.exists(full):
                os.makedirs(full, mode)
            os.chmod(full, mode)
            if len(parts) > 2:
                date = datetime.datetime.strptime(
                    parts[2], '%Y-%m-%d %H:%M:%S')
                setModified(full, None, date)
        else:
            parent = os.path.dirname(full)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            content = parts[1] if len(parts) > 1 else ''
            mode = int(parts[2], 8) if len(parts) > 2 else 0o666
            if content.startswith('->'):
                if os.path.exists(full):
                    os.unlink(full)
                os.symlink(content[2:], full)
            else:
                StringUtils.toFile(full, content, fileMode=mode)
                if len(parts) > 3:
                    date = datetime.datetime.strptime(
                        parts[3], '%Y-%m-%d %H:%M:%S')
                    setModified(full, None, date)


def copyDirectory(source: str, target: str, option: str=None, verboseLevel: int=0):
    '''Copies all files (and dirs) from source to target directory.
    @param source: the base source directory
    @param target: the base target directoy()
    @param option: None, 'clear' or 'update'
        'clear': all files (and subdirs) of target will be deleted
        'update': only younger or not existing files will be copied False: all files will be copied
    '''
    if option == 'clear':
        if verboseLevel >= Const.LEVEL_DETAIL:
            _log('clearing ' + target, verboseLevel)
        clearDirectory(target)
    for node in os.listdir(source):
        src = source + os.sep + node
        trg = target + os.sep + node
        if os.path.islink(src):
            if not option == 'update' or not os.path.exists(trg):
                ref = os.readlink(src)
                if verboseLevel >= Const.LEVEL_DETAIL:
                    _log(f'symlink: {trg} [{ref}]', verboseLevel)
                try:
                    os.symlink(ref, trg)
                except OSError as exc:
                    _error(f'cannot create a symlink: {ref} -> {trg} [{exc}]')
        elif os.path.isdir(src):
            if option != 'update' or not os.path.exists(trg):
                if verboseLevel >= Const.LEVEL_DETAIL:
                    _log(f'directory: {src} -> {trg}', verboseLevel)
                shutil.copytree(src, trg, True)
            else:
                copyDirectory(src, trg, option)
        else:
            if not os.path.exists(trg) or option == 'update' and os.path.getmtime(src) > os.path.getmtime(trg):
                try:
                    if verboseLevel >= Const.LEVEL_DETAIL:
                        _log(f'{src} -> {trg}', verboseLevel)
                    shutil.copy2(src, trg)
                except OSError as exc:
                    _error(f'cannot copy {trg}: {exc}')


def copyByRules(rules, baseSource: str, baseTarget: str):
    '''Copies directories/files from a given directory tree controlled by a list of rules.
    The rules is a list of lines.
    Each line contains a copy rule: a source file/file pattern followed by a target name and options.
    Separator in the line is the ':', in options ','
    Examples:
    public/index.php
        copy public/index.php to public/index.php
    public/icons:*
        copy public/icons with all subdirectories and files into public/icons
    app/*:*:symlink,dirsonly,except local|test
        creates symbolic links from all directories in the subdir app/ except "common"
    tools/run.template:tools/run.sh
        copies the file tools/run.template and change the name to run.sh
    <options>: symlink filesonly dirsonly "except <rexpr-pattern>" "replace<sep>what<sep>with<sep>"
    @param rules: a list of rules for copying
    @param baseSource the directory tree to copy
    @param baseTarget the target directory. Will be created if it does not exist
    '''
    if os.path.dirname(baseSource) != os.path.dirname(baseTarget):
        _error('source and target does not have the same parent. Not supported')
    elif not os.path.isdir(baseSource):
        _error('not a directory: ' + baseSource)
    else:
        ensureDirectory(baseTarget)
        clearDirectory(baseTarget)
        lineNo = 0
        for rule in rules:
            lineNo += 1
            rule = rule.strip()
            if rule == '' or rule.startswith('#'):
                continue
            if rule.startswith(':'):
                target = rule[1:]
                full = baseTarget + os.sep + target
                _log('create ' + full, Const.LEVEL_DETAIL)
                os.makedirs(full)
                continue
            parts = rule.split(':')
            source = parts[0].lstrip(os.sep)
            opts = {}
            full = baseSource + os.sep + source.lstrip(os.sep)
            toTest = os.path.dirname(full) if hasWildcards(source) else full
            if toTest != '' and not os.path.exists(toTest):
                _error(f'line {lineNo}: source not found: {toTest}')
                continue
            if len(parts) == 1:
                target = source
            elif len(parts) == 2:
                target = parts[1] if parts[1].lstrip(os.sep) != '*' else source
            elif len(parts) == 3:
                target = parts[1] if parts[1].lstrip(os.sep) != '*' else source
                for opt in parts[2].split(','):
                    optParts = opt.split(' ', 2)
                    opts[optParts[0]] = None if len(
                        optParts) < 2 else optParts[1]
                    if re.match(r'^dirsonly|except|filesonly|recursive|replace|symlink$', optParts[0]) is None:
                        _error('unknown option: ' + opt)
                    if optParts[0] == 'replace':
                        value = optParts[1]
                        if value == '' or value.count(value[0]) != 3:
                            _error('wrong syntax in replace option: ' + value)
                            del opts['replace']
            else:
                _error(f'line {lineNo}: too many ":" in: {rule}')
                continue
            copyByRule(full, baseTarget + os.sep +
                       target, opts, source.count(os.sep))


def copyByRule(fnSource: str, fnTarget: str, options: str, depthRelPath: int):
    '''Execute a rule from copyFileTree.
    @param fnSource: the source file/directory
    @param fnTarget: the target
    @param options: a dictionary with (option_name, option_value) pairs
    @param depthRelPath: the depth of the tree from the base directory
    '''
    parentSource = os.path.dirname(fnSource)
    pathSource = parentSource + os.sep if parentSource != '' else ''
    parentTarget = os.path.dirname(fnTarget)
    pathTarget = parentTarget + os.sep if parentTarget != '' else ''
    if parentTarget != '':
        ensureDirectory(parentTarget)
    nodeSource = os.path.basename(fnSource)
    if hasWildcards(nodeSource):
        reExcept = None if 'except' not in options else re.compile(
            options['except'])
        for node in os.listdir('.' if parentSource == '' else parentSource):
            full = pathSource + node
            if not fnmatch.fnmatch(node, nodeSource):
                _log(f'ignoring {full}', Const.LEVEL_DETAIL)
                continue
            if reExcept is not None and reExcept.match(node) is not None:
                _log(f'ignoring {full}', Const.LEVEL_DETAIL)
                continue
            isDir = os.path.isdir(full)
            if 'dirsonly' in options and not isDir:
                _log(f'ignoring non directory {full}', Const.LEVEL_DETAIL)
                continue
            if 'filesonly' in options and isDir:
                _log(f'ignoring directory {full}', Const.LEVEL_DETAIL)
                continue
            copyByRule(pathSource + node, pathTarget +
                       node, options, depthRelPath)
    else:
        if 'symlink' in options:
            depth = fnSource.count(os.sep) + 1
            partsSource = fnSource.split(os.sep)
            relPath = os.sep.join(partsSource[depth - depthRelPath - 1:])
            linkSource = '../' * \
                (1 + depthRelPath) + \
                partsSource[depth - depthRelPath - 2] + os.sep + relPath
            os.symlink(linkSource, fnTarget)
        else:
            if 'dirsonly' in options and not os.path.isdir(fnSource):
                _log(f'ignoring non directory {fnSource}', Const.LEVEL_DETAIL)
            elif 'filesonly' in options and os.path.isdir(fnSource):
                _log(f'ignoring directory {fnSource}', Const.LEVEL_DETAIL)
            else:
                if os.path.isdir(fnSource):
                    if 'recursive' in options:
                        shutil.copytree(fnSource, fnTarget)
                    else:
                        _log('creating ' + fnTarget, Const.LEVEL_DETAIL)
                        os.makedirs(fnTarget)
                        shutil.copystat(fnSource, fnTarget)
                elif 'replace' in options:
                    processor = TextProcessor.TextProcessor(MemoryLogger.MemoryLogger.globalLogger())
                    processor.readFile(fnSource, mustExists=True)
                    value = options['replace']
                    if value == '' or value.count(value[0]) != 3:
                        _error('wrong syntax in replace option: ' + value)
                    else:
                        parts = value[1:].split(value[0], 2)
                        hits = processor.replace(
                            parts[0], parts[1], noRegExpr=True, countHits=True)
                        _log(f'{hits} replacement(s) [{value}] in {fnSource} => {fnTarget}',
                             Const.LEVEL_DETAIL)
                        processor.writeFile(fnTarget)
                else:
                    _log(f'copying {fnSource} => {fnTarget}',
                         Const.LEVEL_DETAIL)
                    shutil.copy2(fnSource, fnTarget, follow_symlinks=False)


def copyIfExists(source: str, target: str):
    '''Copies all files (and dirs) from source to target directory.
    @param source: the base source directory
    @param target: the base target directoy()
    @param verboseLevel: True: do logging
    '''
    if os.path.exists(source):
        _log(f'copying {source} => {target} ...', Const.LEVEL_DETAIL)
        shutil.copy2(source, target)


def deepRename(oldName: str, newNode: str, deleteExisting: bool=False) -> bool:
    '''Renames a file or symbolic link.
    Not symbolic links: renaming "normally".
    Symbolic links: the link target will be renamed. This is useful for backing up files:
    not the symbolic link is the subject to save but the link target.
    @param oldName: the file to rename (with path)
    @param newNode: the new filename (without path)
    @return True: success
    '''
    rc = True
    if not os.path.exists(oldName):
        rc = _error('cannot rename (old name does not exist): ' + oldName)
    elif os.path.islink(oldName):
        source = endOfLinkChain(oldName)
        nodeOld = os.path.basename(source)
        if nodeOld == newNode:
            rc = _error(
                f'cannot rename (link target has the same name {nodeOld}): {oldName}')
        else:
            rc = deepRename(source, newNode)
    else:
        newName = os.path.join(os.path.dirname(oldName), newNode)
        if os.path.exists(newName):
            if not deleteExisting:
                rc = _error('cannot rename (new name exists): ' + newName)
            else:
                _log('deleting ' + newName, Const.LEVEL_LOOP)
                if GLOBAL_UNIT_TEST_MODE == 'deepRename-no-unlink':
                    _log(f'suppressing delete of {newName} ({GLOBAL_UNIT_TEST_MODE})',
                         Const.LEVEL_DETAIL)
                else:
                    os.unlink(newName)
                rc = not os.path.exists(newName)
                if not rc:
                    _error(f'cannot remove new name: {newName}')
        if rc:
            _log(f'renaming {oldName} => {newName}', Const.LEVEL_LOOP)
            os.rename(oldName, newName)
    return rc


def distinctPaths(path1: str, path2: str) -> bool:
    '''Tests whether two paths are not part of each other.
    @param path1: first path to test
    @param path2: 2nd path to test
    @return: True: path1 is not parent of path2 and path2 is not parent of path1
    '''
    dir1 = os.path.realpath(path1)
    dir2 = os.path.realpath(path2)
    return not dir1.startswith(dir2) and not dir2.startswith(dir1)


def endOfLinkChain(filename: str) -> str:
    '''Returns the last entry of a symbolic link chain or None.
    @param filename: the first entry of a symbol link chain
    @return: None: not existing nodes in the link chain Otherwise: the last element of the chain
    '''
    rc = os.path.realpath(filename)
    if not os.path.lexists(rc) or os.path.islink(rc):
        _error(f'invalid entry {rc} in the symbolic link chain: {filename}')
        rc = None
    return rc


def ensureDirectory(directory: str, mode: int=0o777, user: str=None, group: str=None) -> str:
    '''Ensures that the given directory exists.
    @param directory: the complete name
    @return: None: could not create the directory
        otherwise: the directory's name
    '''
    if not os.path.isdir(directory):
        try:
            os.lstat(directory)
            os.unlink(directory)
        except FileNotFoundError:
            pass
        _log(f'creating {directory}{os.sep} ...', Const.LEVEL_SUMMARY)
        try:
            os.makedirs(directory, mode)
            os.chmod(directory, mode)
        except OSError as exc:
            _error(f'cannot create dir {directory}: {exc}')
        if not os.path.isdir(directory):
            directory = None
        elif user is not None or group is not None:
            os.chown(directory, LinuxUtils.userId(
                user), LinuxUtils.groupId(group))
    return directory


def ensureFileDoesNotExist(filename: str):
    '''Ensures that a file does not exist.
    @param filename: the file to delete if it exists.
    '''
    if os.path.lexists(filename):
        try:
            try:
                if os.path.isdir(filename):
                    _log(f'removing {filename}{os.sep} ...',
                         Const.LEVEL_DETAIL)
                    shutil.rmtree(filename, False)
                else:
                    _log(f'removing {filename} ...', Const.LEVEL_DETAIL)
                    os.unlink(filename)
            except OSError as exc:
                _error(f'cannot delete {filename}: {exc}')
        except FileNotFoundError:
            pass


def ensureFileExists(filename: str, content: str=''):
    '''Ensures that a file does not exist.
    @param filename: the file to create if it does not exist
    @param content: this text will be stored for a new created file
    '''
    try:
        if os.path.exists(filename):
            if os.path.isdir(filename):
                _log(f'is a directory: {filename}', Const.LEVEL_DETAIL)
        else:
            _log(f'creating {filename} ...', Const.LEVEL_DETAIL)
            StringUtils.toFile(filename, content)
    except OSError as exc:
        _error(f'problems with {filename}: {exc}')


def ensureSymbolicLink(source: str, target: str, createTarget: bool=True):
    '''Ensures that a directory exists.
    @param source: the full name of the link source, e.g. '../sibling'
    @param target: full name of the file of type 'link'
    @param createTarget: creates the target if it does not exist
    @return: True: the link exists
    '''
    info = None
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        pass
    if info is not None:
        if os.path.islink(target):
            oldLink = os.readlink(target)
            if oldLink != source:
                _log(
                    f'changing link from {oldLink} to {source}', Const.LEVEL_DETAIL)
                os.unlink(target)
        elif os.path.isdir(target):
            _error(f'target {target} is already a directory (not a link)')
        else:
            _log(f'removing the non link file {target}', Const.LEVEL_DETAIL)
            os.unlink(target)
    if not os.path.exists(target):
        baseDir = os.path.dirname(target)
        if not os.path.isdir(baseDir) and createTarget:
            ensureDirectory(baseDir)
        hasParent = os.path.isdir(baseDir)
        if not hasParent:
            _error('parent of target is not a directory: ' + baseDir)
        realPath = os.path.join(target, source)
        absSource = os.path.normpath(realPath)
        if not os.path.exists(absSource):
            _error(f'missing source {source} [= {absSource}]')
        elif hasParent:
            _log(f'creating symbol link {source} -> {target}',
                 Const.LEVEL_DETAIL)
            os.symlink(source, target)
    rc = os.path.islink(target) and os.readlink(target) == source
    return rc


def extendedAttributesOf(path: str) -> str:
    '''Returns the attributes of a file (returned from /usr/bin/lsattr).
    Important attributes: c(ompression) (no)C(OW) a(ppendOnly) (no)A(timeUpdates) (synchronous)D(irectoryUpdates)
    I(mmutable) (data)J(ournaling) S(ynchronousUpdates) u(ndeletable)
    @param path: the file to inspect
    @return: a list of attributes, e.g. 'cC' or ''
    '''
    helper = ProcessHelper.ProcessHelper(MemoryLogger.MemoryLogger.globalLogger())
    helper.execute(['/usr/bin/lsattr', path], False, storeOutput=True)
    rc = ('' if not helper.output() else helper.output()[0]).split(
        ' ')[0].replace('-', '')
    return rc


def expandFiles(path: str, pattern: str, dirsOnly: bool=False, filesOnly: bool=True):
    '''Finds the nodes of a given path matching a given pattern.
    @param path: the nodes of that directory will be inspected
    @param pattern: a pattern with shell wildcards "*", "?", "[a-z]"
    @param dirsOnly: only directories may be in the result
    @param filesOnly: only directories may be in the result
    @return a list of nodes
    '''
    rc = []
    try:
        files = os.listdir(path)
        isDir = False
        checkDir = dirsOnly or filesOnly
        for file in files:
            if checkDir:
                isDir = os.path.isdir(f'{path}/{file}')
            if filesOnly and isDir or dirsOnly and not isDir:
                continue
            if fnmatch.fnmatch(file, pattern):
                rc.append(file)
    except PermissionError as exc:
        _error(f'cannot enter directory {path}: {exc}')
    return rc


def expandPathPlaceholders(pattern: str, filename: str):
    '''Expands placeholders in a pattern with the current date time or parts of a related filename.
    @param pattern: a string with placeholders:
        %date%: the current date %datetime%: the current date and time
        %seconds%: the current date time as seconds after the epoche
        %path%: the path of source %node%: the node of source
        %name%: the name of source (without extension) %ext%: the extension of source
    @param filename: the placeholders can be parts of this filename
    @return: pattern with expanded placeholders
    '''
    parts = splitFilename(filename)
    now = datetime.datetime.now()
    for matcher in re.finditer(r'%(date(time)?|seconds|path|node|name|ext)%', pattern):
        name = matcher.group(1)
        macro = matcher.group(0)
        if name == 'date':
            value = now.strftime('%Y.%m.%d')
        elif name == 'datetime':
            value = now.strftime('%Y.%m.%d-%H_%M_%S')
        elif name == 'seconds':
            value = now.strftime('%a')
        elif name == 'path':
            value = parts['path']
        elif name == 'node':
            value = parts['node']
        elif name == 'name':
            value = parts['fn']
        elif name == 'ext':
            value = parts['ext']
        pattern = pattern.replace(macro, value)
    return pattern


def expandWildcards(path: str, nodesList: str, names):
    '''Expands a path with wildcards and a list of nodes with wildcards into a list of concrete names.
    @param path: that path will inspected. Can have wildcards.
    @param nodesList: a comma separated list of nodes with or without wildcards
    @param names: OUT: a list of concrete full filenames matching the path and the nodeList
    '''
    unprocessed = [path]
    processed = []

    def dirName(x):
        return x if not x.endswith('/') else x[0:-1]
    while len(unprocessed) > 0:
        item = dirName(unprocessed[0])
        unprocessed = unprocessed[1:]
        if not hasWildcards(item):
            if os.path.isdir(item):
                processed.append(item)
        else:
            items = item.split('/')
            ix = -1
            for part in items:
                ix += 1
                if hasWildcards(part):
                    prefix = '' if ix == 0 else '/'.join(items[0:ix])
                    if os.path.isdir(prefix):
                        nodes = expandFiles(prefix, part, True, False)
                        suffix = '' if ix >= len(
                            items) - 1 else '/'.join(items[ix+1:])
                        for node in nodes:
                            unprocessed.append(f'{prefix}/{node}/{suffix}')
                        # Handle only the first wildcard:
                        break
    nodesList2 = nodesList.split(',')
    for path2 in processed:
        path2 = dirName(path2)
        for node in nodesList2:
            if not hasWildcards(node):
                full = f'{path2}/{node}'
                if os.path.exists(full):
                    names.append(full)
            else:
                nodes2 = expandFiles(path2, node, False)
                for node3 in nodes2:
                    full = f'{path2}/{node3}'
                    if os.path.exists(full):
                        names.append(full)


def fileClass(path: str):
    '''Returns the file class of the file.
    @param path: the full filename
    @return: a tuple (class, subclass): class: 'container', 'text', 'binary', 'unknown'
            subclass of 'container': 'dir', 'tar', 'tgz', 'zip'
            subclass of 'text': 'xml', 'shell'
    '''
    def isBinaryByte(theByte):
        rc = theByte < 0x09 or (0x0d < theByte < 0x20)
        return rc

    def isBinary(byteArray):
        found = 0
        rc = False
        # for ix in range(len(byteArray)):
        #    theByte = byteArray[ix]
        for theByte in byteArray:
            if theByte == b'\x00':
                rc = True
                break
            if isBinaryByte(theByte):
                found += 1
                if found > 100 or found > len(byteArray) / 10:
                    rc = True
                    break
        return rc

    def isNullString(byteArray) -> bool:
        '''Tests whether the byteArray is a text delimited with 0.
        @param byteArray: array to test
        @return True: only text and '\0' is part of byteArray
        '''
        ix = 0
        rc = True
        hasNull = False
        while ix < len(byteArray):
            if byteArray[ix] == 0:
                hasNull = True
            elif isBinaryByte(byteArray[ix]):
                rc = False
                break
            ix += 1
        return rc and hasNull

    def isNullNumber(byteArray) -> bool:
        '''Tests whether the byteArray are digits delimited with 0.
        @param byteArray: array to test
        @return True: only decimal digits and '\0' is part of byteArray
        '''
        ix = 0
        rc = True
        hasNull = False
        while ix < len(byteArray):
            if byteArray[ix] == 0:
                hasNull = True
            elif not (byteArray[ix] >= 0x30 and byteArray[ix] <= 0x39):  # TAB
                rc = False
                break
            ix += 1
        return rc and hasNull
    if os.path.isdir(path):
        (theClass, subClass) = ('container', 'dir')
    else:
        with open(path, 'rb') as fp:
            start = fp.read(4096)
            if start.startswith(b'\x1f\x8b\x08'):
                (theClass, subClass) = ('container', 'tar')
            elif start.startswith(b'BZ') and isBinary(start[8:80]):
                (theClass, subClass) = ('container', 'tar')
            elif start.startswith(b'PK') and isBinary(start[2:32]):
                (theClass, subClass) = ('container', 'zip')
            elif isNullString(start[0:100]) and isNullNumber(start[100:0x98]):
                (theClass, subClass) = ('container', 'tar')
            elif (start[0:100].lower().find(b'<xml>') >= 0 or start[0:100].lower().find(b'<html') >= 0) and not isBinary(start):
                (theClass, subClass) = ('text', 'xml')
            elif len(start) > 5 and start.startswith(b'#!') and not isBinary(start):
                (theClass, subClass) = ('text', 'shell')
            elif isBinary(start):
                (theClass, subClass) = ('binary', 'binary')
            else:
                (theClass, subClass) = ('text', 'text')
    return (theClass, subClass)


def fileContains(string: str, filename: str) -> bool:
    rc = False
    with open(filename, 'r', encoding='utf-8') as fp:
        for line in fp:
            if line.find(string) >= 0:
                rc = True
                break
    return rc
    
def fileType(path: str) -> str:
    '''Returns the file type: 'file', 'dir', 'link', 'block'
    @param path: the full filename
    @return: the filetype: 'file', 'dir', 'link', 'block', 'char'
    '''
    if os.path.islink(path):
        rc = 'link'
    elif os.path.isdir(path):
        rc = 'dir'
    else:
        rc = 'file'
    return rc


def fromBytes(line) -> str:
    '''Converts a line with type bytes into type str.
    @param line: line to convert
    '''
    try:
        rc = line.decode()
    except UnicodeDecodeError:
        try:
            rc = line.decode('latin-1')
        except UnicodeDecodeError:
            rc = line.decode('ascii', 'ignore')
    return rc


def hasWildcards(filename: str) -> bool:
    '''Tests whether a filename has wildcards.
    @param filename: filename to test
    @return: True: the filename contains wildcard like '*', '?' or '[...]'
    '''
    rc = REG_EXPR_WILDCARDS.search(filename) is not None
    return rc


def joinFilename(parts):
    '''Joins an array of parts  into a filename.
    This is the other part of splitFilename().
    @param parts: the array created by splitFilename
    @return the filename decribed in parts
    '''
    rc = parts['path'] + parts['fn'] + parts['ext']
    return rc


def joinRelativePath(relPath: str, start: str=None):
    '''Joins a relative path and a start path to a non relative path.
    Example: joinPath('../brother', '/parent/sister') is '/parent/brother'
    @param relPath: the relative path, e.g. '../sister'
    @param start: the start point for joining, e.g. 'family/sister'. If None: the current directory
    @returns the non relative path, e.g. 'family/brother'
    '''
    rc = None
    relParts = relPath.split(os.sep)
    if start is None:
        start = os.curdir
    startParts = start.split(os.sep)
    if not relParts or relParts[0] != '..':
        _error('not a relative path: ' + relPath)
    else:
        rc = ''
        while relParts and relParts[0] == '..':
            if not startParts:
                _error(
                    f'too many backsteps in relpath {relPath} for start {start}')
                rc = None
                break
            relParts = relParts[1:]
            startParts = startParts[0:-1]
        if rc is not None:
            rc = os.sep.join(startParts)
            if relParts:
                if rc == '':
                    rc = os.sep.join(relParts)
                else:
                    rc += os.sep + os.sep.join(relParts)
    return rc


def listFile(statInfo, full: str, orderDateSize: bool=True, humanReadable: bool=True) -> str:
    '''Builds the info for one file (or directory)
    @param statInfo: the info returned by os.(l)stat()
    @param full: the filename
    @param orderDateSize: True: order is date left of size False: order is size leftof date
    @param humanReadable: True: better for reading (matching unit), e.g. "10.7 GByte" or "3 kByte"
    '''
    if full.startswith(CURRDIR_PREFIX):
        full = full[2:]
    if stat.S_ISDIR(statInfo.st_mode):
        size = '<dir>'
    elif stat.S_ISLNK(statInfo.st_mode):
        size = '<link>'
        full += ' -> ' + os.readlink(full)
    elif humanReadable:
        size = f'{StringUtils.formatSize(statInfo.st_size):-8}'
    else:
        size = f'{statInfo.st_size / 1000000:13.6f} MB'
    fdate = datetime.datetime.fromtimestamp(statInfo.st_mtime)
    dateString = fdate.strftime("%Y.%m.%d %H:%M:%S")
    if orderDateSize:
        rc = f'{dateString} {size:-12} {full}'
    else:
        rc = f'{size:-12} {dateString} {full}'
    return rc


def mountPointOf(path: str, mountFile: str='/proc/mounts'):
    '''Returns the mount point of the filesystem of a given directory.
    @param path: the path to inspect
    @return: (<mount-point>, <fstype>) the mount point of the filesystem containing the path and the filesystem name
    '''
    rc = None
    fsType = None
    with open(mountFile, 'r', encoding='utf-8') as fp:
        for line in fp:
            parts = line.split(' ')
            if len(parts) > 3 and path.startswith(parts[1]) and (rc is None or len(rc) < len(parts[1])):
                fsType = parts[2]
                rc = parts[1]
    return (rc, fsType)


def moveFile(source: str, target: str, removeAlways: bool=True, createBaseDir: bool=True):
    '''Moves a file from one location to another.
    If both parent directories are in the same filesytem rename is used.
    Otherwise a copy is done and a deletion of the source.
    @param source: the file to move
    @param target: the target filename
    @param removeAlways: True: the source will be deleted after copying
    @param createBaseDir: True: the parent directory of target will be created if it does not exists
    '''
    if createBaseDir:
        baseDir = os.path.dirname(target)
        ensureDirectory(baseDir)
    try:
        os.rename(source, target)
    except OSError:
        try:
            shutil.copy2(source, target)
            if removeAlways:
                try:
                    os.unlink(source)
                except OSError as exc2:
                    _error(f'cannot delete {source} after moving: {exc2}')
        except OSError as exc:
            _error(f'cannot copy {source} to {target}: {exc}')


def pathToNode(path: str) -> str:
    '''Changed a path into a name which can be used as node (of a filename).
    @param path: the path to convert
    @return: path with replaced path separators
    '''
    rc = path.replace(os.sep, '_').replace(':', '_')
    return rc


def replaceExtension(filename: str, extension: str) -> str:
    '''Replaces the extension of a filename.
    @param filename: the filename to process
    @param extension: the new extension
    @return: the filename with the new extension
    '''
    ix = filename.rfind('.')
    ix2 = filename.rfind(os.sep)
    if ix > ix2 + 1:
        rc = filename[0:ix] + extension
    else:
        rc = filename + extension
    return rc


def splitFilename(full: str):
    '''Splits a filename into its parts.
    This is the other part of joinFilename().
    @param full: the filename with path
    @return: a dictionary with the keys 'full', 'path', 'node', 'fn', 'ext'
        example: { 'full': '/home/jonny.txt', 'path': '/home/', 'node' : 'jonny.txt', 'fn': 'jonny' , 'ext': '.txt' }
    '''
    rc = {}
    rc['full'] = full
    ix = full.rfind(os.sep)
    if ix < 0:
        rc['path'] = ''
        node = rc['node'] = full
    else:
        rc['path'] = full[0:ix + 1]
        node = rc['node'] = full[ix + 1:]
    ix = node.rfind('.', 1)
    if ix < 0:
        rc['fn'] = node
        rc['ext'] = ''
    else:
        rc['fn'] = node[0:ix]
        rc['ext'] = node[ix:]
    return rc


def setUnitTestMode(mode):
    '''Sets special behaviour for unit tests.
    '''
    global GLOBAL_UNIT_TEST_MODE
    GLOBAL_UNIT_TEST_MODE = mode


def setModified(path: str, timeUnix, date: datetime.datetime=None):
    '''Sets the file modification time.
    @precondition: exactly one of date and timeUnix must be None and the other not None
    @param path: the full path of the file to modify
    @param timeUnix: None or the time to set (unix timestamp since 1.1.1970)
    @param date: None or the datetime to set (datetime.datetime instance)
    @return: True: success False: precondition raised
    '''
    dateModified = None
    rc = True
    if date is not None:
        dateModified = time.mktime(date.timetuple())
    elif timeUnix is None:
        rc = False
    else:
        dateModified = timeUnix
    if dateModified is not None:
        try:
            os.utime(path, (int(dateModified), int(dateModified)))
        except Exception as exc:
            raise exc
    return rc


def tail(filename: str, maxLines: int=1, withLineNumbers: bool=False):
    '''Returns the tail of a given file.
    @param filename: the file to inspect
    @param maxLines: the number of lines to return (or less)
    @param withLineNumbers: True: add line numbers at the begin of line
    @return: a list of lines from the end of the file
    '''
    lines = []
    maxLines = max(1, maxLines)
    with open(filename, "r", encoding='utf-8') as fp:
        lineNo = 0
        for line in fp:
            lineNo += 1
            if len(lines) >= maxLines:
                del lines[0]
            lines.append(line)
        if withLineNumbers:
            lineNo -= len(lines) - 1
            for ix, line in enumerate(lines):
                lines[ix] = f'{lineNo}: {line}'
                lineNo += 1
    return lines


def tempDirectory(node: str, subDir: str=None) -> str:
    '''Returns the name of a directory laying in the temporary directory.
    @param node: the filename without path
    @param subdir: None or a subdirectory in the temp directory (may be created)
    '''
    path = tempfile.gettempdir() + os.sep
    if subDir is not None:
        path += subDir + os.sep
    path += node
    if not os.path.exists(path):
        os.makedirs(path, 0o777, True)
    return path

def tempFile(node: str, subDir: str=None, subDir2: str=None) -> str:
    '''Returns the name of a file laying in the temporary directory.
    @param node: the filename without path
    @param subdir: None or a subdirectory in the temp directory (may be created)
    '''
    path = tempfile.gettempdir() + os.sep
    if subDir is not None:
        path += subDir
        if subDir2 is not None:
            path += os.sep + subDir2
        if not os.path.exists(path):
            os.makedirs(path, 0o777, True)
        path += os.sep
    path += node
    return path


def unpack(archive: str, target: str, clear: bool=False):
    '''Copies the content of an archive (tar, zip...) into a given directory.
    @param archive: name of the archive, the extension defines the type: '.tgz': tar '.zip': zip
    @param target: the directory which will be filled by the archive content. Will be created if needed
    '''
    if not os.path.exists(target):
        os.makedirs(target, 0o777, True)
    elif not os.path.isdir(target):
        _error('target is not a directory: ' + target)
        archive = None
    elif clear:
        clearDirectory(target)
    if archive is None:
        pass
    elif archive.endswith('.tgz'):
        with tarfile.open(archive, 'r:gz') as tar:
            tar.extractall(target)
    elif archive.endswith('.zip'):
        with zipfile.ZipFile(archive, 'r') as zipFile:
            zipFile.extractall(target)
    else:
        _error('unknown file extend: ' + archive)


if __name__ == '__main__':
    pass

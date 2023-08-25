'''
FileHelperTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import sys
import unittest

import shutil
import datetime
import time
import os.path

from base import MemoryLogger
from base import FileHelper
from base import StringUtils

def inDebug(): return False

class FileHelperTest(unittest.TestCase):
    def setUp(self):
        self._logger = MemoryLogger.MemoryLogger(1)
        self._baseNode = 'unittest.fh'
        self._baseDir = FileHelper.tempDirectory('filetool', self._baseNode)
        self._fn = FileHelper.tempFile('first.txt', self._baseNode, 'filetool')
        StringUtils.toFile(self._fn, "line 1\nline 2\nThis file is in line 3")

    def tearDown(self):
        if os.path.isdir(self._baseDir):
            shutil.rmtree(self._baseDir)

    def assertDirExists(self, filename):
        self.assertTrue(os.path.isdir(filename))

    def assertFileContains(self, filename: str, text: str):
        self.assertTrue(FileHelper.fileContains(filename, text))

    def assertFileContent(self, expected: str, filename: str):
        contents = StringUtils.fromFile(filename)
        self.assertEqual(contents, expected)

    def assertFileExists(self, filename):
        self.assertTrue(os.path.exists(filename), f'missing {filename}')
        
    def assertFileNotExists(self, filename):
        self.assertFalse(os.path.exists(filename), f'unexpected file: {filename}')
        
    def ensureFileDoesNotExist(self, filename):
        if os.path.exists(filename):
            if os.path.isdir(filename):
                shutil.rmtree(filename, True)
            else:
                os.unlink(filename)

    def assertNone(self, item):
        self.assertEquals(None, item)

    def checkPart(self, container, full, path, node, fn, ext):
        self.assertEqual(path, container['path'])
        self.assertEqual(full, container['full'])
        self.assertEqual(node, container['node'])
        self.assertEqual(fn, container['fn'])
        self.assertEqual(ext, container['ext'])
        self.assertEqual(full, FileHelper.joinFilename(container))

    def testSplitFilenameJoinFilename(self):
        if inDebug(): return
        container = FileHelper.splitFilename('/tmp/jonny.txt')
        self.checkPart(container, '/tmp/jonny.txt', '/tmp/', 'jonny.txt', 'jonny', '.txt')
        container = FileHelper.splitFilename('/home/authors/jonny.txt')
        self.checkPart(container, '/home/authors/jonny.txt', '/home/authors/', 'jonny.txt', 'jonny', '.txt')
        container = FileHelper.splitFilename('jonny.v2.txt')
        self.checkPart(container, 'jonny.v2.txt', '', 'jonny.v2.txt', 'jonny.v2', '.txt')
        container = FileHelper.splitFilename('.config')
        self.checkPart(container, '.config', '', '.config', '.config', '')

    def testTail(self):
        if inDebug(): return
        tail = FileHelper.tail(self._fn)
        self.assertEqual(1, len(tail))
        self.assertEqual('This file is in line 3', tail[0])

    def testTailNumbers(self):
        if inDebug(): return
        tail = FileHelper.tail(self._fn, 2, True)
        self.assertEqual(2, len(tail))
        asString = ''.join(tail)
        self.assertEqual('2: line 2\n3: This file is in line 3', asString)

    def testPathToNode(self):
        if inDebug(): return
        self.assertEqual('x__abc_def_x.txt', FileHelper.pathToNode('x:/abc/def/x.txt'))

    def testSetModified(self):
        if inDebug(): return
        fn = FileHelper.tempFile('test.txt', self._baseNode)
        StringUtils.toFile(fn, 'Hi')
        yesterday = int(time.time()) - 86400
        januar = datetime.datetime(2016, 1, 2, 10, 22, 55)
        januar2 = time.mktime(januar.timetuple())
        FileHelper.setModified(fn, yesterday)
        self.assertEqual(yesterday, int(os.path.getmtime(fn)))
        FileHelper.setModified(fn, None, januar)
        self.assertEqual(januar2, os.path.getmtime(fn))

    def testDistinctPaths(self):
        if inDebug(): return
        tempDirectory = FileHelper.tempDirectory('disticts', self._baseNode)
        FileHelper.clearDirectory(tempDirectory)
        dir1 = tempDirectory + os.sep + 'abc'
        dir2 = tempDirectory + os.sep + 'def'
        dirLink = tempDirectory + os.sep + 'link'
        dirChild = dir1 + os.sep + 'child'
        dirChildInLink = dirLink + os.sep + 'childInLink'
        dirLinkLink = dir1 + os.sep + 'linkLink'
        FileHelper.ensureDirectory(dir1)
        FileHelper.ensureDirectory(dir2)
        FileHelper.ensureDirectory(dirChild)
        os.symlink(dir2, dirLink)
        os.symlink(dirChildInLink, dirLinkLink)
        # base/abc
        # base/abc/child
        # base/abc/linkInLink -> def
        # base/def
        # base/link -> def
        # base/def/childInLink
        # base/def/linkLink -> def/childInLink
        self.assertTrue(FileHelper.distinctPaths(dir1, dir2))
        self.assertTrue(FileHelper.distinctPaths(dir2, dir1))
        self.assertTrue(FileHelper.distinctPaths(dirChild, dir2))
        self.assertTrue(FileHelper.distinctPaths(dir2, dirChild))
        self.assertTrue(FileHelper.distinctPaths(dir1, dirLink))
        self.assertTrue(FileHelper.distinctPaths(dirLink, dir1))

        self.assertFalse(FileHelper.distinctPaths(dirChild, dir1))
        self.assertFalse(FileHelper.distinctPaths(dir1, dirChild))
        self.assertFalse(FileHelper.distinctPaths(dir2, dirLink))
        self.assertFalse(FileHelper.distinctPaths(dirLink, dir2))
        self.assertFalse(FileHelper.distinctPaths(dir2, dirChildInLink))
        self.assertFalse(FileHelper.distinctPaths(dirChildInLink, dir2))
        self.assertFalse(FileHelper.distinctPaths(dir2, dirLinkLink))
        self.assertFalse(FileHelper.distinctPaths(dirLinkLink, dir2))
        self.assertFalse(FileHelper.distinctPaths(dirChildInLink, dirLinkLink))
        self.assertFalse(FileHelper.distinctPaths(dirLinkLink, dirChildInLink))
        self.assertFalse(FileHelper.distinctPaths(dirLinkLink, dir2))
        self.assertFalse(FileHelper.distinctPaths(dir2, dirLinkLink))

    def testFromBytes(self):
        if inDebug(): return
        self.assertEqual('ascii', FileHelper.fromBytes(b'ascii'))
        self.assertEqual('äöüÖÄÜß', FileHelper.fromBytes('äöüÖÄÜß'.encode('utf_8')))
        line = 'äöüÖÄÜß'.encode('latin-1')
        self.assertEqual('äöüÖÄÜß', FileHelper.fromBytes(line))
        line = 'äöüÖÄÜß'.encode('cp850')
        self.assertFalse('äöüÖÄÜß' == FileHelper.fromBytes(line))
        line = b''
        hexString = ''
        for ix in range(1, 255):
            hexString += "{:02x}".format(ix)
        line = bytes.fromhex(hexString)
        self.assertFalse('äöüÖÄÜß' == FileHelper.fromBytes(line))

    def testEnsureDir(self):
        if inDebug(): return
        temp = FileHelper.tempDirectory('dir1', self._baseNode)
        # already exists
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))
        # does not exist with logger
        self.ensureFileDoesNotExist(temp)
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))
        # does not exist without logger
        self.ensureFileDoesNotExist(temp)
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))
        # file exists, with logger
        self.ensureFileDoesNotExist(temp)
        StringUtils.toFile(temp, 'anything')
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))
        # file exists, with logger
        self.ensureFileDoesNotExist(temp)
        StringUtils.toFile(temp, 'anything')
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))
        # invalid link, with logger
        self.ensureFileDoesNotExist(temp)
        os.symlink('../does-not-exist', temp)
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))
        # invalid link, without logger
        self.ensureFileDoesNotExist(temp)
        os.symlink('../does-not-exist2', temp)
        FileHelper.ensureDirectory(temp)
        self.assertTrue(os.path.isdir(temp))

    def testEnsureFileDoesNotExist(self):
        if inDebug(): return
        temp = FileHelper.tempDirectory('file', self._baseNode)
        # directory exists
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))
        # does not exists:
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))
        # file exists
        StringUtils.toFile(temp, 'x')
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))
        StringUtils.toFile(temp, 'x')
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))
        # invalid link exists
        os.symlink('../invalid-link-source', temp)
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))
        os.symlink('../invalid-link-source', temp)
        FileHelper.ensureFileDoesNotExist(temp)
        self.assertFalse(os.path.exists(temp))

    def testEnsureSymbolicLink(self):
        if inDebug(): return
        tempDirectory = FileHelper.tempDirectory('jail', self._baseNode)
        target = tempDirectory + os.sep + 'parent'
        # creating base dir and target:
        self.ensureFileDoesNotExist(tempDirectory)
        FileHelper.tempDirectory('sibling', self._baseNode)
        FileHelper.ensureSymbolicLink('../../sibling', target)
        self.assertTrue(os.path.islink(target))
        self.assertEqual('../../sibling', os.readlink(target))
        # changing link source:
        FileHelper.tempDirectory('sibling2', self._baseNode)
        FileHelper.ensureSymbolicLink('../../sibling2', target, True)
        self.assertTrue(os.path.islink(target))
        self.assertEqual('../../sibling2', os.readlink(target))
        # removing existing target:
        self.ensureFileDoesNotExist(target)
        StringUtils.toFile(target, 'anything')
        FileHelper.ensureSymbolicLink('../../sibling2', target, True)
        self.assertTrue(os.path.islink(target))
        self.assertEqual('../../sibling2', os.readlink(target))

    def testEnsureSymbolicLinkErrors(self):
        if inDebug(): return
        tempDirectory = FileHelper.tempDirectory('jail', self._baseNode)
        target = tempDirectory + os.sep + 'parent'
        FileHelper.ensureDirectory(target)
        # creating base dir and target:
        self.ensureFileDoesNotExist(tempDirectory)
        FileHelper.tempDirectory('sibling', self._baseNode)
        self._logger.log('= expecting error is directory')
        FileHelper.ensureSymbolicLink('../../sibling', target, True)
        self.assertFalse(os.path.exists(target))
        # must not create parent:
        self._logger.log('= expecting error missing parent')
        self.ensureFileDoesNotExist(os.path.dirname(target))
        FileHelper.ensureSymbolicLink('../../sibling', target, False)
        self.assertFalse(os.path.exists(target))

    def testFileClass(self):
        if inDebug(): return
        baseDir = '/usr/share/snakeboxx/unittest/data/'
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.zip')
        self.assertEqual('container', aClass)
        self.assertEqual('zip', subClass)
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.tar')
        self.assertEqual('container', aClass)
        self.assertEqual('tar', subClass)
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.tgz')
        self.assertEqual('container', aClass)
        self.assertEqual('tar', subClass)
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.tbz')
        self.assertEqual('container', aClass)
        self.assertEqual('tar', subClass)
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.html')
        self.assertEqual('text', aClass)
        self.assertEqual('xml', subClass)
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.sh')
        self.assertEqual('text', aClass)
        self.assertEqual('shell', subClass)
        aClass, subClass = FileHelper.fileClass(baseDir + 'example.txt')
        self.assertEqual('text', aClass)
        self.assertEqual('text', subClass)

    def testEnsureFileExists(self):
        if inDebug(): return
        fn = FileHelper.tempFile('should.exist.txt', self._baseNode)
        FileHelper.ensureFileDoesNotExist(fn)
        FileHelper.ensureFileExists(fn, 'Hi world')
        self.assertFileContains('Hi world', fn)

    def testEnsureFileExistsError(self):
        if inDebug(): return
        fn = FileHelper.tempDirectory('blocking.dir', self._baseNode)
        self._logger.log('expectig error: blocking dir')
        FileHelper.ensureFileExists(fn, 'Hi')
        self.assertDirExists(fn)

    def testCopyDirectoryClear(self):
        if inDebug(): return
        source = FileHelper.tempDirectory('src', self._baseNode)
        target = FileHelper.tempDirectory('trg', self._baseNode)
        StringUtils.toFile(source + '/hi.txt', 'Hi')
        os.symlink('hi.txt', source + os.sep + 'hi.link.txt')
        source2 = FileHelper.tempDirectory('src/dir1', self._baseNode)
        StringUtils.toFile(source2 + '/wow.txt', 'Wow')
        if not os.path.exists(source2 + '/wow.symlink.txt'):
            os.symlink('wow.txt', source2 + '/wow.symlink.txt')
        FileHelper.copyDirectory(source, target, 'clear', 3)
        self.assertFileContains('Hi', target + '/hi.txt')
        self.assertDirExists(target + '/dir1')
        self.assertFileContains('Wow', target + '/dir1/wow.txt')
        trg2 = target + '/dir1/wow.symlink.txt'
        self.assertFileContains('Wow', trg2)
        self.assertTrue(os.path.islink(trg2))
        fn = target + os.sep + 'hi.link.txt'
        self.assertFileExists(fn)
        self.assertEqual('hi.txt', os.readlink(fn))

    def testCopyDirectoryUpdate(self):
        if inDebug(): return
        source = FileHelper.tempDirectory('src', self._baseNode)
        target = FileHelper.tempDirectory('trg', self._baseNode)
        StringUtils.toFile(source + '/hi.txt', 'Hi')
        source2 = FileHelper.tempDirectory('src/dir1', self._baseNode)
        StringUtils.toFile(source2 + '/wow.txt', 'Wow')
        FileHelper.copyDirectory(source, target, 'clear', 3)
        time.sleep(1)
        StringUtils.toFile(source + '/hi.txt', 'hi!')
        FileHelper.setModified(source + '/hi.txt', 365*24*3600)
        StringUtils.toFile(source + '/hi2.txt', 'hi!')
        StringUtils.toFile(source2 + '/wow2.txt', 'wow!')
        FileHelper.setModified(source2 + '/wow2.txt', 365*24*3600)
        FileHelper.copyDirectory(source, target, 'update')
        self.assertFileContains('Hi', target + '/hi.txt')
        self.assertFileContains('hi!', target + '/hi2.txt')
        self.assertDirExists(target + '/dir1')
        self.assertFileContains('Wow', target + '/dir1/wow.txt')
        self.assertFileContains('wow!', target + '/dir1/wow2.txt')

    def testUnpackTgz(self):
        if inDebug(): return
        target = FileHelper.tempDirectory(self._baseNode)
        fn = target + os.sep + 'dummy'
        StringUtils.toFile(fn, '')
        FileHelper.unpack('/usr/share/snakeboxx/unittest/data/etc.work.tgz', target, True)
        self.assertFileNotExists(fn)
        self.assertFileExists(target + '/etc/passwd')
        self.assertFileExists(target + '/etc/nginx/sites-available/default')

    def testUnpackZip(self):
        if inDebug(): return
        target = FileHelper.tempDirectory('archive', self._baseNode)
        FileHelper.unpack('/usr/share/snakeboxx/unittest/data/example.zip', target, True)
        self.assertFileExists(target + '/All.sh')

    def testTempFile(self):
        if inDebug(): return
        fn = FileHelper.tempFile('test.txt', 'unittest.2')
        parent = os.path.dirname(fn)
        self.assertEqual('test.txt', os.path.basename(fn))
        self.assertEqual('unittest.2', os.path.basename(parent))
        self.assertFileExists(parent)
        self.ensureFileDoesNotExist(parent)

    def testCreateTree(self):
        if inDebug(): return
        FileHelper.ensureDirectory(self._baseDir)
        FileHelper.createFileTree('''tree1/
tree1/file1|blaBla|660|2020-04-05 11:22:33
tree2/|744|2020-04-06 12:23:34
tree2/file2
tree2/file3|1234|700
tree1/file4
link|->tree1
''', self._baseDir)
        dirName = self._baseDir + os.sep + 'tree1'
        self.assertDirExists(dirName)
        fn = dirName + os.sep + 'file1'
        self.assertFileExists(fn)
        statInfo = os.stat(fn)
        self.assertNotEqual(None, statInfo)
        self.assertEqual('blaBla', StringUtils.fromFile(fn))
        self.assertEqual(0o660, statInfo.st_mode % 0o1000)
        current = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(statInfo.st_mtime))
        self.assertEqual('2020-04-05 11:22:33', current)
        self.assertFileExists(dirName + os.sep + 'file4')
        dirName = self._baseDir + os.sep + 'tree2'
        self.assertDirExists(dirName)
        statInfo = os.lstat(dirName)
        self.assertEqual(0o744, statInfo.st_mode % 0o1000)
        current = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(statInfo.st_mtime))
        self._logger.log('== time test for dirs deactivated')
        #self.assertEqual('2020-04-06 12:23:34', current)
        self.assertFileExists(dirName + os.sep + 'file2')
        fn = dirName + os.sep + 'file3'
        self.assertFileExists(dirName + os.sep + 'file3')
        statInfo = os.stat(fn)
        self.assertNotEqual(None, statInfo)
        self.assertEqual(0o700, statInfo.st_mode % 0o1000)
        self.assertEqual('1234', StringUtils.fromFile(fn))
        fn = self._baseDir + os.sep + 'link'
        self.assertFileExists(fn)
        self.assertTrue(os.path.islink(fn))
        self.assertEqual('tree1', os.readlink(fn))

    def testCopyByRules(self):
        if inDebug(): return
        FileHelper.ensureDirectory(self._baseDir)
        FileHelper.createFileTree('''skeleton/
skeleton/.list|app
skeleton/app/
skeleton/app/test/
skeleton/app/.gitignore|test/
skeleton/app/common/
skeleton/app/common/sql/
skeleton/app/common/sql/common.sql|select * from x;
skeleton/app/users/
skeleton/app/roles/
skeleton/public/
skeleton/public/index.php|<?php
skeleton/public/js/
skeleton/public/js/file1.js|.name { width:3 }
skeleton/public/js/file2.js|.name { width:4 }
skeleton/public/js/global.js|->file1.js
''', self._baseDir)
        rules = '''
# symlinks+except
app/*:*:symlink,dirsonly,except test
# single dir in base dir
.list:*
# single dir
public:*
# single file with replacement
public/index.php:*:replace /php/php>/
# dirtree
public/js:*:recursive
:tmp/down
'''.split('\n')
        baseSource = self._baseDir + os.sep + 'skeleton'
        baseTarget = self._baseDir + os.sep + 'project'
        self.ensureFileDoesNotExist(baseTarget)
        FileHelper.copyByRules(rules, baseSource, baseTarget)
        self.assertFileContent('app', baseTarget + '/.list')
        self.assertDirExists(baseTarget + '/app')
        self.assertFileNotExists(baseTarget + '/app/test')
        self.assertFileNotExists(baseTarget + '/app/.gitignore')
        self.assertFileExists(baseTarget + '/app/common/sql/common.sql')
        self.assertFileContent('select * from x;', baseTarget + '/app/common/sql/common.sql')
        self.assertFileExists(baseTarget + '/app/users')
        self.assertFileExists(baseTarget + '/app/roles')
        self.assertFileContent('<?php>', baseTarget + '/public/index.php')
        self.assertDirExists(baseTarget + '/public/js')
        self.assertFileContent('.name { width:3 }', baseTarget + '/public/js/file1.js')
        self.assertFileContent('.name { width:4 }', baseTarget + '/public/js/file2.js')
        self.assertFileContent('.name { width:3 }', baseTarget + '/public/js/global.js')
        self.assertDirExists(baseTarget + '/tmp/down')

    def testEndOfLinkChain(self):
        if inDebug(): return
        end = self._baseDir + os.sep + 'end.txt'
        StringUtils.toFile(end, 'endOfLink')
        link1 = self._baseDir + os.sep + 'link1'
        FileHelper.ensureFileDoesNotExist(link1)
        os.symlink('link2', link1)
        link2 = self._baseDir + os.sep + 'link2'
        FileHelper.ensureFileDoesNotExist(link2)
        os.symlink('end.txt', link2)
        self.assertEqual(end, FileHelper.endOfLinkChain(link1))
        FileHelper.ensureFileDoesNotExist(end)
        self.assertNone(FileHelper.endOfLinkChain(link1))

    def testDeepRename(self):
        if inDebug(): return
        first = self._baseDir + os.sep + 'first.txt'
        StringUtils.toFile(first, 'first')
        second = self._baseDir + os.sep + 'second.txt'
        FileHelper.ensureFileDoesNotExist(second)
        self.assertTrue(FileHelper.deepRename(first, 'second.txt'))
        self.assertFileNotExists(first)
        self.assertFileContent('first', second)

        third = self._baseDir + os.sep + 'third.txt'
        StringUtils.toFile(third, 'third')
        self.assertTrue(FileHelper.deepRename(second, third, deleteExisting=True))
        self.assertFileNotExists(second)
        self.assertFileContent('first', third)

    def testDeepRenameLink(self):
        if inDebug(): return
        first = self._baseDir + os.sep + 'first.txt'
        StringUtils.toFile(first, 'first')
        second = self._baseDir + os.sep + 'second.txt'
        StringUtils.toFile(second, '2nd')
        FileHelper.ensureFileDoesNotExist(second)
        link1 = self._baseDir + os.sep + 'link1'
        FileHelper.ensureFileDoesNotExist(link1)
        os.symlink('link2', link1)
        link2 = self._baseDir + os.sep + 'link2'
        FileHelper.ensureFileDoesNotExist(link2)
        os.symlink('first.txt', link2)
        self.assertTrue(FileHelper.deepRename(link2, 'second.txt', deleteExisting=True))
        self.assertFileNotExists(first)
        self.assertFileContent('first', second)

    def testDeepRenameLink2(self):
        if inDebug(): return
        first = FileHelper.tempFile('first.txt', 'renamedir')
        StringUtils.toFile(first, 'first')
        second = FileHelper.tempFile('second.txt', 'renamedir')
        StringUtils.toFile(second, '2nd')
        FileHelper.ensureFileDoesNotExist(second)
        link1 = self._baseDir + os.sep + 'link1'
        FileHelper.ensureFileDoesNotExist(link1)
        os.symlink('link2', link1)
        link2 = self._baseDir + os.sep + 'link2'
        FileHelper.ensureFileDoesNotExist(link2)
        os.symlink(first, link2)
        self.assertTrue(FileHelper.deepRename(link2, 'second.txt', deleteExisting=True))
        self.assertFileNotExists(first)
        self.assertFileContent('first', second)

    def testDeepRenameError(self):
        if inDebug(): return
        self._logger.clear()
        self.assertFalse(FileHelper.deepRename('not#existising#file', 'realy#not#existising#file'))
        self.assertTrue(self._logger.contains('old name does not exist', errorsToo=True))

        self._logger.clear()
        first = FileHelper.tempFile('first.txt', 'renamedir')
        StringUtils.toFile(first, '')
        link1 = self._baseDir + os.sep + 'link1'
        FileHelper.ensureFileDoesNotExist(link1)
        os.symlink(first, link1)
        self.assertFalse(FileHelper.deepRename(link1, 'first.txt', deleteExisting=True))
        self.assertTrue(self._logger.contains('link target has the same name', errorsToo=True))

        self._logger.clear()
        second = FileHelper.tempFile('second.txt', 'renamedir')
        StringUtils.toFile(second, '')
        self.assertFalse(FileHelper.deepRename(first, 'second.txt', deleteExisting=False))
        self.assertTrue(self._logger.contains('new name exists', errorsToo=True))

        self._logger.clear()
        FileHelper.setUnitTestMode('deepRename-no-unlink')
        self.assertFalse(FileHelper.deepRename(first, 'second.txt', deleteExisting=True))
        self.assertTrue(self._logger.contains('cannot remove new name', errorsToo=True))
        FileHelper.setUnitTestMode(None)

    def testMoveFileRename(self):
        if inDebug(): return
        first = FileHelper.tempFile('first.txt', 'move')
        second = FileHelper.tempFile('second.txt', 'move', 'trg')
        StringUtils.toFile(first, '')
        FileHelper.moveFile(first, second)
        self.assertFileExists(second)
        self.assertFileNotExists(first)
        
    def testMoveFileCopy(self):
        if inDebug(): return
        srcDir = '/opt/tmp'
        if not os.path.exists(srcDir):
            self._logger.log(f'>>> missing {srcDir}: cannot do the unit test')
        else:
            first = srcDir + os.sep + 'first'
            second = FileHelper.tempFile('second.txt', 'move', 'trg')
            StringUtils.toFile(first, '')
            FileHelper.moveFile(first, second)
            self.assertFileExists(second)
            self.assertFileNotExists(first)

    def testReplaceExtension(self):
        if inDebug(): return
        self.assertEqual('/abc/def.abc', FileHelper.replaceExtension('/abc/def.txt', '.abc'))
        self.assertEqual('/abc/.def.abc', FileHelper.replaceExtension('/abc/.def', '.abc'))

    def testMountPointOf(self):
        #if inDebug(): return
        mounts = FileHelper.tempFile('proc_mounts', 'unittest.files')
        StringUtils.toFile(mounts, '''sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
udev /dev devtmpfs rw,nosuid,relatime,size=15347716k,nr_inodes=3836929,mode=755 0 0
devpts /dev/pts devpts rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
tmpfs /run tmpfs rw,nosuid,noexec,relatime,size=3082092k,mode=755 0 0
/dev/nvme0n1p7 / btrfs rw,relatime,ssd,space_cache,subvolid=5,subvol=/ 0 0
securityfs /sys/kernel/security securityfs rw,nosuid,nodev,noexec,relatime 0 0
tmpfs /sys/fs/cgroup tmpfs ro,nosuid,nodev,noexec,mode=755 0 0
cgroup2 /sys/fs/cgroup/unified cgroup2 rw,nosuid,nodev,noexec,relatime,nsdelegate 0 0
cgroup /sys/fs/cgroup/systemd cgroup rw,nosuid,nodev,noexec,relatime,xattr,name=systemd 0 0
pstore /sys/fs/pstore pstore rw,nosuid,nodev,noexec,relatime 0 0
efivarfs /sys/firmware/efi/efivars efivarfs rw,nosuid,nodev,noexec,relatime 0 0
none /sys/fs/bpf bpf rw,nosuid,nodev,noexec,relatime,mode=700 0 0
cgroup /sys/fs/cgroup/devices cgroup rw,nosuid,nodev,noexec,relatime,devices 0 0
systemd-1 /proc/sys/fs/binfmt_misc autofs rw,relatime,fd=40,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=1421 0 0
hugetlbfs /dev/hugepages hugetlbfs rw,relatime,pagesize=2M 0 0
mqueue /dev/mqueue mqueue rw,relatime 0 0
debugfs /sys/kernel/debug debugfs rw,relatime 0 0
sunrpc /run/rpc_pipefs rpc_pipefs rw,relatime 0 0
nfsd /proc/fs/nfsd nfsd rw,relatime 0 0
/dev/nvme0n1p5 /home btrfs rw,relatime,compress=zlib:3,ssd,space_cache,autodefrag,subvolid=256,subvol=/home 0 0
/dev/nvme0n1p5 /opt btrfs rw,relatime,compress=zlib:3,ssd,space_cache,autodefrag,subvolid=257,subvol=/opt 0 0
tmpfs /run/user/1000 tmpfs rw,nosuid,nodev,relatime,size=3082088k,mode=700,uid=1000,gid=1000 0 0
/dev/sda5 /media/space-nocow ext4 rw,relatime 0 0
''')
        mount, fsType = FileHelper.mountPointOf('/home/jonny/data', mounts)
        self.assertEqual('/home', mount)
        self.assertEqual('btrfs', fsType)
        mount, fsType = FileHelper.mountPointOf('/var/lib/mysql', mounts)
        self.assertEqual('/', mount)
        self.assertEqual('btrfs', fsType)
        mount, fsType = FileHelper.mountPointOf('/media/space-nocow', mounts)
        self.assertEqual('/media/space-nocow', mount)
        self.assertEqual('ext4', fsType)

    def testExtendedAttributesOf(self):
        if inDebug(): return
        fn = FileHelper.tempFile('attributes.data', 'unittest.files')
        StringUtils.toFile(fn, '')
        FileHelper.changeExtendedAttributes(fn, 'cA')
        self.assertEqual('Ac', FileHelper.extendedAttributesOf(fn))
        FileHelper.changeExtendedAttributes(fn, toDelete='c')
        self.assertEqual('A', FileHelper.extendedAttributesOf(fn))


if __name__ == '__main__':
    sys.argv = ['', 'Test.testName']
    tester = FileHelperTest()
    tester.run()

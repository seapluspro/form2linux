'''
Created on 20.18.2023

@author: SeaPlusPro
'''
import unittest
import Form2Linux
import os.path
import base.MemoryLogger
import base.ProcessHelper
import base.StringUtils
import base.FileHelper

def inDebug(): return False

class Form2LinuxTest(unittest.TestCase):

    def testPackageBuild(self):
        if inDebug(): return
        logger = base.MemoryLogger.MemoryLogger(3)
        processHelper = base.ProcessHelper.ProcessHelper(logger)
        old = processHelper.pushd('package/test')
        archive = 'cppknife-0.6.3_amd64.deb'
        if os.path.exists(archive):
            os.unlink(archive)
        self.assertFalse(os.path.exists(archive))
        Form2Linux.main(['form2linux', '-v', 'package', 'build', 'package.json'])
        self.assertTrue(os.path.exists(archive))
        processHelper.popd(old)

    def testServiceInstall(self):
        if inDebug(): return
        logger = base.MemoryLogger.MemoryLogger(3)
        processHelper = base.ProcessHelper.ProcessHelper(logger)
        old = processHelper.pushd('service/test')
        Form2Linux.main(['form2linux', '-y', '-v', 'service', 'install', 'service.json'])
        processHelper.popd(old)
        serviceFile = '/tmp/examplesv.service'
        self.assertTrue(os.path.exists(serviceFile))
        contents = base.StringUtils.fromFile(serviceFile)
        self.assertEqual(contents, '''[Unit]
Description=A example service doing nothing.
After=syslog.target
[Service]
Type=simple
User=nobody
Group=nobody
WorkingDirectory=None
EnvironmentFile=-/etc/examplesv/examplesv.env
ExecStart=/usr/local/bin/examplesv daemon
ExecReload=/usr/local/bin/examplesv reload
SyslogIdentifier=examplesv
StandardOutput=syslog
StandardError=syslog
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
''')
    def testTextReplaceRangeString(self):
        if inDebug(): return
        fnDocument = base.FileHelper.tempFile('document.md', 'unittest')
        base.StringUtils.toFile(fnDocument, '''# Chapter1
~~abc!!
# Chapter2
~~def!!
# Chapter3
''')
        Form2Linux.main(['form2linux', '-v', 'text', 'replace-range', fnDocument, '--replacement=Dubidu', 
                         '--anchor=Chapter2', '--start=~~', '--end=!!'])
        replacement = base.StringUtils.fromFile(fnDocument)
        self.assertEqual(replacement, '''# Chapter1
~~abc!!
# Chapter2
~~Dubidu!!
# Chapter3
''')
    def testTextReplaceRangeFile(self):
        if inDebug(): return
        fnDocument = base.FileHelper.tempFile('document.md', 'unittest')
        fnData = base.FileHelper.tempFile('data.txt', 'unittest')
        base.StringUtils.toFile(fnData, '''Example:
one two three
''')
        base.StringUtils.toFile(fnDocument, '''# Chapter1
```
abc
```
# Chapter2
```
line 1
line 2
```
# Chapter3
''')
        Form2Linux.main(['form2linux', '-v', 'text', 'replace-range', fnDocument, f'--file={fnData}', '--anchor', 'Chapter2'])
        replacement = base.StringUtils.fromFile(fnDocument)
        self.assertEqual(replacement, '''# Chapter1
```
abc
```
# Chapter2
```
Example:
one two three
```
# Chapter3
''')


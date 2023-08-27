'''
Form2LinuxTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import os.path
import json
import unittest
import form2linux
import base.MemoryLogger
import base.ProcessHelper
import base.StringUtils
import base.FileHelper
from Builder import BuilderStatus

def inDebug(): return False

class form2linuxTest(unittest.TestCase):

    def testPackageBuild(self):
        if inDebug(): return
        logger = base.MemoryLogger.MemoryLogger(3)
        processHelper = base.ProcessHelper.ProcessHelper(logger)
        old = processHelper.pushd('package/test')
        archive = 'cppknife-0.6.3_amd64.deb'
        if os.path.exists(archive):
            os.unlink(archive)
        self.assertFalse(os.path.exists(archive))
        form2linux.main(['form2linux', '-v', 'package', 'build', 'package.json'])
        self.assertTrue(os.path.exists(archive))
        processHelper.popd(old)

    def testPackageExample(self):
        if inDebug(): return
        fnOutput = base.FileHelper.tempFile('package.example', 'unittest')
        form2linux.main(['form2linux', 'package', 'example', f'--file={fnOutput}'])
        lines = base.StringUtils.fromFile(fnOutput)
        json.loads(lines)
        self.assertTrue(lines.find('0.6.3') > 0)

    def testServiceExample(self):
        if inDebug(): return
        form2linux.main(['form2linux', 'service', 'example'])
        fnOutput = base.FileHelper.tempFile('service.example', 'unittest')
        form2linux.main(['form2linux', 'service', 'example', f'--file={fnOutput}'])
        lines = base.StringUtils.fromFile(fnOutput)
        json.loads(lines)
        self.assertTrue(lines.find('examplesv') > 0)

    def testServiceInstall(self):
        if inDebug(): return
        logger = base.MemoryLogger.MemoryLogger(3)
        processHelper = base.ProcessHelper.ProcessHelper(logger)
        old = processHelper.pushd('service/test')
        form2linux.main(['form2linux', '-y', '-v', 'service', 'install', 'service.json'])
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
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', fnDocument, '--replacement=Dubidu', 
                         '--anchor=Chapter2', '--start=~~', '--end=!!'])
        replacement = base.StringUtils.fromFile(fnDocument)
        self.assertEqual(replacement, '''# Chapter1
~~abc!!
# Chapter2
~~Dubidu!!
# Chapter3
''')

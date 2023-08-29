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
from base import MemoryLogger
from base import ProcessHelper
from base import StringUtils
from base import FileHelper
def inDebug(): return False

class form2linuxTest(unittest.TestCase):

    def testPackageBuild(self):
        if inDebug(): return
        logger = MemoryLogger.MemoryLogger(3)
        processHelper = ProcessHelper.ProcessHelper(logger)
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
        fnOutput = FileHelper.tempFile('package.example', 'unittest')
        form2linux.main(['form2linux', 'package', 'example', f'--file={fnOutput}'])
        lines = StringUtils.fromFile(fnOutput)
        json.loads(lines)
        self.assertTrue(lines.find('0.6.3') > 0)

    def testServiceExample(self):
        if inDebug(): return
        form2linux.main(['form2linux', 'service', 'example'])
        fnOutput = FileHelper.tempFile('service.example', 'unittest')
        form2linux.main(['form2linux', 'service', 'example', f'--file={fnOutput}'])
        lines = StringUtils.fromFile(fnOutput)
        json.loads(lines)
        self.assertTrue(lines.find('examplesv') > 0)

    def testServiceInstall(self):
        if inDebug(): return
        logger = MemoryLogger.MemoryLogger(3)
        processHelper = ProcessHelper.ProcessHelper(logger)
        old = processHelper.pushd('service/test')
        form2linux.main(['form2linux', '-y', '-v', 'service', 'install', 'service.json'])
        processHelper.popd(old)
        serviceFile = '/tmp/examplesv.service'
        self.assertTrue(os.path.exists(serviceFile))
        contents = StringUtils.fromFile(serviceFile)
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

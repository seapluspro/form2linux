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

class Form2LinuxTest(unittest.TestCase):

    def testPackageBuild(self):
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

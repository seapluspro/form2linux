''''
SetupBuilderTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import unittest
import form2linux
import json
import re
from base import StringUtils
from base import FileHelper
import Builder

def inDebug(): return False

class TextF2LTest(unittest.TestCase):

    def testTextReplaceRangeString(self):
        if inDebug(): return
        fnDocument = FileHelper.tempFile('document.md', 'unittest')
        StringUtils.toFile(fnDocument, '''# Chapter1
~~abc!!
# Chapter2
~~def!!
# Chapter3
''')
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', fnDocument, '--replacement=Dubidu', 
                         '--anchor=Chapter2', '--start=~~', '--end=!!'])
        result = StringUtils.fromFile(fnDocument)
        self.assertEqual(result, '''# Chapter1
~~abc!!
# Chapter2
~~Dubidu!!
# Chapter3
''')
    def testTextReplaceRangeFile(self):
        if inDebug(): return
        fnDocument = FileHelper.tempFile('document.md', 'unittest')
        StringUtils.toFile(fnDocument, '''# Chapter1
```
abc
```
# Chapter2
```
def
```
# Chapter3
''')
        fnReplacement = FileHelper.tempFile('replacement.txt', 'unittest')
        StringUtils.toFile(fnReplacement, 'Hello\nworld\n')
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', fnDocument, f'--file={fnReplacement}', 
                         '--anchor=Chapter2'])
        result = StringUtils.fromFile(fnDocument)
        self.assertEqual(result, '''# Chapter1
```
abc
```
# Chapter2
```
Hello
world
```
# Chapter3
''')

    def testTextReplaceRangeEndOfLine(self):
        if inDebug(): return
        fnDocument = FileHelper.tempFile('document.md', 'unittest')
        StringUtils.toFile(fnDocument, '''[SectionA]
minValue = 3
[SectionB]
''')
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', 
                         fnDocument, '--replacement=5', '--min-length=1', 
                         f'--start=minValue\s*=\s*', '--end=$',
                         ])
        result = StringUtils.fromFile(fnDocument)
        self.assertEqual(result, '''[SectionA]
minValue = 5
[SectionB]
''')
    def testTextReplaceRangeInsertionAnchor(self):
        #if inDebug(): return
        fnDocument = FileHelper.tempFile('document.md', 'unittest')
        StringUtils.toFile(fnDocument, '''[SectionA]
minValue = 3
[SectionB]
age = 32
''')
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', 
                         fnDocument, '--replacement=5', '--min-length=1', 
                         f'--start=maxValue\s*=\s*', '--end=$',
                         '--insertion-position=SectionB', '--insertion=maxValue=5'
                         ])
        result = StringUtils.fromFile(fnDocument)
        self.assertEqual(result, '''[SectionA]
minValue = 3
[SectionB]
maxValue=5
age = 32
''')
    def testTextReplaceRangeInsertionAtEnd(self):
        if inDebug(): return
        fnDocument = FileHelper.tempFile('document.md', 'unittest')
        StringUtils.toFile(fnDocument, '''[SectionA]
minValue = 3
[SectionB]
age = 32
''')
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', 
                         fnDocument, '--replacement=5', '--min-length=1', 
                         f'--start=maxValue\s*=\s*', '--end=$',
                         '--insertion-position=SectionC', '--insertion=maxValue=5'
                         ])
        result = StringUtils.fromFile(fnDocument)
        self.assertEqual(result, '''[SectionA]
minValue = 3
[SectionB]
age = 32
maxValue=5
''')
    def testTextReplaceRangeInsertionNoPosition(self):
        if inDebug(): return
        fnDocument = FileHelper.tempFile('document.md', 'unittest')
        StringUtils.toFile(fnDocument, '''[SectionA]
minValue = 3
[SectionB]
age = 32
''')
        form2linux.main(['form2linux', '-v', 'text', 'replace-range', 
                         fnDocument, '--replacement=5', '--min-length=1', 
                         f'--start=maxValue\s*=\s*', '--end=$',
                         '--insertion=maxValue=5'
                         ])
        result = StringUtils.fromFile(fnDocument)
        self.assertEqual(result, '''[SectionA]
minValue = 3
[SectionB]
age = 32
maxValue=5
''')

    def testExampleAdaptVariables(self):
        if inDebug(): return
        fnOutput = FileHelper.tempFile('adapt-variables.example', 'unittest')
        form2linux.main(['form2linux', 'text', 'example-adapt-variables', f'--file={fnOutput}'])
        lines = StringUtils.fromFile(fnOutput)
        json.loads(lines)
        self.assertTrue(lines.find('VARIABLE|VALUE') >= 0)

    def testAdaptVariables(self):
        #if inDebug(): return
        fnFpm = FileHelper.tempFile('fpm.ini', 'unittest')
        StringUtils.toFile(fnFpm, '''; any value
memory_limit = 128M
[Session]
session.save_handler = files
session.save_path = "/var/lib/php/sessions"
[opcache]
[Debug]
''')
        fnCli = FileHelper.tempFile('cli.ini', 'unittest')
        StringUtils.toFile(fnCli, '''; any value
memory_limit = 128M
[Debug]
''')
        fnForm = FileHelper.tempFile('adapt-variables.json', 'unittest')
        StringUtils.toFile(fnForm, r'''{
  "Variables": {
    "VERSION": "8.2"
  },
  "Comment": "Rules: 'VARIABLE|VALUE' or 'VARIABLE|VALUE|ANCHOR_IF_NOT_FOUND'",
  "Files": {
    "/tmp/unittest/fpm.ini": [
      "memory_limit|2048M",
      "session.save_handler|redis|^\\[Session\\]",
      "session.save_path|\"tcp://127.0.0.1:6379\"|^session.save_handler",
      "opcache.enable|1|^\\[opcache\\]"
    ],
    "/tmp/unittest/cli.ini": [
      "memory_limit|1024M",
      "upload_max_files|30"
    ]
  }
}
''')

        form2linux.main(['form2linux', '-v', 'text', 'adapt-variables', fnForm])
        logger = Builder.BuilderStatus.lastLogger()
        lines = re.sub(r'\.\d+', '.X', '\n'.join(logger.getMessages())) + '\n'
        self.assertEqual(lines, '''memory_limit: 128M -> 2048M
session.save_handler: files -> redis
session.save_path: "/var/lib/php/sessions" -> "tcp://127.X.X.X:6379"
added: opcache.enable=1
renaming /tmp/unittest/fpm.ini => /tmp/unittest/fpm.X
memory_limit: 128M -> 1024M
added: upload_max_files=30
renaming /tmp/unittest/cli.ini => /tmp/unittest/cli.X
''')
        current = StringUtils.fromFile(fnFpm)
        self.assertEqual(current, '''; any value
memory_limit = 2048M
[Session]
session.save_handler = redis
session.save_path = "tcp://127.0.0.1:6379"
[opcache]
opcache.enable=1
[Debug]
''')
        current = StringUtils.fromFile(fnCli)
        self.assertEqual(current, '''; any value
memory_limit = 1024M
[Debug]
upload_max_files=30''')

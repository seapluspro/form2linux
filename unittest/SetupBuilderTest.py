''''
SetupBuilderTest.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''
import unittest
import form2linux
import Builder
import base.StringUtils
import base.FileHelper

def inDebug(): return False

class SetupF2LTest(unittest.TestCase):

    def testAddStandardUser(self):
        if inDebug(): return
        fnForm = base.FileHelper.tempFile('stdusers.json', 'unittest')
        base.StringUtils.toFile(fnForm, '''{
  "Variables": {
    "SHELL": "/bin/bash",
    "NOLOGIN": "/usr/sbin/nologin"
  },
  "Users": {
    "bupsample": { "Uid": 230, "Gid": 230, "Home": "*", "Shell": "%(SHELL)", "Desc": "does not exist: colon"},
    "bupwrong": { "Uid": 33, "Gid": 201, "Home": "*", "Shell": "%(SHELL)", "Desc": "uid exists"},
    "bin": { "Uid": 2, "Gid": 1002, "Home": "*", "Shell": "%(SHELL)", "Desc": "already exists same uid"},
    "daemon": { "Uid": 444, "Gid": 444, "Home": "*", "Shell": "%(SHELL)", "Desc": "already exists other uid"}
  },
  "Groups": {
    "bupsample": 230,
    "daemon": 444,
    "bin": 2
  }
}
''')
        form2linux.main(['form2linux', '-v', 'setup', 'add-standard-users', fnForm])
        logger = Builder.BuilderStatus.lastLogger()
        lines = '\n'.join(logger.getMessages()) + '\n'
        self.assertEquals(lines, '''+++ user id 33 [bupwrong] already exists: www-data
# user bin already exists
+++ user daemon already exists with another uid: 444 / 1
+++ group daemon already exists with another uid: 444 / 1
# group bin already exists
sudo groupadd -g 230 bupsample
sudo useradd -m --no-user-group -g 230 -c "does not exist_ colon" -d /bin/bash -s /bin/bash bupsample
''')

    def testAdaptUsers(self):
        if inDebug(): return
        fnPasswd = base.FileHelper.tempFile('passwd', 'unittest')
        fnGroup = base.FileHelper.tempFile('group', 'unittest')
        fnShadow = base.FileHelper.tempFile('shadow', 'unittest')
        base.StringUtils.toFile(fnPasswd, '''root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
games:x:5:60:games:/usr/games:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
sftdragon:x:205:205:,,,:/home/sftdragon:/bin/false
hugo:x:1010:1013:Hugo Miller,,,:/home/hugo:/bin/bash
''')
        base.StringUtils.toFile(fnGroup, '''root:x:0:
daemon:x:1:
bin:x:2:
sys:x:3:
adm:x:4:
tty:x:5:
disk:x:6:
lp:x:7:
mail:x:8:
news:x:9:
sftdragon:x:205:bin,sys,adm
hugo:x:1010::hugo,root

''')
        base.StringUtils.toFile(fnShadow, '''root:$6$DasIstEinkomischesPasswort12345:18366:0:99999:7:::
daemon:*:18092:0:99999:7:::
bin:*:18092:0:99999:7:::
sys:*:18092:0:99999:7:::
sync:*:18092:0:99999:7:::
games:*:18092:0:99999:7:::
man:*:18092:0:99999:7:::
lp:*:18092:0:99999:7:::
hugo:$6$VerySecret:19550:0:99999:7:::
''')
        form2linux.main(['form2linux', '-v', 'setup', 'adapt-users', fnPasswd, fnGroup, fnShadow])
        logger = Builder.BuilderStatus.lastLogger()
        lines = '\n'.join(logger.getMessages()) + '\n'
        self.assertEquals(lines, '''# user root already exists
# user daemon already exists
# user bin already exists
# user games already exists
# user uucp already exists
# user proxy already exists
# user www-data already exists
# user backup already exists
# group root already exists
# group daemon already exists
# group bin already exists
# group sys already exists
# group adm already exists
# group tty already exists
# group disk already exists
# group lp already exists
# group mail already exists
# group news already exists
sudo groupadd -g 205 sftdragon
sudo groupadd --system -g 1010 hugo
sudo useradd -m --no-user-group -g 205 -c ",,," -d /home/sftdragon -s /bin/false sftdragon
sudo useradd --system -m --no-user-group -g 1010 -c "Hugo Miller,,," -d /home/hugo -s /bin/bash hugo
sudo form2linux setup patch-shadow hugo '$6$VerySecret'
sudo usermod -a -G sftdragon bin
sudo usermod -a -G sftdragon sys
sudo usermod -a -G sftdragon adm
''')

    def testPatchShadow(self):
        if inDebug(): return
        fnShadow = base.FileHelper.tempFile('shadow', 'unittest')
        base.StringUtils.toFile(fnShadow, '''root:$6$DasIstEinkomischesPasswort12345:18366:0:99999:7:::
daemon:*:18092:0:99999:7:::
bin:*:18092:0:99999:7:::
sys:*:18092:0:99999:7:::
sync:*:18092:0:99999:7:::
games:*:18092:0:99999:7:::
man:*:18092:0:99999:7:::
lp:*:18092:0:99999:7:::
hugo:$6$VerySecret:19550:0:99999:7:::
hugo2:$6$NoNoNo:19550:0:99999:7:::
''')
        form2linux.main(['form2linux', '-v', 'setup', 'patch-shadow', 'hugo', '$6$ChangedVAlue', f'--file={fnShadow}'])
        lines = base.StringUtils.fromFile(fnShadow)
        self.assertEquals(lines, '''root:$6$DasIstEinkomischesPasswort12345:18366:0:99999:7:::
daemon:*:18092:0:99999:7:::
bin:*:18092:0:99999:7:::
sys:*:18092:0:99999:7:::
sync:*:18092:0:99999:7:::
games:*:18092:0:99999:7:::
man:*:18092:0:99999:7:::
lp:*:18092:0:99999:7:::
hugo:$6$ChangedVAlue:19550:0:99999:7:::
hugo2:$6$NoNoNo:19550:0:99999:7:::
''')

    def testArchive(self):
        if inDebug(): return
        fnForm = base.FileHelper.tempFile('backup.json', 'unittest')
        fnArchive = base.FileHelper.tempFile('backup.tar.zst', 'unittest')
        base.StringUtils.toFile(fnForm, '''{
  "Variables": {
  "DUMMY": ""
  },
  "Command": "tar --zstd -cf ARCHIVE -C/ --files-from=%FILE%",
  "Files": {
      "/etc/": "auto.*,passwd,group",
      "/etc/default/": "grub",
      "/etc/network/": "interfaces",
      "/home/sysinfo/": "*",
      "/home/*/.ssh/": "authorized_keys,id_rsa,id_rsa.pub",
      "/home/*/.mozilla/firefox/*/": "places.sqlite,favicons.sqlite,key4.db,logins.json,search.json.mozlz4",
      "/home/*/.thunderbird/*/": "places.sqlite,favicons.sqlite,key4.db,logins.json,search.json.mozlz4",
      "/home/sysinfo/": "*"
  }
}
'''.replace('ARCHIVE', fnArchive))
        fnFiles = base.FileHelper.tempFile('files.out', 'unittest')
        form2linux.main(['form2linux', '-v', 'setup', 'archive', fnForm, f'--file={fnFiles}'])
        lines = base.StringUtils.fromFile(fnFiles)
        self.assertTrue(lines.find('etc/passwd\netc/group\netc/default/grub') >= 0)
        logger = Builder.BuilderStatus.lastLogger()
        lines = '\n'.join(logger.getMessages()) + '\n'
        self.assertTrue(lines.find(f'sudo tar --zstd -cf /tmp/unittest/backup.tar.zst -C/ --files-from={fnArchive}'))

    def testExampleArchive(self):
        if inDebug(): return
        fnOutput = base.FileHelper.tempFile('archive.example', 'unittest')
        form2linux.main(['form2linux', 'setup', 'example-archive', f'--file={fnOutput}'])
        lines = base.StringUtils.fromFile(fnOutput)
        self.assertTrue(lines.find('tar --zstd -cf') >= 0)

    def testExampleAddStandardUsers(self):
        if inDebug(): return
        fnOutput = base.FileHelper.tempFile('addstdusr.example', 'unittest')
        form2linux.main(['form2linux', 'setup', 'example-add-standard-users', f'--file={fnOutput}'])
        lines = base.StringUtils.fromFile(fnOutput)
        self.assertTrue(lines.find('bupsupply') >= 0)

    def testExampleSystemInfo(self):
        if inDebug(): return
        fnOutput = base.FileHelper.tempFile('sysinfo.example', 'unittest')
        form2linux.main(['form2linux', 'setup', 'example-system-info', f'--file={fnOutput}'])
        lines = base.StringUtils.fromFile(fnOutput)
        self.assertTrue(lines.find('STORAGE') >= 0)

    def testSystemInfo(self):
        #if inDebug(): return
        fnForm = base.FileHelper.tempFile('systeminfo.json', 'unittest')
        base.StringUtils.toFile(fnForm, '''{
  "Variables": {
    "STORAGE": "/tmp/unittest/sysinfo"
  },
  "Commands": {
    "# Command": "# stored in",
    "mkdir -p %(STORAGE)": "",
    "fdisk -l": "%(STORAGE)/fdisk.txt",
    "lsblk": "%(STORAGE)/lsblk.txt",
    "blkid": "%(STORAGE)/blkid.txt",
    "mount": "%(STORAGE)/mount.txt",
    "df -h": "%(STORAGE)/df.txt",
    "free": "%(STORAGE)/free.txt",
    "smartctl -a /dev/sda": "%(STORAGE)/smartctl.sda.txt",
    "ps aux": "%(STORAGE)/ps.txt",
    "systemctl list-units": "%(STORAGE)/systemctl.list-units.txt",
    "#cat /proc/mdstat": "%(STORAGE)/mdstat.txt"
  }
}
''')
        form2linux.main(['form2linux', 'setup', 'system-info', fnForm])
        logger = Builder.BuilderStatus.lastLogger()
        lines = '\n'.join(logger.getMessages()) + '\n'
        self.assertEqual(lines, '''sudo mkdir -p /tmp/unittest/sysinfo
sudo fdisk -l >/tmp/unittest/sysinfo/fdisk.txt
sudo lsblk >/tmp/unittest/sysinfo/lsblk.txt
sudo blkid >/tmp/unittest/sysinfo/blkid.txt
sudo mount >/tmp/unittest/sysinfo/mount.txt
sudo df -h >/tmp/unittest/sysinfo/df.txt
sudo free >/tmp/unittest/sysinfo/free.txt
sudo smartctl -a /dev/sda >/tmp/unittest/sysinfo/smartctl.sda.txt
sudo ps aux >/tmp/unittest/sysinfo/ps.txt
sudo systemctl list-units >/tmp/unittest/sysinfo/systemctl.list-units.txt
''')


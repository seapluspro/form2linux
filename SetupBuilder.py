'''
SetupBuilder.py

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
import text.jsonutils as jsonutils
import base.StringUtils
from Builder import Builder, CLIError


class UserData:
    '''Stores the user properties.
    '''

    def __init__(self, name, uid: int, gid: int, home: str, shell: str, desc: str):
        '''Constructor.
        @param name: the user name
        @param uid: the user id
        @param gid: the group id
        @param home: the home directory
        @param shell: the default shell
        @param desc: the description
        '''
        self._name = name
        self._uid = uid
        self._gid = gid
        self._home = home
        self._shell = shell
        self._desc = desc


class GroupData:
    '''Stores the user properties.
    '''

    def __init__(self, name: str, gid: int, members: str):
        '''Constructor.
        @param name: the group name
        @param gid: the group id
        @param members: a comma separated list of user names
        '''
        self._name = name
        self._gid = gid
        self._members = members


class SetupBuilder (Builder):
    '''Processes the "setup" command.
    '''

    def __init__(self, verbose: bool, dry: bool):
        '''Constructor.
        @param verbose: <em>True</em>: info messages will be displayed
        @param dry: <em>True</em>: says what to do, but do not change data
        '''
        Builder.__init__(self, verbose, dry)
        self._users = {}
        self._groups = {}
        self._activeUsers = pwd.getpwall()
        self._activeGroups = grp.getgrall()
        self._idPwSaved = {}
        self._namePwSaved = {}
        self._idGroupSaved = {}
        self._nameGroupSaved = {}
        self._shadowSaved = {}
        self._command = None

    def _byGroupId(self, gid: int):
        '''Get the group info given by the id.
        @param gid: the group id
        @return None or the group entry
        '''
        rc = None
        for ix in range(len(self._activeGroups)):
            if self._activeGroups[ix].gr_gid == gid:
                rc = self._activeGroups[ix]
                break
        return rc

    def _byGroupName(self, name):
        '''Get the system group info given by the name.
        @param name: the group name
        @return None or the group entry
        '''
        rc = None
        for ix in range(len(self._activeGroups)):
            if self._activeGroups[ix].gr_name == name:
                rc = self._activeGroups[ix]
                break
        return rc

    def _byUserId(self, uid: int):
        '''Get the system user info given by the id.
        @param uid: the user id
        @return None or the user entry
        '''
        rc = None
        for ix in range(len(self._activeUsers)):
            if self._activeUsers[ix].pw_uid == uid:
                rc = self._activeUsers[ix]
                break
        return rc

    def _byUserName(self, name):
        '''Get the system user info given by the name.
        @param name: the user name
        @return None or the user entry
        '''
        rc = None
        for ix in range(len(self._activeUsers)):
            if self._activeUsers[ix].pw_name == name:
                rc = self._activeUsers[ix]
                break
        return rc

    def exampleStandardUsers(self, filename: str):
        '''Shows the example for the configuration file of "add-standard-users".
        @param filename: None or the file to store
        '''
        message = '''{
  "Variables": {
    "SHELL": "/bin/bash",
    "NOLOGIN": "/usr/sbin/nologin"
  },
  "Users": {
    "bupsrv": { "Uid": 201, "Gid": 201, "Home": "*", "Shell": "%(SHELL)", "Desc": "receiver for external archive"},
    "bupsupply": { "Uid": 203, "Gid": 203, "Home": "*", "Shell": "%(SHELL)", "Desc": "receiver for external data"},
    "bupwiki": { "Uid": 205, "Gid": 205, "Home": "*", "Shell": "%(SHELL)", "Desc": "receiver for wiki data"},
    "extbup": { "Uid": 212, "Gid": 212, "Home": "*", "Shell": "%(SHELL)", "Desc": "sender for archive data"},
    "extcloud": { "Uid": 213, "Gid": 213, "Home": "*", "Shell": "%(SHELL)", "Desc": "sender for cloud data"},
    "extdata": { "Uid": 214, "Gid": 214, "Home": "*", "Shell": "%(SHELL)", "Desc": "sender for other data"}
  },
  "Groups": {
    "bupsrv": 201,
    "bupsupply": 203,
    "bupwiki": 205,
    "extbup": 212,
    "extcloud": 213,
    "extdata": 214
  }
}
'''
        if filename is None:
            self.log(message)
        else:
            base.StringUtils.toFile(filename, message)

    def adaptUsers(self, passwd: str, group: str, shadow: str):
        '''Compares two passwd/group files:
        If the 2nd file contains a member not known in the system user/group file 
        that member will be inserted with "useradd" or "groupadd"
        @param passwd: the name of the 2nd password file
        @param group: the name of the 2nd group file
        @param shadow: the name of the 2nd shadow password file
        '''
        self.checkAdaptUsers(passwd, group, shadow)
        for group in self._groups:
            entry = self._groups[group]
            gid = int(entry._gid)
            system = '' if gid < 1000 else '--system '
            self.runProgram(f'groupadd {system}-g {gid} {group}', True)
        for user in self._users:
            entry = self._users[user]
            system = '' if int(entry._uid) < 1000 else '--system '
            self.runProgram(
                f'useradd {system}-m --no-user-group -g {entry._gid} -c "{entry._desc}" -d {entry._home} -s {entry._shell} {user}', True)
            passwd = '' if user not in self._shadowSaved else self._shadowSaved[user]
            if len(passwd) > 5:
                if os.geteuid() == 0:
                    self.patchShadow(user, passwd)
                else:
                    self.log(
                        f"sudo form2linux setup patch-shadow {user} '{passwd}'")
        for group in self._groups:
            entry = self._groups[group]
            gid = entry._gid
            members = entry._members
            for member in members.split(','):
                if member != '':
                    self.runProgram(f'usermod -a -G {group} {member}', True)

    def addStandardUsers(self, form):
        '''Compares the form entries with the system user/group files.
        If the form contains a member not known in the system user/group file 
        that member will be inserted with "useradd" or "groupadd"
        @param form: the name of the form with Json format
        '''
        self.checkStandardUsers(form)
        for group in self._groups:
            gid = self._groups[group]
            system = '' if gid < 1000 else '--system '
            self.runProgram(f'groupadd {system}-g {gid} {group}', True)
        for user in self._users:
            entry = self._users[user]
            system = '' if entry._uid < 1000 else '--system '
            self.runProgram(
                f'useradd {system}-m --no-user-group -g {entry._gid} -c "{entry._desc}" -d {entry._home} -s {entry._shell} {user}', True)

    def archive(self, form: str, filesList: str):
        '''Stores files into a archive using a user defined command.
        @param form: the name of the form with Json format
        @param filesList: the name of the file storing the full filenames to archive
        '''
        if filesList == '*':
            filesList = f'/tmp/f2l.files.{int(time.time())%86400}.lst'
        self.checkArchive(form)
        with open(filesList, 'w') as fp:
            for file in self._files:
                # write without preceding '/'
                fp.write(f'{file[1:]}\n')
        command = self._command.replace('%FILE%', filesList)
        self.runProgram(command, True, True)

    def checkAdaptUsers(self, passwd: str, group: str, shadow: str):
        '''Checks the input data for the method adaptUsers() and stores the data that must be inserted.
        @param passwd: the name of the 2nd password file
        @param group: the name of the 2nd group file
        @param shadow: the name of the 2nd shadow password file
        '''
        with open(passwd, 'r') as fp:
            for line in fp:
                line = line.strip()
                # 0................1.2...3...4.......5............6
                # systemd-timesync:x:101:101:systemd:/run/systemd:/usr/sbin/nologin
                parts = line.split(':')
                # ...............name, uid, gid, home, shell, desc
                entry = UserData(parts[0], parts[2], parts[3],
                                 parts[5], parts[6], parts[4])
                self._idPwSaved[int(parts[2])] = entry
                self._namePwSaved[parts[0]] = entry
        with open(group, 'r') as fp:
            for line in fp:
                line = line.strip()
                # 0.....1.2..3
                # video:x:44:seacocmd,seapluspro
                parts = line.split(':')
                if len(parts) >= 4:
                    members = parts[3]
                    # ...............name, gid, members
                    entry = GroupData(parts[0], parts[2], members)
                    self._idGroupSaved[int(parts[2])] = entry
                    self._nameGroupSaved[parts[0]] = entry
        with open(shadow, 'r') as fp:
            for line in fp:
                # 0.....1.2.....3
                # statd:*:19255:0:99999:7:::
                parts = line.split(':')
                self._shadowSaved[parts[0]] = parts[1]
        for user in self._namePwSaved:
            entry = self._namePwSaved[user]
            uid = entry._uid
            entry2 = self._byUserName(user)
            entry3 = self._byUserId(uid)
            if entry3 is not None and entry3.pw_name != user:
                self.error(
                    f'user id {uid} [{user}] already exists: {entry3.pw_name}')
            elif entry2 is None:
                self._users[user] = entry
            else:
                uidActive = entry2.pw_uid
                if int(uidActive) != int(uid):
                    self.error(
                        f'user {user} already exists with another uid: {uid} / {uidActive}')
                else:
                    self.info(f'# user {user} already exists')
        for group in self._nameGroupSaved:
            entry = self._nameGroupSaved[group]
            gid = entry._gid
            entry2 = self._byGroupId(gid)
            entry3 = self._byGroupName(group)
            if entry2 is not None and entry2.gr_name != group:
                self.error(
                    f'group id {gid} [{group}] already exists: {entry2.gr_name}')
            elif entry3 is None:
                self._groups[group] = entry
            else:
                gidActive = entry3.gr_gid
                if int(gidActive) != int(gid):
                    self.error(
                        f'group {group} already exists with another uid: {gid} / {gidActive}')
                else:
                    self.info(f'# group {group} already exists')

    def checkArchive(self, form: str):
        '''Checks the data for the method addStandardUsers and store the data that must be inserted.
        @param form: the name of the form with Json format
        '''
        self._files = []
        with open(form, 'r') as fp:
            data = fp.read()
            self._root = root = json.loads(data)
            path = 'Files:m Command:s Variables:m'
            jsonutils.checkJsonMapAndRaise(root, path, True)
            variables = root['Variables']
            self._command = self.valueOf('Command')
            if self._command.find('%FILE%') < 0:
                raise CLIError(f'missing %FILE% in Command: {self._command}')
            for name in variables:
                self.setVariable(name, variables[name])
            self.finishVariables()
            files = root['Files']
            for path in files:
                path2 = self.replaceVariables(path)
                if not path2.startswith('/'):
                    self.error(f'path is not absolute: {path}')
                fileList = self.valueOf(f'Files {path2}')
                base.FileHelper.expandWildcards(path2, fileList, self._files)

    def checkStandardUsers(self, form):
        '''Compares the form entries with the system user/group files.
        If the form contains a member not known in the system user/group file 
        that member will be inserted with "useradd" or "groupadd"
        @param form: the name of the form with Json format
        '''
        with open(form, 'r') as fp:
            data = fp.read()
            self._root = root = json.loads(data)
            path = 'Users:m Groups:m Variables:m'
            jsonutils.checkJsonMapAndRaise(root, path, True)
            variables = root['Variables']
            for name in variables:
                self.setVariable(name, variables[name])
            self.finishVariables()
            users = root['Users']
            for user in users:
                path = 'Uid:i Gid:i Home:s Shell:s Desc:s'
                entry = users[user]
                jsonutils.checkJsonMapAndRaise(entry, path, True)
                if not re.match(r'^[a-z][\w-]*$', user):
                    raise CLIError(f'wrong username: {user}')
                shell = self.valueOf(f'Users {user} Shell')
                if not os.path.exists(shell):
                    raise CLIError(f'missing shell: {shell}')
                uid = self.valueOf(f'Users {user} Uid', 'i')
                gid = self.valueOf(f'Users {user} Gid', 'i')
                home = self.valueOf(f'Users {user} Shell')
                if home == '*':
                    home = f'/home/{user}'
                desc = self.valueOf(f'Users {user} Desc')
                desc = re.sub(r'[^\w -]+', '_', desc)
                entry2 = self._byUserName(user)
                entry3 = self._byUserId(uid)
                if entry3 is not None and entry3.pw_name != user:
                    self.error(
                        f'user id {uid} [{user}] already exists: {entry3.pw_name}')
                elif entry2 is None:
                    self._users[user] = UserData(
                        user, uid, gid, home, shell, desc)
                else:
                    uidActive = entry2.pw_uid
                    if uidActive != uid:
                        self.error(
                            f'user {user} already exists with another uid: {uid} / {uidActive}')
                    else:
                        self.info(f'# user {user} already exists')
            groups = root['Groups']
            for group in groups:
                if not re.match(r'^[a-z][\w-]*$', group):
                    raise CLIError(f'wrong group name: {group}')
                gid = self.valueOf(f'Groups {group}', 'i')
                entry2 = self._byGroupId(gid)
                entry3 = self._byGroupName(group)
                if entry2 is not None and entry2.gr_name != group:
                    self.error(
                        f'group id {gid} [{group}] already exists: {entry2.gr_name}')
                elif entry3 is None:
                    self._groups[group] = gid
                else:
                    gidActive = entry3.gr_gid
                    if gidActive != gid:
                        self.error(
                            f'group {group} already exists with another uid: {gid} / {gidActive}')
                    else:
                        self.info(f'# group {group} already exists')

    def exampleArchive(self, filename: str):
        '''Shows the example for the configuration of the archive command.
        @param filename: None or the file to store
        '''
        message = '''{
  "Variables": {
    "Comment": "At least one entry is needed."
  },
  "Command": "tar --zstd -cf /opt/archive/daily.tar.zst -C/ --files-from=%FILE%",
  "Files": {
      "/etc/": "passwd,group,shadow,fstab,hosts,auto.*,exports,sudoers",
      "/etc/default/": "grub",
      "/home/sysinfo/": "*",
      "/home/*/.ssh/": "authorized_keys,id_rsa,id_rsa.pub",
      "/home/*/.mozilla/firefox/*/": "places.sqlite,favicons.sqlite,key4.db,logins.json,search.json.mozlz4",
      "/home/*/.thunderbird/*/": "places.sqlite,favicons.sqlite,key4.db,logins.json,search.json.mozlz4",
      "/home/sysinfo/": "*"
  }
}
'''
        if filename is None:
            self.log(message)
        else:
            base.StringUtils.toFile(filename, message)

    def patchShadow(self, user: str, passwd: str, shadow: str):
        '''Replaces in the shadow file a encoded password with a given value.
        @param user: the password of that user will be changed
        @param passwd: the new value of the encoded password
        @param shadow: the name of the shadow file
        '''
        with open(shadow, 'r') as fp:
            lines = []
            found = False
            changed = False
            for line in fp:
                parts = line.split(':')
                if parts[0] == user:
                    changed = parts[1] != passwd
                    parts[1] = passwd
                    line = ':'.join(parts)
                    found = True
                lines.append(line)
        if found:
            self.info("# user found")
            if changed:
                if self._dry:
                    self.log(f'# dry mode: not written {shadow}')
                else:
                    with open(shadow, 'w') as fp:
                        fp.write(''.join(lines))
                        self.info('# written: {shadow}')

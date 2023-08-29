## The Task "Setup"

The task "Setup" contains tools to setup a new system and backup/restore:

- adapt-users: creates users and groups from safed versions of passwd and group
- add-standard-users: creates users and groups from a Json form
- example-add-standard-users: shows a form for the "add-standard-users" command
- archive: stores files into a archive
- example-archive: shows the form of the command "archive"
- patch-shadow: puts an encoded password into the shadow password file
- system-info: collects the state of the current system
- example-system-info: shows the configuration of "system-info"

### Examples
```
form2linux setup --help
form2linux setup adapt-users /backup/passwd /backup/group /backup/shadow

form2linux setup example-add-standard-users myform.json
form2linux setup add-standard-users myform.json

form2linux setup example-archive myform.json
form2linux setup archive myform.json

form2linux setup example-system-info myform.json
form2linux setup system-info myform.json
```

### Usage
```
usage: form2linux.py service [-h] {example,check,install} ...

positional arguments:
  {example,check,install}
                        service help
    example             shows an example configuration file. Can be used as
                        template for a new service.
    check               checks the configuration file
    install             Installs a systemd service defined by a Json
                        configuration file.

options:
  -h, --help            show this help message and exit
```
#### Variables
In all forms may be a section "Variables". You can define strings occurring more than one time in the form.

Each variable is defined by a name and the value:

Example: The variable SHELL should have the value "/bin/bash":
```
"SHELL": "/bin/bash"
```
The variable can be used at any position of the form (including in other variables) 
with the syntax %&lt;<name>), for example %(SERVICE).


### The Form add-standard-users
<code>form2linux setup example-add-standard-users</code> shows the following:
```
{
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
```

#### Users

Each standard user will be defined with that attributes:
- Uid: the user id
- Gid: the standard group
- Home: the home directory
- Shell: the login shell
- Desc: a description

#### Groups

Each standard group will be defined with that attributes:
- Gid: the standard group

### The Form archive
<code>form2linux setup example-archive</code> shows the following:
```
{
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
```
#### Command
Defines the command to create the archive. Must contain the keyword %FILE%.
That keyword is replaced by a file created from the application.

Works only with archive programs that can read the files from a file: tar, zip

#### Files
Defines the files to store in the archive.

The key is the path. The path may contain wildcards (like a shell).

The value is a list of node names, delimited by ','. Each node name may contain wildcards.

### The Form system-info
<code>form2linux setup example-system-info</code> shows the following:
```
{
  "Variables": {
    "STORAGE": "/home/sysinfo"
  },
  "Commands": {
    "# Command": "# stored in",
    "fdisk -l": "%(STORAGE)/fdisk.txt",
    "lsblk": "%(STORAGE)/lsblk.txt",
    "blkid": "%(STORAGE)/blkid.txt",
    "mount": "%(STORAGE)/mount.txt",
    "df -h": "%(STORAGE)/df.txt",
    "free": "%(STORAGE)/free.txt",
    "smartctl -a /dev/nvme0n1": "%(STORAGE)/smartctl.nvme0n1.txt",
    "smartctl -a /dev/sda": "%(STORAGE)/smartctl.sda.txt",
    "ps aux": "%(STORAGE)/ps.txt",
    "systemctl list-units": "%(STORAGE)/systemctl.list-units.txt",
    "#cat /proc/mdstat": "%(STORAGE)/mdstat.txt"
  }
}
```
#### Commands
Here are the commands that produce the info.

The key is the command.

The value is the file storing the info.

### The Command patch-shadow
The command <code>form2linux setup patch-shadow user password</code>
puts the encrypted password to the user in the file /etc/shadow.

So passwords can be transfered from other systems (or backup).

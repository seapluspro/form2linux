# Form2Task
Execute a Linux task specified by a form in Json format.

The following tasks are available:

- Installs and configures packages
- Builds a debian package
- Installs a SystemD service
- Setup, backup or restore a new linux system
- Some text manipulations

## Debian Package
There are Debian packages for each version of the project.
See debian/packages.

### Download
```
wget -O version.txt https://github.com/seapluspro/form2linux/blob/main/debian/packages/version.txt?raw=true
VERSION=$(cat version.txt)
wget -O form2linux-${VERSION}_all.deb https://github.com/seapluspro/form2linux/blob/main/debian/packages/form2linux-${VERSION}_all.deb?raw=true
```

## Links
- [Dokumentation "install"](doc/install.md)
- [Dokumentation "package"](doc/package.md)
- [Dokumentation "service"](doc/service.md)
- [Dokumentation "setup"](doc/setup.md)
- [Dokumentation "text"](doc/text.md)


## Usage
The Python script form2task is a command line tool with the following options:


## form2task -h
The call <code>form2linux -h</code> show the following:

```
usage: form2linux.py [-h] [-v] [-V] [-y] [-n] [-R]
                     {install,package,service,setup,text} ...

form2linux -- shortdesc

  Created by SeePlusPro on 2023-08-20.
  Copyright 2023 SeePlusPro. All rights reserved.

  Licensed under the CC0 1.0 Universal
  https://creativecommons.org/publicdomain/zero/1.0/deed.en

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

Examples:

form2linux install example-standard-host myform.json
form2linux install standard-host myform.json

form2linux package example
form2linux package example package.json
form2linux package build package.json

form2linux service example
form2linux service example service.json
form2linux service install service.json

form2linux setup example-add-standrd-users myform.json
form2linux setup add-standrd-users myform.json

form2linux text replace-range readme.md --replacement=0.4.2   --anchor=Download --start=myfile. --end=.txt

positional arguments:
  {install,package,service,setup,text}
                        sub-command help
    install             installs and configures packages.
    package             Builds a debian package from a package description in
                        Json format.
    service             Installs a SystemD service.
    setup               archive and restore, setup of a new system.
    text                Some text manipulation.

options:
  -h, --help            show this help message and exit
  -v, --verbose         set verbosity level [default: None]
  -V, --version         show program's version number and exit
  -y, --dry             do not create files and directories
  -n, --not-root        commmand must not be executed as root
  -R, --root            commmand must be executed as root
```

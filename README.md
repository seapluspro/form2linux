# Form2Task
Execute a Linux task specified by a form in Json format.

The following tasks are available:

- Build a debian package
- Install a SystemD service

## Debian Package
There are Debian packages for each version of the project.
See debian/packages.

## Links
- [Dokumentation "package"](doc/package.md)
- [Dokumentation "service"](doc/service.md)
- [Dokumentation "text"](doc/text.md)


## Usage
The Python script form2task is a command line tool with the following options:


## form2task -h
```
usage: Form2Linux.py [-h] [-v] [-V] [-y] {package,service,text} ...

form2linux -- shortdesc

  Created by SeePlusPro on 2023-08-20.
  Copyright 2023 SeePlusPro. All rights reserved.

  Licensed under the CC0 1.0 Universal
  https://creativecommons.org/publicdomain/zero/1.0/deed.en

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

Examples:

form2linux --help

form2linux package example
form2linux package example package.json
form2linux package build package.json

form2linux service example
form2linux service example service.json
form2linux service install service.json

positional arguments:
  {package,service,text}
                        sub-command help
    package             Builds a debian package from a package description in
                        Json format.
    service             Installs a SystemD service.
    text                Some text manipulation.

options:
  -h, --help            show this help message and exit
  -v, --verbose         set verbosity level [default: None]
  -V, --version         show program's version number and exit
  -y, --dry             do not create files and directories
```

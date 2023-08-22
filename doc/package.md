## The Task "Package"

The task "package" builds a debian package archive (*.deb) from its components.

The components must be defined in a Json form.

### Usage
```
usage: form2linux.py package [-h] {example,check,build} ...

positional arguments:
  {example,check,build}
                        package help
    example             shows an example configuration file. Can be used for
                        initializing a new package project.
    check               checks the configuration file
    build               builds the debian package

options:
  -h, --help            show this help message and exit
```

### Examples
The command task2linux service example shows the following:
```
form2linux package -h

form2linux package example >package.json
# Modify the file package.json with your requests
form2linux package check package.json
form2linux package build package.json
```

### The Form
The call <code>form2linux package example</code> shows:
```
{
  "Variables": {
     "VERSION": "0.6.3",
     "BASE": "usr/share/cppknife-%(VERSION)"
  },
  "Project": {
    "Package": "cppknife",
    "Version": "%(VERSION)",
    "Architecture": "amd64",
    "Maintainer": "SeaPlusPro <seapluspro@gmail.com>",
    "Replaces": "",
    "Depends": {
      "libc6": ">= 2.36",
      "libgdal-dev": ""
      },
    "Provides": "*",
    "Suggests": [
      "cppknife-db"
      ],
    "Homepage": "https://github.com/seapluspro/cppknife",
    "Description": "Shared libraries for C++ programming and tools using that.",
    "Notes": [
      "The heart is the shared library libcppknife as a helper for fast programming a command line C++ program.",
      "Also there are the programs textknife, fileknife, geoknife, sesknife, osknife which demonstrate the usage of the library."
    ]
  },
  "Directories": [
    "%(BASE)"
    ],
  "Files": {
    "../build.release/libcppknife-%(VERSION).so": "%(BASE)/",
    "../build.release/libcppknifegeo-%(VERSION).so": "%(BASE)/",
    "../build.release/fileknife": "%(BASE)/",
    "../build.release/textknife": "%(BASE)/",
    "../build.release/sesknife": "%(BASE)/",
    "../basic/*.hpp": "%(BASE)/basic/",
    "../db/*.hpp": "%(BASE)/db/",
    "../core/*.hpp": "%(BASE)/core/",
    "../net/*.hpp": "%(BASE)/net/",
    "../geo/*.hpp": "%(BASE)/geo/",
    "../text/*.hpp": "%(BASE)/text/",
    "../tools/*.hpp": "%(BASE)/tools/"
  },
  "Links": {
    "%(BASE)/libcppknife-%(VERSION).so": "usr/lib/",
    "%(BASE)/libcppknifegeo-%(VERSION).so": "usr/lib/",
    "%(BASE)/fileknife": "usr/local/bin/",
    "%(BASE)/textknife": "usr/local/bin/",
    "%(BASE)/sesknife": "usr/local/bin/"
  },
  "PostInstall": "postinst2",
  "PostRemove": ""
}

```

### Description:

#### Variables
In that section you can define Strings occurring more than one time in the form.

Each variable is defined by a name and the value:

Example: The variable VERSION should have the value "0.6.3"
```
"VERSION": "0.6.3"
```

The variable can be used at any position of the form (including in other variables) 
with the syntax %&lt;<name>), for example %(VERSION).

#### Project Version
The version is a semantic version with 3 numbers, e.g. "0.2.4".

#### Project Depends
That is a list of dependencies.

Each dependency is defined by the debian package name and a version rule.

The version rule may be:
- empty ("")
- a exact version number: "0.2.4"
- a condition: ">= 1.0.0"

#### Project Provides
This is a package name which can be used for (exclusive) alternative packages.

If "*" the package name is used.

#### Project Suggests
That is a list of suggested package names. May be empty.

If "*" the package name is used.

#### Project Description
That is short descrition of the package: specifie only one line.

#### Project Notes
That is a list of additional lines for the description.

### Directories
That is a list of directories to create while installation.

#### Files
That is a list of files to create while installation.

Each file is specified by a source file (or a pattern with the wildcards '*' and '?')
and a destination definition, for example: <code>"/home/ws/data/config.txt": "etc/myapp/"</code>

The destination path is relative to root ("/"): Do not start it with "/".

If the destination ends with '/' the destination is interpreted as path and
the name of the destination is the same name as the source.

#### Links
That is a list of symbolic links to create while installation.

Each link is a pair of source (the link target) and the destination (the symbolic link itself).

Example:
```
"usr/share/myapp/doit.sh": "usr/local/bin/"
```
Than a symbolic link "/usr/local/bin/doit.sh" is created which points to "usr/share/myapp/doit.sh"

The installation automatically create relative links. In this case: '../../share/myapp/doit.sh"

The source and the destination is relative to root. Do not start it with "/".


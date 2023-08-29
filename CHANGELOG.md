# Changelog

# [0.5.2] - 2023-08-27 documentation completed

# [0.5.1] - 2023-08-27 adapt-variables php

## Added
- mode text: example-adapt-variable, adapt-variables
- mode install: example-php, php
- TextProcessor: adaptVariables(), insertByAnchor()
- some commands stores the forms in /var/lib/form2linux/forms
- text replace-range: --insert-position --insert


## Changed
- debian package: postinst2
- documentation completed
- text replace-range: default value of --min-length set to 1 (from 3)



# [0.4.1] - 2023-08-27

## Added
- mode install with standard-host and example-standard-host
- new global options --root and --not-root
- Builder: 
    - GlobalLogger
    - checkPattern(), checkNodePattern()
    - ensureDirectory(), needsRoot(), canWrite()
    - saveFile(), writeFile()

## Changed
- constructor of Builder: parameter options
- using Builder._example() for example*()

## Fixed
- SetupBuilder::exampleSystemInfo(): missing "

# [0.3.1] - 2023-08-25

## Added
- mode setup: system-info, example-system-info
- all forms: optional field "Comment" in all maps
- Builder::runProgram(): new parameter outputFile
 
## Changed
- Refactoring: pylint warnings reduced (all modules)
 
 # [0.2.1] - 2023-08-24

## Added
- new mode setup
    - adapt-users, add-standard-users, example-add-standard-users
    - patch-shadow, archive, example-archive
- mode package + service: subcommand "example" known now option --file
- FileHelper: expandFiles(), expandWildcards()

# [0.1.4] - 2023-08-22

## Added
- Debian packages

# [0.1.3] - 2023-08-22

## Changed
- Refactoring Form2Linux.py splitted into Builder.py, PackageBuilder.py ServiceBuilder.py TextTool.py and form2linux.py

## Fixed
- Builder::handleFiles(): wrong target file node on copied files
- PackageBuilder::buildPostInstall(): wrong link file nodes
- missing "exit 0" in scripts

# [0.1.2] - 2023-08-21

## Added
- package: scripts/form2linux
- package: attribute "PostInstall"
- package: attribute "PostRemove"
- package: creating DEBIAN/postrm
- new section: text with sub command replace-range
- documentation: automatic replacement in examples and usage messages
- releases/form2linux-VERSION.deb

## Changed
- tolerance for preceding "/" in "Files


# Changelog

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


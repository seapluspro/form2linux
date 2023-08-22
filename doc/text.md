## The Task "Text"

The task "Text" offers text manipulation.

### Usage
```
usage: form2linux.py text [-h] {replace-range} ...

positional arguments:
  {replace-range}  text help
    replace-range  replaces a section in text document with a string or a
                   file.

options:
  -h, --help       show this help message and exit
```

### Examples
```
form2linux text --help
VERSION=1.1.0
OUTPUT=/tmp/data
form2linux -v text replace-range package.json --replacement=$VERSION --anchor=Variables '--start=VERSION":."' '--end="'
form2linux service example >$OUTPUT
form2linux -v text replace-range ../doc/service.doc --file=$OUTPUT "--anchor=^###.The.Form"#
```


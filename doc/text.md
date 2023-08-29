## The Task "Text"

The task "Text" offers text manipulation.

### Usage
```
usage: form2linux.py text [-h]
                          {adapt-variables,example-adapt-variables,replace-range}
                          ...

positional arguments:
  {adapt-variables,example-adapt-variables,replace-range}
                        text help
    adapt-variables     replaces variables in a configuration file if needed.
    example-adapt-variables
                        shows an example form for the command "adapt-
                        variables".
    replace-range       replaces a section in text document with a string or a
                        file.

options:
  -h, --help            show this help message and exit
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


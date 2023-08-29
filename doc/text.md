## The Task "Text"

The task "Text" offers text manipulation.

### Usage
The call <code>form2linux text -h</code> show the following:

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
form2linux -v text replace-range ../doc/service.doc --file=$OUTPUT "--anchor=^###.The.Form"

form2linux -v text example-adapt-variables myform.json
form2linux -v text adapt-variables myform.json
```

### Sub command adapt-variables
Use that command to adapt variables in a configuratin file.
The file must have the following format:
* There are variable definitions like: VARIABLE = VALUE
* One variable definition in one line

You must create a form (use  <code>example-form2linux newform.json</code>).

Than edit the form with your requests.

<code>example-form2linux newform.json</code> modifies the configuration file.

#### The Form

The call <code>form2linux text example-adapt-variables show the following:
This is a meaningful example to modify the PHP configuration: two configuration files for FPM and CLI.
```
{
  "Variables": {
    "VERSION": "8.2"
  },
  "Comment": "Rules: 'VARIABLE|VALUE' or 'VARIABLE|VALUE|ANCHOR_IF_NOT_FOUND'",
  "Files": {
    "/etc/php/%(VERSION)/fpm/php.ini": [
      "memory_limit|2048M",
      "upload_max_filesize|512M",
      "max_file_uploads|100",
      "post_max_size|512M",
      "max_execution_time|600",
      "max_input_time|600",
      "default_socket_timeout|600",
      "session.save_handler|redis|^\\[Session\\]",
      "session.save_path|\"tcp://127.0.0.1:6379\"|^session.save_handler",
      "opcache.enable|1|^\\[opcache\\]",
      "opcache.memory_consumption|1024|opcache.enable",
      "opcache.interned_strings_buffer|512|^opcache.memory_consumption"
    ],
    "/etc/php/%(VERSION)/cli/php.ini": [
      "memory_limit|2048M",
      "upload_max_filesize|512M",
      "max_file_uploads|100",
      "post_max_size|512M",
      "max_execution_time|600",
      "max_input_time|600",
      "default_socket_timeout|600"
    ]
  }
}
```

#### Decription
- "Files": that is a list of associations: the filename of the configuration file is assigned to a list of rules.
- Each rule has two or three parts, delimited by '|':
    - the variable name
    - the variable value
    - the anchor if the variable does not exist (optional)
Each specified variable is searched in the file.
If it is found and the value is not the specified than the value is replaced by the specified.
If it is not found and an anchor is given the anchor is searched. 
If found the assignment "VARIABLE = VALUE" is inserted behind the anchor. 
If there is no anchor or the anchor can not be found the assignment is put at the end of the file

### Sub command replace-range
With that command you can replace a piece of text in a file by another text.
The region to replace is specified by two regular expressions: the text on top of the region and the text below the region
You can use an anchor: This is a specified text (regular expression) in a line above the region.

Example:

```
= Users:
Name: Anna,
= Admins:
Name: Anna,
```
If the anchor "Admins" is chosen and the region is defined by the start "Name: " end the end "$" (end of line), 
than the 4th line will be changed and not the 2nd. 

The call <code>form2linux text replace-range -h</code> show the following:

```
usage: form2linux.py text replace-range [-h] [-f FILE] [-r REPLACEMENT]
                                        [-s START] [-e END]
                                        [-p INSERTIONPOSITION] [-i INSERTION]
                                        [-a ANCHOR] [-m MINLENGTH] [-n]
                                        document

positional arguments:
  document              the document to change.

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  the file contents is the replacement. Exclusive
                        alternative: --replacement
  -r REPLACEMENT, --replacement REPLACEMENT
                        defines the replacement as string. Exclusive
                        alternative: --file
  -s START, --start START
                        a regular expression starting the range to change.
  -e END, --end END     a regular expression ending the range to change.
  -p INSERTIONPOSITION, --insertion-position INSERTIONPOSITION
                        a regular expression of the position where the
                        insertion should be done.
  -i INSERTION, --insertion INSERTION
                        this string will be inserted if the --start is not
                        found
  -a ANCHOR, --anchor ANCHOR
                        a regular expression defining the position of the text
                        change. Than the next range is replaced by the
                        program's output.
  -m MINLENGTH, --min-length MINLENGTH
                        the replacement or replacement file must have at least
                        that length
  -n, --newline         add a newline at the --replacement string
```


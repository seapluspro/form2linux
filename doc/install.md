## The Task "Install"

The task "Install" installs some packages.

The components must be defined in a Json form.

### Usage

The call <code>form2linux install -h</code> show the following:

```
usage: form2linux.py install [-h]
                             {php,example-php,standard-host,example-standard-host}
                             ...

positional arguments:
  {php,example-php,standard-host,example-standard-host}
                        install help
    php                 installs and configures the PHP packages
    example-php         shows an example configuration of the command "php"
    standard-host       prepares a standard linux host
    example-standard-host
                        shows an example configuration of the command
                        "standard-host"

options:
  -h, --help            show this help message and exit
```

### Examples
```
form2linux install --help
form2linux install example-standard-host myform.json
form2linux install standard-host myform.json

form2linux install example-php myform.json
form2linux install php myform.json

```
{
  "Variables": {
    "VERSION": "8.2"
  },
  "ConfigurationDirectory": "/etc/php/%(VERSION)",
  "Repository": { 
      "File": "/etc/apt/sources.list.d/php.list", 
      "Contents": "deb https://packages.sury.org/php/ bookworm main",
      "Initialization": [
        "sudo rm -f /tmp/php.gpg",
        "wget -qO /tmp/php.gpg https://packages.sury.org/php/apt.gpg",
        "sudo cp -a /tmp/php.gpg /etc/apt/trusted.gpg.d/php.gpg"
      ]
   },
  "Comment": "php8.2-xdebug php8.2-pgsql",
  "Packages": [
      "php%(VERSION) php%(VERSION)-curl php%(VERSION)-gd php%(VERSION)-igbinary",
      "php%(VERSION)-imagick php%(VERSION)-intl php%(VERSION)-mbstring",
      "php%(VERSION)-memcached php%(VERSION)-mysql php%(VERSION)-opcache",
      "php%(VERSION)-readline php%(VERSION)-redis",
      "php%(VERSION)-msgpack php%(VERSION)-phpdbg php%(VERSION)-xml",
      "php%(VERSION)-zip"
  ],
  "FpmReplacements": [
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
  "CliReplacements": [
    "memory_limit|2048M", 
    "upload_max_filesize|512M",
    "max_file_uploads|100",
    "post_max_size|512M",
    "max_execution_time|600",
    "max_input_time|600",
    "default_socket_timeout|600"
  ]
}
```
"SERVICE": "examplesv"
```
The variable can be used at any position of the form (including in other variables) 
with the syntax %&lt;<name>), for example %(SERVICE).


### The Form standard-host
<code>form2linux install example-standard-host</code> shows the following:
```
{
  "Variables": {
    "EMAIL": "any@gmx.de"
  },
  "ConfigurationDirectory": "/etc/form2linux",
  "Packages": [
      "htop iotop tmux bzip2 zip unzip rsync sudo zram-tools smartmontools wget curl",
      "nfs-common nfs-kernel-server nmap openssh-server iotop jnettop ssl-cert ca-certificates net-tools ntp",
      "ssmtp sharutils"
  ],
  "Ssmtp": {
      "Directory": "/etc/ssmtp",
      "Sender": "%(EMAIL)",
      "!Code": "",
      "MailHub": "mail.gmx.net:587",
      "Users": "root,jonny",
      "Comment": "StartTLS or TLS",
      "Mode": "StartTLS"
  }
}
```

#### ConfigurationDirectory
That is the directory storing configuration files of the package form2linux.

#### Packages:
That is a list of entries. Each entry is a blank delimited list of package names.

This structure allows grouping packages by some user defined criteria.

#### Ssmtp Directory
That is the directory storing configuration files of the package ssmtp.

#### Ssmtp Sender
That is the email address of the account from the mail hub.

#### Ssmtp !Code
That is the password of the account from the mail hub.

#### Ssmtp MailHub
That is the domain of the SMTP provider with the port of the SMTP service.

#### Ssmtp Users
A comma separated list of linux users that can send mail.

#### Ssmtp Mode
Defines the transport encryption: StartTLS or TLS

### The Sub Command php
That command installs and configurures the PHP packages.

Create a form (with example-php), adapt the values to your request and start the installation.

#### The Form
The call <code>form2linux install example-php show the following:
```
{
  "Variables": {
    "VERSION": "8.2"
  },
  "ConfigurationDirectory": "/etc/php/%(VERSION)",
  "Repository": { 
      "File": "/etc/apt/sources.list.d/php.list", 
      "Contents": "deb https://packages.sury.org/php/ bookworm main",
      "Initialization": [
        "sudo rm -f /tmp/php.gpg",
        "wget -qO /tmp/php.gpg https://packages.sury.org/php/apt.gpg",
        "sudo cp -a /tmp/php.gpg /etc/apt/trusted.gpg.d/php.gpg"
      ]
   },
  "Comment": "php8.2-xdebug php8.2-pgsql",
  "Packages": [
      "php%(VERSION) php%(VERSION)-curl php%(VERSION)-gd php%(VERSION)-igbinary",
      "php%(VERSION)-imagick php%(VERSION)-intl php%(VERSION)-mbstring",
      "php%(VERSION)-memcached php%(VERSION)-mysql php%(VERSION)-opcache",
      "php%(VERSION)-readline php%(VERSION)-redis",
      "php%(VERSION)-msgpack php%(VERSION)-phpdbg php%(VERSION)-xml",
      "php%(VERSION)-zip"
  ],
  "FpmReplacements": [
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
  "CliReplacements": [
    "memory_limit|2048M", 
    "upload_max_filesize|512M",
    "max_file_uploads|100",
    "post_max_size|512M",
    "max_execution_time|600",
    "max_input_time|600",
    "default_socket_timeout|600"
  ]
}
```
#### Description
- "ConfigurationDirectory": the PHP base configuration directory. There must be two subdirs: fpi and cli
- "Repository": specifies the package repository for more PHP versions.
    - "File": the apt source file
    -  "Contents": the content of the apt source file
    - "Initialization": a list of commands to get the apt source file
- "FpmReplacements": a list of rules to modify PHP configuration variables for the FPM sub system.
    - Each rule contains 2 or 3 parts, separated by '|': NAME|VALUE or NAME|VALUE|ANCHOR
    - The anchor is used if the variable is not found in the file: the variable definition 
is inserted behind the anchor or at the end if no anchor is given or the anchor is not found
- "CliReplacements": a list of rules to modify PHP configuration variables for the CLI sub system.
    - Each rule contains 2 or 3 parts, separated by '|': NAME|VALUE or NAME|VALUE|ANCHOR
    - The anchor is used if the variable is not found in the file: the variable definition 
is inserted behind the anchor or at the end if no anchor is given or the anchor is not found


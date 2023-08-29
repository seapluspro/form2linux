## The Task "Install"

The task "Install" installs some packages.

The components must be defined in a Json form.

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
form2linux install --help
form2linux install example-standard-host myform.json
form2linux install standard-host myform.json
```

### Variables
In all sections you can define strings occurring more than one time in the form.

Each variable is defined by a name and the value:

Example: The variable SERVICE should have the value "servicesv":

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

### Ssmtp Directory
That is the directory storing configuration files of the package ssmtp.

### Ssmtp Sender
That is the email address of the account from the mail hub.

### Ssmtp !Code
That is the password of the account from the mail hub.

### Ssmtp MailHub
That is the domain of the SMTP provider with the port of the SMTP service.

### Ssmtp Users
A comma separated list of linux users that can send mail.

### Ssmtp Mode
Defines the transport encryption: StartTLS or TLS

## The Task "Service"

The task "Service" creates a simple SystemD service from its components.

The components must be defined in a Json form.

### Usage
```
usage: form2linux service [-h] {example,check,install} ...

positional arguments:
  {example,check,install}
                        service help
    example             shows an example configuration file. Can be used as template for a new service.
    check               checks the configuration file
    install             Installs a systemd service defined by a Json configuration file.

options:
  -h, --help            show this help message and exit
```

### Examples
```
form2linux --help
form2linux service example > service.json
# Modify "service.service" with your request
form2linux service install service.json
```

### The Form
<code>form2linux service example</code> shows the following:
```
{
  "Variables": {
    "SERVICE": "examplesv",
    "USER": "nobody",
    "SCRIPT_NODE": "%(SERVICE)",
    "SCRIPT": "/usr/local/bin/%(SCRIPT_NODE)"
  },
  "Service": {
    "Name": "%(SERVICE)",
    "Description": "A example service doing nothing.",
    "File": "/etc/systemd/system/%(SERVICE).service",
    "User": "%(USER)",
    "Group": "%(USER)",
    "WorkingDirectory": "/tmp",
    "EnvironmentFile": "-/etc/%(SERVICE)/%(SERVICE).env",
    "ExecStart": "%(SCRIPT) daemon",
    "ExecReload": "%(SCRIPT) reload",
    "SyslogIdentifier": "%(SERVICE)",
    "StandardOutput": "syslog",
    "StandardError": "syslog",
    "Restart": "always",
    "RestartSec": 5
  },
  "Directories": [
    "/usr/local/bin",
    "/var/log/local",
    "/etc/%(SERVICE)"
  ],
  "Files": {
    "scripts/%(SCRIPT_NODE)": "/etc/%(SERVICE)/"
  },
  "Links": {
    "/etc/%(SERVICE)/": "/usr/local/bin/%(SERVICE)"
  }
}
```

#### Variables
In that section you can define Strings occurring more than one time in the form.

Each variable is defined by a name and the value:

Example: The variable SERVICE should have the value "servicesv":

```
"SERVICE": "examplesv"
```
The variable can be used at any position of the form (including in other variables) 
with the syntax %&lt;<name>), for example %(SERVICE).

#### Service User

The service is started with that user. If id does not exist it will be created.

#### Service Group

The service is started with that group. If id does not exist it will be created.
It may be empty: "".

#### Service ExecStart

The command that starts the service.

#### Service ExecReload

The command that restarts the service. May be empty: "".

#### Files
That is a list of files to create while installation.

Each file is specified by a source file (or a pattern with the wildcards '*' and '?')
and a destination definition, for example: <code>"/home/ws/data/config.txt": "etc/myapp/"</code>

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


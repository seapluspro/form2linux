#! /usr/bin/python3
# encoding: utf-8
'''
form2linux -- shortdesc

form2linux is a command line tool which can some Linux task specified by a form in Json format.

It offers some sub commands:
<ul>
<li>package
    <ul><li>example: prints a example configuration file. Use it as template for a new project.</li<
    <li>check: checks the configuration file</li>
    <li>build: builds the debian package</li>
    </ul>
</li>
<li>service
    <ul><li>example: prints a example configuration file. Use it as template for a new project.</li<
    <li>check: checks the configuration file</li>
    <li>install: build service configuration file and install the service.</li>
    </ul>
</li>
</ul>
@author:     SeaPlusPro

@license:    CC0 Universal

@contact:    seapluspro@gmail.com
@deffield    updated: Updated
'''
# pylint: disable-next=invalid-name

import sys
import os
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from PackageBuilder import PackageBuilder
from TextTool import TextTool
from ServiceBuilder import ServiceBuilder
from SetupBuilder import SetupBuilder
from Builder import CLIError

__all__ = []
__version__ = '0.3.1'
__date__ = '2023-08-20'
__updated__ = '2023-08-25'

DEBUG = 1
TESTRUN = 0
PROFILE = 0


def buildUsageMessage(argv):
    '''Builds data for usage.
    @return a tuple (programLicense, programVersionMessage)
    '''
    programName = os.path.basename(argv[0])
    programVersion = f'v{__version__}'
    programBuildDate = str(__updated__)
    programVersionMessage = f'%(prog)s {programVersion} ({programBuildDate})'

    programShortDesc = __import__('__main__').__doc__.split('\n')[1]
    programLicense = f'''{programShortDesc}

  Created by SeePlusPro on {__date__}.
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

'''
    return (programLicense, programVersionMessage, programName)


def defineSetup(subparsersMain):
    '''Defines the sub commands / options of the section "setup".
    @param subparsersMain: the parent of the new parsers
    '''
    parserSetup = subparsersMain.add_parser(
        'setup', help='archive and restore, setup of a new system.')
    subparsersSetup = parserSetup.add_subparsers(
        help='setup help', dest='setup')
    parserAdaptUsers = subparsersSetup.add_parser(
        'adapt-users',  help='creates users and groups from safed versions of passwd and group')
    parserAdaptUsers.add_argument(
        'passwd', help='a saved version of /etc/passwd')
    parserAdaptUsers.add_argument(
        'group', help='a saved version of /etc/group')
    parserAdaptUsers.add_argument(
        'shadow', help='a saved version of /etc/shadow')

    parserAddStandardUsers = subparsersSetup.add_parser(
        'add-standard-users', help='creates users and groups from a Json form')
    parserAddStandardUsers.add_argument(
        'form', help='a safed version of /etc/passwd')

    parserExampleAddStandardUsers = subparsersSetup.add_parser(
        'example-add-standard-users', help='shows a form for the "add-standard-users" command')
    parserExampleAddStandardUsers.add_argument(
        '-f', '--file', dest='file', help='the output is stored there')

    parserArchive = subparsersSetup.add_parser(
        'archive',  help='stores files into a archive')
    parserArchive.add_argument(
        'form', help='the Json file with the archive definitions')
    parserArchive.add_argument(
        '-f', '--file', help='the list of the files will be stored there', default="*")

    parserExampleArchive = subparsersSetup.add_parser(
        'example-archive',  help='shows the form of the command "archive"')
    parserExampleArchive.add_argument(
        '-f', '--file', dest='file', help='the result is stored there')

    parserPatchShadow = subparsersSetup.add_parser(
        'patch-shadow',  help='puts an encoded password into the shadow password file')
    parserPatchShadow.add_argument(
        'user', help='the user of the entry to change')
    parserPatchShadow.add_argument(
        'passwd', help='the encoded password')
    parserPatchShadow.add_argument(
        '-f', '--file', dest='file', help='the shadow file', default='/etc/shadow')

    parserSystemInfo = subparsersSetup.add_parser(
        'system-info',  help='assembles the state of the current system')
    parserSystemInfo.add_argument(
        'form', help='the form with the configuration')

    parserExampleSystemInfo = subparsersSetup.add_parser(
        'example-system-info',  help='shows an example form for the command "system-info"')
    parserExampleSystemInfo.add_argument(
        '-f', '--file', dest='file', help='the result is stored there')


def definePackage(subparsersMain):
    '''Defines the sub commands / options of the section "package".
    @param subparsersMain: the parent of the new parsers
    '''
    parserPackage = subparsersMain.add_parser(
        'package', help='Builds a debian package from a package description in Json format.')
    subparsersPackage = parserPackage.add_subparsers(
        help='package help', dest='package')
    parserExample = subparsersPackage.add_parser(
        'example', help='shows an example configuration file. Can be used for initializing a new package project.')
    parserExample.add_argument('-f', '--file', dest='file',
                               help='the output is stored in that file')
    parserCheck = subparsersPackage.add_parser(
        'check', help='checks the configuration file')
    parserCheck.add_argument(
        'configuration', help='the configuration file', default='project.json')
    parserBuild = subparsersPackage.add_parser(
        'build', help='builds the debian package')
    parserBuild.add_argument(
        'configuration', help='defines the properties and the contents of the Debian package.', default='package.json')


def defineService(subparsersMain):
    '''Defines the sub commands / options of the section "service".
    @param subparsersMain: the parent of the new parsers
    '''
    parserService = subparsersMain.add_parser(
        'service', help='Installs a SystemD service.')
    subparsersService = parserService.add_subparsers(
        help='service help', dest='service')
    parserExampleService = subparsersService.add_parser(
        'example', help='shows an example configuration file. Can be used as template for a new service.')
    parserExampleService.add_argument('-f', '--file', dest='file',
                                      help='the output is stored in that file')
    parserCheckService = subparsersService.add_parser(
        'check', help='checks the configuration file')
    parserCheckService.add_argument(
        'configuration', help='the configuration file', default='project.json')
    parserInstallService = subparsersService.add_parser(
        'install', help='Installs a systemd service defined by a Json configuration file.')
    parserInstallService.add_argument(
        'configuration', help='defines the properties of the service.', default='service.json')


def defineText(subparsersMain):
    '''Defines the sub commands / options of the section "text".
    @param subparsersMain: the parent of the new parsers
    '''
    parserText = subparsersMain.add_parser(
        'text', help='Some text manipulation.')
    subparsersText = parserText.add_subparsers(
        help='text help', dest='text')
    parserReplaceRange = subparsersText.add_parser(
        'replace-range', help='replaces a section in text document with a string or a file.')
    parserReplaceRange.add_argument(
        'document', help='the document to change.')
    parserReplaceRange.add_argument(
        '-f', '--file', dest='file', help="the file contents is the replacement. Exclusive alternative: --replacement")
    parserReplaceRange.add_argument('-r', '--replacement', dest='replacement',
                                    help="defines the replacement as string. Exclusive alternative: --file")
    parserReplaceRange.add_argument(
        '-s', '--start', dest='start', help="a regular expression starting the range to change.", default="```")
    parserReplaceRange.add_argument(
        '-e', '--end', dest='end', help="a regular expression ending the range to change.", default="```")
    parserReplaceRange.add_argument('-a', '--anchor', dest='anchor',
                                    # pylint disable-next=line-too-long
                                    help="a regular expression defining the position of the text change. " +
                                    "Than the next range is replaced by the program's output.",
                                    default=None)
    # pylint: disable-next=line-too-long
    parserReplaceRange.add_argument('-m', '--min-length', dest='minLength',
                                    help="the replacement or replacement file must have at least that length",
                                    default=3)
    parserReplaceRange.add_argument('-n', '--newline', action="store_true",
                                    dest='newline', help="add a newline at the --replacement string")


def executePackage(args, verbose: bool, dry: bool):
    '''Switches to a subcommand of "package".
    @param args: the arguments
    @param verbose: True: show info messages
    @param dry: says what to do, but do nothing
    '''
    builder = PackageBuilder(verbose, dry)
    if args.package == 'example':
        builder.example(args.file)
    elif args.package == 'check':
        builder.check(args.configuration)
    elif args.package == 'build':
        builder.build(args.configuration)
    else:
        raise CLIError(f'unknown command: {args.package}')


def executeService(args, verbose: bool, dry: bool):
    '''Switches to a subcommand of "service".
    @param args: the arguments
    @param verbose: True: show info messages
    @param dry: says what to do, but do nothing
    '''
    builder = ServiceBuilder(verbose, dry)
    if args.service == 'example':
        builder.example(args.file)
    elif args.service == 'check':
        builder.check(args.configuration)
    elif args.service == 'install':
        builder.install(args.configuration)
    else:
        raise CLIError(f'unknown command: {args.package}')


def executeSetup(args, verbose: bool, dry: bool):
    '''Switches to a subcommand of "setup".
    @param args: the arguments
    @param verbose: True: show info messages
    @param dry: says what to do, but do nothing
    '''
    builder = SetupBuilder(verbose, dry)
    if args.setup == 'add-standard-users':
        builder.addStandardUsers(args.form)
    elif args.setup == 'adapt-users':
        builder.adaptUsers(args.passwd, args.group, args.shadow)
    elif args.setup == 'example-add-standard-users':
        builder.exampleStandardUsers(args.file)
    elif args.setup == 'example-archive':
        builder.exampleArchive(args.file)
    elif args.setup == 'example-archive':
        builder.exampleArchive(args.file)
    elif args.setup == 'archive':
        builder.archive(args.form, args.file)
    elif args.setup == 'patch-shadow':
        builder.patchShadow(args.user, args.passwd, args.file)
    elif args.setup == 'example-standard-users':
        builder.exampleStandardUsers(args.file)
    elif args.setup == 'system-info':
        builder.systemInfo(args.form)
    elif args.setup == 'example-system-info':
        builder.exampleSystemInfo(args.file)
    else:
        raise CLIError(f'unknown command: {args.setup}')

# xpylint: disable-next=too-many-statements,too-many-branches,too-many-locals


def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    programLicense, programVersionMessage, programName = buildUsageMessage(
        argv)
    try:
        # Setup argument parser
        parser = ArgumentParser(
            description=programLicense, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument('-v', '--verbose', dest='verbose', action='count',
                            help='set verbosity level [default: %(default)s]')
        parser.add_argument('-V', '--version', action='version',
                            version=programVersionMessage)
        parser.add_argument('-y', '--dry', dest='dry', action="store_true",
                            help="do not create files and directories")

        subparsersMain = parser.add_subparsers(
            help='sub-command help', dest='main')

        defineSetup(subparsersMain)

        definePackage(subparsersMain)

        defineService(subparsersMain)

        defineText(subparsersMain)

        # Process arguments
        args = parser.parse_args(argv[1:])

        verbose = args.verbose
        dry = args.dry
        if args.main == 'package':
            executePackage(args, verbose, dry)
        elif args.main == 'service':
            executeService(args, verbose, dry)
        elif args.main == 'setup':
            executeSetup(args, verbose, dry)
        elif args.main == 'text':
            if args.text == 'replace-range':
                builder = TextTool(verbose, dry)
                builder.replaceRange(args.document, args.replacement, args.file,
                                     args.anchor, args.start, args.end, args.minLength,
                                     args.newline)
            else:
                raise CLIError(f'unknown command: {args.text}')
        else:
            raise CLIError(f'unknown command: {args.main}')
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    # pylint: disable-next=broad-exception-caught
    except Exception as exc:
        if DEBUG or TESTRUN:
            raise exc
        indent = len(programName) * ' '
        sys.stderr.write(programName + ': ' + repr(exc) + '\n')
        sys.stderr.write(indent + '  for help use --help')
        return 2


if __name__ == '__main__':
    sys.exit(main())

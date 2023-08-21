'''
LinuxUtils.py

Created on: 20.08.2023
    Author: SeaPlusPro
   License: CC0 1.0 Universal
'''

import os
import subprocess
import re
import stat
import pwd
import grp

import base.StringUtils


def diskFree(verboseLevel=0, logger=None):
    '''Returns an info about the mounted filesystems.
    @return: a list of info entries: entry: [mountPath, totalBytes, freeBytes, availableBytesForNonPrivilegs]
    '''
    if logger is not None and verboseLevel > base.Const.LEVEL_LOOP:
        logger.log('taskFileSystem()...', verboseLevel)

    rc = []
    ignoredDevs = ['udev', 'devpts', 'tmpfs', 'securityfs', 'pstore',
                   'cgroup', 'tracefs', 'mqueue', 'hugetlbfs', 'debugfs']
    with open('/proc/mounts', 'r') as f:
        for line in f:
            dev, path, fstype, rest = line.split(None, 3)
            base.StringUtils.avoidWarning(rest)
            if logger is not None and verboseLevel >= base.Const.LEVEL_FINE:
                logger.log(line, verboseLevel)
            if (fstype in ['sysfs', 'proc'] or dev in ignoredDevs):
                continue
            if (path.startswith('/proc/') or path.startswith('/sys/') or path.startswith('/run/')
                    or path.startswith('/dev/loop') or path.startswith('/snap/')):
                continue
            if not os.path.isdir(path):
                continue
            if logger is not None and verboseLevel >= base.Const.LEVEL_FINE:
                logger.log(path + '...', verboseLevel)
            info = diskInfo(path)
            if info is not None:
                rc.append(info)
    return rc


def diskInfo(path):
    '''Returns some infe about a mounted block device.
    @param path: the mount path
    @return: None: not available otherwise: [mountPath, totalBytes, freeBytes, availableBytesForNonPrivilegs]
    '''
    rc = None
    try:
        stat1 = os.statvfs(path)
        blocksize = stat1.f_bsize
        # ....path, total, free, available
        rc = [path, stat1.f_blocks * blocksize, stat1.f_bfree *
              blocksize, stat1.f_bavail * blocksize]
    except FileNotFoundError:
        # if mounted by autofs: the path can not be found
        pass
    return rc


def disksMounted(logger=None):
    '''Returns a list of mounted filesystems.
    @return: a list of mounted filesystems, e.g. ['/', '/home']
    '''
    if logger is not None:
        logger.log('taskFileSystem()...', base.Const.LEVEL_LOOP)

    rc = []
    ignoredDevs = ['udev', 'devpts', 'tmpfs', 'securityfs', 'pstore',
                   'cgroup', 'tracefs', 'mqueue', 'hugetlbfs', 'debugfs']
    with open('/proc/mounts', 'r') as f:
        found = []
        for line in f:
            dev, path, fstype, rest = line.split(None, base.Const.LEVEL_LOOP)
            base.StringUtils.avoidWarning(rest)
            if dev in found:
                continue
            found.append(dev)
            if logger is not None:
                logger.log(line.rstrip(), base.Const.LEVEL_LOOP)
            if fstype == 'sysfs' or fstype == 'proc' or dev in ignoredDevs:
                continue
            if (path.startswith('/proc/')
                    or path.startswith('/sys/') or path.startswith('/run/')
                    or path.startswith('/dev/loop')
                    or path.startswith('/snap/')):
                continue
            if not os.path.isdir(path):
                continue
            rc.append(path)
    return rc


def diskIo():
    '''Returns a list of [diskname, countReads, countWrites, countDiscards] arrays.
    Data are accumulated since last boot.
    Note: sector size: 512 Byte
    @see https://www.kernel.org/doc/Documentation/iostats.txt
    @return: array of arrays [id, diskname, countReads, countWrites, countDiscards], e.g. [ ['8-0-sda', 299, 498, 22 ] ]
    '''
    rc = []
    with open('/proc/diskstats', 'r') as fp:
        for line in fp:
            # 1......2.....3....4.............5...........6...........7.........8..............
            # mainid subid name readscomplete readsmerged readsectors readmsecs writescomplete
            # 9............10...........11.........12.........13.....14.............15................
            # writesmerged writesectors writesmsec inprogress iomsec weightediomsec discardscompleted
            # 16.............17...............18
            # discardsmerged discardssectors  discardsmsec
            # 8 0 sda 101755 2990 6113900 37622 69827 44895 1535408 41169 0 85216 2732 0 0 0 0
            # 8 1 sda1 82 0 6368 22 0 0 0 0 0 76 0 0 0 0 0
            parts = line.split()
            rc.append(['{}-{}'.format(parts[0], parts[1]),
                       parts[2], parts[5], parts[9], parts[16]])
    return rc


def groupId(nameOrId, defaultValue=None):
    '''Returns the group id of a given group name.
    @param nameOrId: normally a group. If this is a number this will taken as result
    @param defaultValue: the result value when the group name is unknown
    @return: defaultValue: unknown group name otherwise: the group id
    '''
    if isinstance(nameOrId, int):
        rc = nameOrId
    elif base.StringUtils.asInt(nameOrId) is not None:
        rc = base.StringUtils.asInt(nameOrId)
    else:
        try:
            rc = grp.getgrnam(nameOrId).gr_gid
        except KeyError:
            rc = defaultValue
    return rc


def isExecutable(statInfo, euid, egid):
    '''Tests whether the file or directory) is executable
    @param statInfo: the result of os.stat()
    @param euid: the effective UID of the current process. We can get it with os.geteuid()
    @param egid: the the effective GID of the current process. We can get it with os.getegid()
    @return: True: the file is executable
    '''
    if statInfo.st_uid == euid:
        # S_IXUSR S_IXGRP S_IXOTH
        mask = (stat.S_IXUSR | stat.S_IXOTH)
    elif statInfo.st_gid == egid:
        mask = (stat.S_IXGRP | stat.S_IXOTH)
    else:
        mask = stat.S_IXOTH
    return (statInfo.st_mode & mask) != 0


def isReadable(statInfo, euid, egid):
    '''Tests whether the file or directory) is readable.
    @param statInfo: the result of os.stat()
    @param euid: the effective UID of the current process. We can get it with os.geteuid()
    @param egid: the the effective GID of the current process. We can get it with os.getegid()
    @return: True: the file is readable
    '''
    if statInfo.st_uid == euid:
        # S_IXUSR S_IXGRP S_IXOTH
        mask = (stat.S_IRUSR | stat.S_IROTH)
    elif statInfo.st_gid == egid:
        mask = (stat.S_IRGRP | stat.S_IROTH)
    else:
        mask = stat.S_IROTH
    return (statInfo.st_mode & mask) != 0


def isWritable(statInfo, euid, egid):
    '''Tests whether the file or directory) is writable.
    @param statInfo: the result of os.stat()
    @param euid: the effective UID of the current process. We can get it with os.geteuid()
    @param egid: the the effective GID of the current process. We can get it with os.getegid()
    @return: True: the file is writable
    '''
    if statInfo.st_uid == euid:
        mask = (stat.S_IWUSR | stat.S_IWOTH)
    elif statInfo.st_gid == egid:
        mask = (stat.S_IWGRP | stat.S_IWOTH)
    else:
        mask = stat.S_IWOTH
    return (statInfo.st_mode & mask) != 0


def stress(patternDisks, patternInterface):
    '''Returns the load data of a server.
    Note: the byte data (ioReadBytes ... netWriteBytes) are summarized since boot time.
    @param patternDisk: a regular expression of the disk devices used for the result (sum is built), e.g. 'sd[ab]'
    @param patternInterface: a regular expression of the network interfaces used for the result (sum is built), e.g. 'eth0|wlan0'
    @return: [ioReadBytes, ioWriteBytes, netReadBytes, netWriteBytes, load1Minute, memoryAvailable, swapAvailable]
    '''
    readIO = 0
    writeIO = 0
    rexprDisks = base.StringUtils.regExprCompile(patternDisks, 'disk pattern')
    with open('/proc/diskstats', 'r') as fp:
        for line in fp:
            # 1......2.....3....4.............5...........6...........7.........8..............
            # mainid subid name readscomplete readsmerged readsectors readmsecs writescomplete
            # 9............10...........11.........12.........13.....14.............15................
            # writesmerged writesectors writesmsec inprogress iomsec weightediomsec discardscompleted
            # 16.............17...............18
            # discardsmerged discardssectors  discardsmsec
            # 8 0 sda 101755 2990 6113900 37622 69827 44895 1535408 41169 0 85216 2732 0 0 0 0
            # 8 1 sda1 82 0 6368 22 0 0 0 0 0 76 0 0 0 0 0
            parts = line.split()
            if rexprDisks.match(parts[2]) is not None:
                readIO += int(parts[5])
                writeIO += int(parts[9])
    readIO *= 512
    writeIO *= 512
    readNet = 0
    writeNet = 0
    rexprNet = base.StringUtils.regExprCompile(
        patternInterface, 'interface pattern')
    with open('/proc/net/dev', 'r') as fp:
        for line in fp:
            # 1......2........3......4....5....6....7.....8..........9.........10.......
            # Inter-|   Receive                                                |  Transmit
            # 11.....12....13...14...15....16......17
            # face |bytes    packets errs drop fifo frame compressed multicast|bytes
            # packets errs drop fifo colls carrier compressed
            # lo:   33308     376    0    0    0     0          0         0    33308
            # 376    0    0    0     0       0          0
            parts = line.split()
            # remove ':' from the first field:
            if rexprNet.match(parts[0][0:-1]) is not None:
                readNet += int(parts[1])
                writeNet += int(parts[9])
    with open('/proc/loadavg', 'rb') as fp:
        loadMin1 = float(fp.read().decode().split()[0])
    #@return: [TOTAL_RAM, AVAILABLE_RAM, TOTAL_SWAP, FREE_SWAP, BUFFERS]
    with open('/proc/meminfo', 'r') as fp:
        lines = fp.read().split('\n')
        freeRam = _getNumber(lines[2])
        freeSwap = _getNumber(lines[15])
    return [readIO, writeIO, readNet, writeNet, loadMin1, freeRam, freeSwap]


def userId(nameOrId, defaultValue=None):
    '''Returns the user id of a given user name.
    @param nameOrId: normally a username. If this is a number this will taken as result
    @param defaultValue: the result value when the user name is unknown
    @return: defaultValue: unknown user name otherwise: the user id
    '''
    if isinstance(nameOrId, int):
        rc = nameOrId
    elif base.StringUtils.asInt(nameOrId) is not None:
        rc = base.StringUtils.asInt(nameOrId)
    else:
        try:
            rc = pwd.getpwnam(nameOrId).pw_uid
        except KeyError:
            rc = defaultValue
    return rc


def users():
    '''Returns the users currently logged in.
    @return: None: parser error. otherwise: tuple of entries (USERNAME, IP, LOGINSTART, LOGINDURATION, CPUTIME)
    '''
    with subprocess.Popen('/usr/bin/w', stdout=subprocess.PIPE) as proc:
        data = proc.stdout.read().decode()
    lines = data.split('\n')[2:]
    rc = []
    for line in lines:
        if line == '':
            break
        # hm       pts/0    88.67.239.209    21:17    1:32 m  6:37   0.04 s w
        # hm       pts/0    88.67.239.209    21:17    60s  0.00s  0.00s w
        parts = line.split()
        if len(parts) < 4:
            rc = None
            break
        rc.append((parts[0], parts[2], parts[3], parts[4],
                   parts[5] if parts[5].find(':') > 0 else parts[6]))
    return rc


def load():
    '''Returns average loads.
    @return: [LOAD_1_MINUTE, LOAD_5_MINUTE, LOAD_10_MINUTE, RUNNING_PROCESSES, PROCESSES]
    '''
    with open('/proc/loadavg', 'rb') as fp:
        data = fp.read().decode()
        matcher = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+(\d+)/(\d+)', data)
        if matcher is None:
            rc = None
        else:
            rc = [float(matcher.group(1)), float(matcher.group(2)), float(matcher.group(3)),
                  int(matcher.group(4)), int(matcher.group(5))]
    return rc


def _getNumber(line):
    parts = line.split()
    return int(parts[1])


def memoryInfo():
    '''Returns the memory usage.
    @return: [TOTAL_RAM, AVAILABLE_RAM, TOTAL_SWAP, FREE_SWAP, BUFFERS]
    '''
    with open('/proc/meminfo', 'rb') as fp:
        lines = fp.read().decode().split('\n')
        rc = [_getNumber(lines[0]), _getNumber(lines[2]), _getNumber(
            lines[14]), _getNumber(lines[15]), _getNumber(lines[3])]
    return rc


def mdadmInfo(filename='/proc/mdstat'):
    '''Returns the info about the software raid systems.
    @return: a list of array [name, type, members, blocks, status>,
        e.g. [['md0', 'raid1', 'dm-12[0] dm-13[1]', 1234, 'OK'], ['md1', 'raid0', 'sda1[0] sdb1[1]', 1234, 'broken']]
        status: 'OK', 'recovery', 'broken'
    '''
    rc = []
    if os.path.exists(filename):
        with open(filename, 'r') as fp:
            # md2 : active raid1 sdc1[0] sdd1[1]
            # md1 : active raid1 hda14[0] sda11[2](F)
            rexpr1 = re.compile(r'^(\w+) : active (raid\d+) (.*)')
            #  1953378368 blocks super 1.2 [2/2] [UU]
            rexpr2 = re.compile(r'^\s+(\d+) blocks.*\[([_U]+)\]')
            members = None
            for line in fp:
                matcher = rexpr1.match(line)
                if matcher:
                    name = matcher.group(1)
                    aType = matcher.group(2)
                    members = matcher.group(3)
                    continue
                matcher = rexpr2.match(line)
                if matcher:
                    blocks = matcher.group(1)
                    status = matcher.group(2)
                    status2 = 'broken' if status.find(
                        '_') >= 0 or members is not None and members.find('(F)') > 0 else 'OK'
                    rc.append([name, aType, members, int(blocks), status2])
                    continue
                if line.find('recovery') > 0:
                    rc[len(rc) - 1][4] = 'recovery'
    return rc


def main():
    '''main function.
    '''
    infos = diskFree()
    for info in infos:
        print(base.StringUtils.join(' ', info))


if __name__ == '__main__':
    main()

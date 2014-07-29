#!/usr/bin/python
# Copyright (c) 2003-2012 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id: psexec.py 712 2012-09-06 04:26:22Z bethus@gmail.com $
#
# PSEXEC like functionality example using
#RemComSvc (https://github.com/kavika13/RemCom)
#
# Author:
#  beto (bethus@gmail.com)
#
# Reference for:
#  DCE/RPC and SMB.

""".

OK
"""


import cmd
import os
import re
import sys

#from impacket.smbconnection import *
from impacket.dcerpc import dcerpc
from impacket.dcerpc import transport
from impacket.examples import remcomsvc
from impacket.examples import serviceinstall
from impacket import smbconnection
from impacket import structure as im_structure
from impacket import version
#from impacket.dcerpc import dcerpc_v4
#from impacket.dcerpc import srvsvc
#from impacket.dcerpc import svcctl
#from impacket.smbconnection import smb
#from impacket.smbconnection import SMB_DIALECT
#from impacket.smbconnection import SMBConnection

import argparse
import random
import string
import threading
import time


class RemComMessage(im_structure.Structure):

    """."""

    structure = (
        ('Command', '4096s=""'),
        ('WorkingDir', '260s=""'),
        ('Priority', '<L=0x20'),
        ('ProcessID', '<L=0x01'),
        ('Machine', '260s=""'),
        ('NoWait', '<L=0'),
    )


class RemComResponse(im_structure.Structure):

    """."""

    structure = (
        ('ErrorCode', '<L=0'),
        ('ReturnCode', '<L=0'),
    )

RemComSTDOUT = "RemCom_stdout"
RemComSTDIN = "RemCom_stdin"
RemComSTDERR = "RemCom_stderr"

lock = threading.Lock()


class PSEXEC:

    """."""

    KNOWN_PROTOCOLS = {
        '139/SMB': (r'ncacn_np:%s[\pipe\svcctl]', 139),
        '445/SMB': (r'ncacn_np:%s[\pipe\svcctl]', 445),
        }

    def __init__(self, command, path, exeFile, protocols=None,
                 username='', password='', domain='', hashes=None):
        """."""
        if not protocols:
            protocols = PSEXEC.KNOWN_PROTOCOLS.keys()

        self.__username = username
        self.__password = password
        self.__protocols = [protocols]
        self.__command = command
        self.__path = path
        self.__domain = domain
        self.__lmhash = ''
        self.__nthash = ''
        self.__exeFile = exeFile
        if hashes is not None:
            self.__lmhash, self.__nthash = hashes.split(':')

    def run(self, addr):
        """."""
        for protocol in self.__protocols:
            protodef = PSEXEC.KNOWN_PROTOCOLS[protocol]
            port = protodef[1]

            print("Trying protocol %s...\n" % protocol)
            stringbinding = protodef[0] % addr

            rpctransport = transport.DCERPCTransportFactory(stringbinding)
            rpctransport.set_dport(port)
            if hasattr(rpctransport, 'preferred_dialect'):
                rpctransport.preferred_dialect(smbconnection.SMB_DIALECT)
            if hasattr(rpctransport, 'set_credentials'):
                # This method exists only for selected protocol sequences.
                rpctransport.set_credentials(self.__username, self.__password,
                                             self.__domain, self.__lmhash,
                                             self.__nthash)

            self.doStuff(rpctransport)

    def openPipe(self, s, tid, pipe, accessMask):
        """."""
        pipeReady = False
        tries = 50
        while pipeReady is False and tries > 0:
            try:
                s.waitNamedPipe(tid, pipe)
                pipeReady = True
            except Exception:
                tries -= 1
                time.sleep(2)
                pass

        if tries == 0:
            print('[!] Pipe not ready, aborting')
            raise

        fid = s.openFile(tid, pipe, accessMask, creationOption=0x40,
                         fileAttributes=0x80)

        return fid

    def doStuff(self, rpctransport):
        """."""
        dce = dcerpc.DCERPC_v5(rpctransport)
        try:
            dce.connect()
        except Exception as e:
            print(e)
            sys.exit(1)

        global dialect
        dialect = rpctransport.get_smb_connection().getDialect()

        try:
            unInstalled = False
            s = rpctransport.get_smb_connection()

            # We don't wanna deal with timeouts from now on.
            s.setTimeout(100000)
            svcName = "RackspaceSystemDiscovery"
            executableName = "RackspaceSystemDiscovery.exe"
            if self.__exeFile is None:
                svc = remcomsvc.RemComSvc()
                installService = serviceinstall.ServiceInstall(s, svc,
                                                               svcName,
                                                               executableName)
            else:
                try:
                    f = open(self.__exeFile)
                except Exception as e:
                    print(e)
                    sys.exit(1)
                installService = serviceinstall.ServiceInstall(s, f,
                                                               svcName,
                                                               executableName)

            installService.install()

            if self.__exeFile is not None:
                f.close()

            tid = s.connectTree('IPC$')
            fid_main = self.openPipe(s, tid, '\RemCom_communicaton', 0x12019f)

            packet = RemComMessage()
            pid = os.getpid()

            packet['Machine'] = ''.join([random.choice(string.letters)
                                        for i in range(4)])
            if self.__path is not None:
                packet['WorkingDir'] = self.__path
            packet['Command'] = self.__command
            packet['ProcessID'] = pid

            s.writeNamedPipe(tid, fid_main, str(packet))

            # Here we'll store the command we type so we don't print it back ;)
            # ( I know.. globals are nasty :P )
            global LastDataSent
            LastDataSent = ''

            retCode = None
            # Create the pipes threads
            stdin_pipe = RemoteStdInPipe(rpctransport,
                                         '\%s%s%d' % (RemComSTDIN,
                                                      packet['Machine'],
                                                      packet['ProcessID']),
                                         smbconnection.smb.FILE_WRITE_DATA |
                                         smbconnection.smb.FILE_APPEND_DATA,
                                         installService.getShare())
            stdin_pipe.start()
            stdout_pipe = RemoteStdOutPipe(rpctransport,
                                           '\%s%s%d' % (RemComSTDOUT,
                                                        packet['Machine'],
                                                        packet['ProcessID']),
                                           smbconnection.smb.FILE_READ_DATA)
            stdout_pipe.start()
            stderr_pipe = RemoteStdErrPipe(rpctransport,
                                           '\%s%s%d' % (RemComSTDERR,
                                                        packet['Machine'],
                                                        packet['ProcessID']),
                                           smbconnection.smb.FILE_READ_DATA)
            stderr_pipe.start()

            # And we stay here till the end
            ans = s.readNamedPipe(tid, fid_main, 8)

            if len(ans):
                retCode = RemComResponse(ans)
                print("[*] Process %s finished with ErrorCode: %d, "
                      "ReturnCode: %d" % (self.__command, retCode['ErrorCode'],
                                          retCode['ReturnCode']))
            installService.uninstall()
            unInstalled = True
            sys.exit(retCode['ReturnCode'])

        except Exception:
            if unInstalled is False:
                installService.uninstall()
            sys.stdout.flush()
            if retCode:
                sys.exit(retCode['ReturnCode'])
            else:
                sys.exit(1)


class Pipes(threading.Thread):

    """."""

    def __init__(self, transport, pipe, permissions, share=None):
        """."""
        threading.Thread.__init__(self)
        self.server = 0
        self.transport = transport
        self.credentials = transport.get_credentials()
        self.tid = 0
        self.fid = 0
        self.share = share
        self.port = transport.get_dport()
        self.pipe = pipe
        self.permissions = permissions
        self.daemon = True

    def connectPipe(self):
        """."""
        try:
            lock.acquire()
            global dialect

            remoteHost = self.transport.get_smb_connection().getRemoteHost()
            #self.server = SMBConnection('*SMBSERVER',
            #self.transport.get_smb_connection().getRemoteHost(),
            #sess_port = self.port, preferredDialect = SMB_DIALECT)
            self.server = smbconnection.SMBConnection('*SMBSERVER', remoteHost,
                                        sess_port=self.port,
                                        preferredDialect=dialect)  # noqa
            user, passwd, domain, lm, nt = self.credentials
            self.server.login(user, passwd, domain, lm, nt)
            lock.release()
            self.tid = self.server.connectTree('IPC$')

            self.server.waitNamedPipe(self.tid, self.pipe)
            self.fid = self.server.openFile(self.tid, self.pipe,
                                            self.permissions,
                                            creationOption=0x40,
                                            fileAttributes=0x80)
            self.server.setTimeout(1000000)
        except Exception:
            message = ("[!] Something wen't wrong connecting the pipes(%s), "
                       "try again")
            print(message % self.__class__)


class RemoteStdOutPipe(Pipes):

    """."""

    def __init__(self, transport, pipe, permisssions):
        """."""
        Pipes.__init__(self, transport, pipe, permisssions)

    def run(self):
        """."""
        self.connectPipe()
        while True:
            try:
                ans = self.server.readFile(self.tid, self.fid, 0, 1024)
            except Exception:
                pass
            else:
                try:
                        global LastDataSent
                        if ans != LastDataSent:  # noqa
                            sys.stdout.write(ans)
                            sys.stdout.flush()
                        else:
                            # Don't echo what I sent, and clear it up
                            LastDataSent = ''
                        # Just in case this got out of sync, i'm cleaning it
                        # up if there are more than 10 chars,
                        # it will give false positives tho.. we should find a
                        # better way to handle this.
                        if LastDataSent > 10:
                            LastDataSent = ''
                except Exception:
                    pass


class RemoteStdErrPipe(Pipes):

    """."""

    def __init__(self, transport, pipe, permisssions):
        """."""
        Pipes.__init__(self, transport, pipe, permisssions)

    def run(self):
        """."""
        self.connectPipe()
        while True:
            try:
                ans = self.server.readFile(self.tid, self.fid, 0, 1024)
            except Exception:
                pass
            else:
                try:
                    sys.stderr.write(str(ans))
                    sys.stderr.flush()
                except Exception:
                    pass


class RemoteShell(cmd.Cmd):

    """."""

    def __init__(self, server, port, credentials, tid, fid, share):
        """."""
        cmd.Cmd.__init__(self, False)
        self.prompt = '\x08'
        self.server = server
        self.transferClient = None
        self.tid = tid
        self.fid = fid
        self.credentials = credentials
        self.share = share
        self.port = port
        self.intro = '[!] Press help for extra shell commands'

    def connect_transferClient(self):
        """."""
        #self.transferClient = SMBConnection('*SMBSERVER',
        #self.server.getRemoteHost(), sess_port = self.port,
        #preferredDialect = SMB_DIALECT)
        self.transferClient = smbconnection.SMBConnection('*SMBSERVER',
                                            self.server.getRemoteHost(),
                                            sess_port=self.port,
                                            preferredDialect=dialect)  # noqa
        user, passwd, domain, lm, nt = self.credentials
        self.transferClient.login(user, passwd, domain, lm, nt)

    def do_help(self, line):
        """."""
        print("""
 lcd {path}                 - changes the current local directory to {path}
 exit                       - terminates the server process (and this session)
 put {src_file, dst_path}   - uploads a local file to the dst_path RELATIVE to
                              the connected share (%s)
 get {file}                 - downloads pathname RELATIVE to the connected
                              share (%s) to the current local dir
 ! {cmd}                    - executes a local shell cmd
""" % (self.share, self.share))
        self.send_data('\r\n', False)

    def do_shell(self, s):
        """."""
        os.system(s)
        self.send_data('\r\n')

    def do_get(self, src_path):
        """."""
        try:
            if self.transferClient is None:
                self.connect_transferClient()

            import ntpath
            filename = ntpath.basename(src_path)
            fh = open(filename, 'wb')
            print("[*] Downloading %s\%s" % (self.share, src_path))
            self.transferClient.getFile(self.share, src_path, fh.write)
            fh.close()
        except Exception as e:
            print(e)
            pass

        self.send_data('\r\n')

    def do_put(self, s):
        """."""
        try:
            if self.transferClient is None:
                self.connect_transferClient()
            params = s.split(' ')
            if len(params) > 1:
                src_path = params[0]
                dst_path = params[1]
            elif len(params) == 1:
                src_path = params[0]
                dst_path = '/'

            src_file = os.path.basename(src_path)
            fh = open(src_path, 'rb')
            f = dst_path + '/' + src_file
            pathname = string.replace(f, '/', '\\')
            print("[*] Uploading %s to %s\\%s" % (src_file, self.share,
                                                  dst_path))
            self.transferClient.putFile(self.share, pathname, fh.read)
            fh.close()
        except Exception as e:
            print(e)
            pass

        self.send_data('\r\n')

    def do_lcd(self, s):
        """."""
        if s == '':
            print(os.getcwd())
        else:
            os.chdir(s)
        self.send_data('\r\n')

    def emptyline(self):
        """."""
        self.send_data('\r\n')
        return

    def do_EOF(self, line):
        """."""
        self.server.logoff()

    def default(self, line):
        """."""
        self.send_data(line+'\r\n')

    def send_data(self, data, hideOutput=True):
        """."""
        if hideOutput is True:
            global LastDataSent
            LastDataSent = data
        else:
            LastDataSent = ''
        self.server.writeFile(self.tid, self.fid, data)


class RemoteStdInPipe(Pipes):

    """RemoteStdInPipe class.

    Used to connect to RemComSTDIN named pipe on remote system
    """

    def __init__(self, transport, pipe, permisssions, share=None):
        """Constructor."""
        Pipes.__init__(self, transport, pipe, permisssions, share)

    def run(self):
        """."""
        self.connectPipe()
        self.shell = RemoteShell(self.server, self.port, self.credentials,
                                 self.tid, self.fid, self.share)
        self.shell.cmdloop()


# Process command-line arguments.
if __name__ == '__main__':
    print(version.BANNER)

    parser = argparse.ArgumentParser()

    parser.add_argument('target', action='store',
                        help='[domain/][username[:password]@]<address>')
    parser.add_argument('command', action='store',
                        help='command to execute at the target (w/o path)')
    parser.add_argument('-path', action='store',
                        help='path of the command to execute')
    parser.add_argument(
        '-file', action='store',
        help="alternative RemCom binary (be sure it doesn't require CRT)")
    parser.add_argument(
        '-port', action='store',
        help='alternative port to use, this will copy settings from 445/SMB')
    parser.add_argument('protocol', choices=PSEXEC.KNOWN_PROTOCOLS.keys(),
                        nargs='?', default='445/SMB',
                        help='transport protocol (default 445/SMB)')

    group = parser.add_argument_group('authentication')

    group.add_argument('-hashes', action="store", metavar="LMHASH:NTHASH",
                       help='NTLM hashes, format is LMHASH:NTHASH')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    options = parser.parse_args()

    domain, username, password, address = re.compile(
        '(?:(?:([^/@:]*)/)?([^@:]*)(?::([^.]*))?@)?(.*)'
        ).match(options.target).groups('')

    if domain is None:
        domain = ''

    if options.port:
        options.protocol = "%s/SMB" % options.port

    executer = PSEXEC(options.command, options.path, options.file,
                      options.protocol, username, password, domain,
                      options.hashes)

    if options.protocol not in PSEXEC.KNOWN_PROTOCOLS:
        connection_string = 'ncacn_np:%s[\\pipe\\svcctl]'
        PSEXEC.KNOWN_PROTOCOLS[options.protocol] = (connection_string,
                                                    options.port)

    executer.run(address)

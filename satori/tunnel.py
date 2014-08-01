#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""SSH tunneling module.

Set up a forward tunnel across an SSH server, using paramiko. A local port
(given with -p) is forwarded across an SSH session to an address:port from
the SSH server. This is similar to the openssh -L option.
"""
try:
    import eventlet
    eventlet.monkey_patch()
    from eventlet.green import threading
    from eventlet.green import time
except ImportError:
    import threading
    import time
    pass

import logging
import select
import socket
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

import paramiko

LOG = logging.getLogger(__name__)


class TunnelServer(SocketServer.ThreadingTCPServer):

    """Serve on a local ephemeral port.

    Clients will connect to that port/server.
    """

    daemon_threads = True
    allow_reuse_address = True


class TunnelHandler(SocketServer.BaseRequestHandler):

    """Handle forwarding of packets."""

    def handle(self):
        """Do all the work required to service a request.

        The request is available as self.request, the client address as
        self.client_address, and the server instance as self.server, in
        case it needs to access per-server information.

        This implementation will forward packets.
        """
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   self.target_address,
                                                   self.request.getpeername())
        except Exception as exc:
            LOG.error('Incoming request to %s:%s failed',
                      self.target_address[0],
                      self.target_address[1],
                      exc_info=exc)
            return
        if chan is None:
            LOG.error('Incoming request to %s:%s was rejected '
                      'by the SSH server.',
                      self.target_address[0],
                      self.target_address[1])
            return

        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        try:
            peername = None
            peername = str(self.request.getpeername())
        except socket.error as exc:
            LOG.warning("Couldn't fetch peername.", exc_info=exc)
        chan.close()
        self.request.close()
        LOG.info("Tunnel closed from '%s'", peername or 'unnamed peer')


class Tunnel(object):  # pylint: disable=R0902

    """Create a TCP server which will use TunnelHandler."""

    def __init__(self, target_host, target_port,
                 sshclient, tunnel_host='localhost',
                 tunnel_port=0):
        """Constructor."""
        if not isinstance(sshclient, paramiko.SSHClient):
            raise TypeError("'sshclient' must be an instance of "
                            "paramiko.SSHClient.")

        self.target_host = target_host
        self.target_port = target_port
        self.target_address = (target_host, target_port)
        self.address = (tunnel_host, tunnel_port)

        self._tunnel = None
        self._tunnel_thread = None
        self.sshclient = sshclient
        self._ssh_transport = self.get_sshclient_transport(
            self.sshclient)

        TunnelHandler.target_address = self.target_address
        TunnelHandler.ssh_transport = self._ssh_transport

        self._tunnel = TunnelServer(self.address, TunnelHandler)
        # reset attribute to the port it has actually been set to
        self.address = self._tunnel.server_address
        tunnel_host, self.tunnel_port = self.address

    def get_sshclient_transport(self, sshclient):
        """Get the sshclient's transport.

        Connect the sshclient, that has been passed in and return its
        transport.
        """
        sshclient.connect()
        return sshclient.get_transport()

    def serve_forever(self, async=True):
        """Serve the tunnel forever.

        if async is True, this will be done in a background thread
        """
        if not async:
            self._tunnel.serve_forever()
        else:
            self._tunnel_thread = threading.Thread(
                target=self._tunnel.serve_forever)
            self._tunnel_thread.start()
            # cooperative yield
            time.sleep(0)

    def shutdown(self):
        """Stop serving the tunnel.

        Also close the socket.
        """
        self._tunnel.shutdown()
        self._tunnel.socket.close()

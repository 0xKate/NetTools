"""
MIT License

Copyright (c) 2021 0xKate

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import contextlib
from multiprocessing.pool import ThreadPool
from socket import gethostbyaddr, AF_INET6, AF_INET, SOCK_DGRAM, SOCK_STREAM
from typing import Dict, Tuple, List, ValuesView, Union
from datetime import datetime


import psutil
from scapy.arch import get_if_addr
from scapy.config import conf
from scapy.layers.inet import TCP, UDP, IP
from scapy.sendrecv import AsyncSniffer

import Enums
from Enums import PROTO
from Model.HostData import HostData

PROTO_MAP = {
    (AF_INET, SOCK_STREAM): PROTO.TCP.value,
    (AF_INET, SOCK_DGRAM): PROTO.UDP.value,
}
PROTO_MAP6 = {
    (AF_INET6, SOCK_STREAM): 'TCP6',
    (AF_INET6, SOCK_DGRAM): 'UDP6',
}

class NetToolsData:
    __slots__ = ["Sniffing", "BackgroundThreads", "ReverseResolver", "Connections", "SnifferEvent", "LocalIP", "loop", "ListAllSockets"]
    def __init__(self):
        self.Sniffing = False
        self.BackgroundThreads = 0
        self.ReverseResolver = False
        self.Connections = {} #type: Dict[Tuple[str, int, int], HostData]
        self.SnifferEvent = asyncio.Event()
        self.LocalIP = get_if_addr(conf.iface)
        self.loop = asyncio.get_running_loop()
        self.ListAllSockets = psutil.net_connections(kind='inet4')

    ## - Helper Functions - ##
    def _FindTrafficSocketData(self, signature: Tuple[str, int, int], update=False) -> Union[Tuple[int, str, int ],None]:
        """
        _FindTrafficSocketData(signature) -> ()\n
        :param signature: The connection signature of (str(IP), int(port), int(ENUM(PROTO)))
        :param update: True if you want to skip checking the cache first.
        :return: A tuple of (PID, CONN_STATUS, FILE_DESCRIPTOR)
        """
        if update:
            self.ListAllSockets = psutil.net_connections(kind='inet4')
        _dict = {(x.raddr[0], x.raddr[1], PROTO_MAP[(x.family, x.type)]): (x.pid, x.status, x.fd) for x in self.ListAllSockets if len(x.raddr) == 2}
        if signature not in _dict:
            if update is False:
                return self._FindTrafficSocketData(signature, update=True)
            else:
                return None
        else:
            return _dict[signature]

    async def _GetHostByAddrAsync(self, ip):
        """
        GetHostFromAddr(ip) -> fqdn\n
        :param ip: The hosts ip address ie. 192.168.1.1
        :return: Return the fqdn (a string of the form 'sub.example.com') for a host.
        """
        self.BackgroundThreads += 1
        loop = asyncio.get_running_loop()
        event = asyncio.Event()
        pool = ThreadPool(processes=1)

        thread_result = pool.apply_async(gethostbyaddr, (ip,), callback=lambda x: loop.call_soon_threadsafe(event.set))

        with contextlib.suppress(asyncio.TimeoutError):
            if await asyncio.wait_for(event.wait(), 5):
                result = thread_result.get()[0]
            event.clear()
            pool.close()
            pool.terminate()
            self.BackgroundThreads -= 1
            return result

    ## - Backend Data Manipulation - ##

    async def _BGSniffer(self):
        _SnifferTask = AsyncSniffer(iface=conf.iface, prn=self._PacketCB, store=0, filter="tcp or udp and not host 127.0.0.1")
        _SnifferTask.start()
        self.Sniffing = True
        await self.SnifferEvent.wait()
        if _SnifferTask.running:
            _SnifferTask.stop()
        self.Sniffing = False
        self.SnifferEvent.clear()

    async def _UpdateConnectionData(self, conn_signature: Tuple[str, int, int],
                                remote_host, local_host,
                                conn_type, conn_direction, pkt_size):
        if conn_signature in self.Connections:
            self.Connections[conn_signature].IncrementCount(conn_direction, pkt_size)
            time_delta = datetime.now() - self.Connections[conn_signature].LastSeen
            if time_delta.total_seconds() / 60 > 60:
                socket_data = self._FindTrafficSocketData(conn_signature)
                self.Connections[conn_signature].SetSocketData(socket_data)
            self.Connections[conn_signature].SetLastSeen(datetime.now())
        else:
            socket_data = self._FindTrafficSocketData(conn_signature)
            data = HostData(*local_host, *remote_host, remote_host[0], conn_type, socket_data)
            self.Connections[conn_signature] = data
            self.Connections[conn_signature].IncrementCount(conn_direction, pkt_size)
            hostname = await self._GetHostByAddrAsync(conn_signature[0])
            if hostname:
                self.Connections[conn_signature].SetRemoteHostname(hostname)

    def _PacketCB(self, pkt: IP):
        proto = None
        direction = None
        remote_socket = None
        local_socket = None
        if IP in pkt:
            if TCP in pkt:
                proto = PROTO.TCP
                if pkt[IP].dst == self.LocalIP:
                    direction = 'Incoming'
                    remote_socket = (pkt[IP].src, int(pkt[TCP].sport))
                    local_socket = (self.LocalIP, int(pkt[TCP].dport))
                elif pkt[IP].src == self.LocalIP:
                    direction = 'Outgoing'
                    remote_socket = (pkt[IP].dst, int(pkt[TCP].dport))
                    local_socket = (self.LocalIP, int(pkt[TCP].sport))
            elif UDP in pkt:
                proto = PROTO.UDP
                if pkt[IP].dst == self.LocalIP:
                    direction = 'Incoming'
                    remote_socket = (pkt[IP].src, int(pkt[UDP].sport))
                    local_socket = (self.LocalIP, int(pkt[UDP].dport))
                elif pkt[IP].src == self.LocalIP:
                    direction = 'Outgoing'
                    remote_socket = (pkt[IP].dst, int(pkt[UDP].dport))
                    local_socket = (self.LocalIP, int(pkt[UDP].sport))
            if proto is not None\
                    and direction is not None \
                    and remote_socket is not None\
                    and local_socket is not None:
                conn_signature = (str(remote_socket[0]), int(remote_socket[1]), int(proto.value))
                self.loop.create_task(self._UpdateConnectionData(conn_signature, remote_socket, local_socket,
                                                             proto.name, direction, len(pkt)))

    ## - M.U.D - ##

    def SniffStop(self):
        if self.Sniffing:
            self.SnifferEvent.set()

    def SniffStart(self):
        if not self.Sniffing:
            self.loop.create_task(self._BGSniffer())

    def SetConnectionsDict(self, new_dict):
        self.Connections = new_dict

    def GetConnectionsDict(self):
        return self.Connections

    def GetAllConnections(self) -> ValuesView[HostData,  dict[tuple[str, int, int], HostData]]:
        return self.Connections.values()

    def GetNumBGThreads(self):
        return self.BackgroundThreads
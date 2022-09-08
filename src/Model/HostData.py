"""
MIT License

Copyright (c) 2022 0xKate

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

from datetime import datetime

import psutil


class HostData:
    __slots__ = ['FirstSeen','LastSeen','ProtoType','PacketCount','IncomingCount','OutgoingCount',
                 'BandwidthUsage','UploadUsage','DownloadUsage','LocalPort','LocalIP','RemotePort',
                 'RemoteIP','RemoteHostname','SocketData', 'ProcessName']

    def __init__(self, LocalIP, LocalPort, RemoteIP, RemotePort, RemoteHostname, ProtoType, socket_data):
        self.FirstSeen = datetime.now()
        self.LastSeen = datetime.now()
        self.ProtoType = ProtoType
        self.PacketCount = 0
        self.IncomingCount = 0
        self.OutgoingCount = 0
        self.BandwidthUsage = 0
        self.UploadUsage = 0
        self.DownloadUsage = 0
        self.LocalPort = LocalPort
        self.LocalIP = LocalIP
        self.RemotePort = RemotePort
        self.RemoteIP = RemoteIP
        self.RemoteHostname = RemoteHostname
        self.SocketData = socket_data
        self.ProcessName = None

    def IncrementCount(self, conn_direction, pkt_size):
        self.PacketCount += 1
        self.BandwidthUsage += pkt_size
        if conn_direction == 'Incoming':
            self.IncomingCount += 1
            self.DownloadUsage += pkt_size
        elif conn_direction == 'Outgoing':
            self.OutgoingCount += 1
            self.UploadUsage += pkt_size

    def __str__(self):
        return f'RemoteHost: {self.RemoteHostname}:{self.RemotePort} - ' \
               f'PacketCount: {self.PacketCount} Incoming: {self.IncomingCount} Outgoing: {self.OutgoingCount}'

    def GetProcName(self):
        pid = self.SocketData[0]
        if pid and psutil.pid_exists(pid):
            return psutil.Process(pid).name()
        else:
            return None

    def SetRemoteHostname(self, NewRemoteHostname):
        self.RemoteHostname = NewRemoteHostname

    def GetRemoteEndPoint(self):
        return f'{self.RemoteHostname}:{self.RemotePort}'

    def GetPID(self):
        if self.SocketData and self.SocketData[0]:
            return self.SocketData[0]
        return 0

    def SetLastSeen(self, param):
        self.LastSeen = param

    def SetSocketData(self, socket_data):
        self.SocketData = socket_data

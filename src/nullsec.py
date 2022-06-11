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
import ctypes
import enum
import time
import webbrowser
from multiprocessing.pool import ThreadPool
from socket import gethostbyaddr
from typing import Dict, Tuple
import pyperclip as pc

import pubsub.pub
import wx
from pubsub import pub
from scapy.arch import get_if_addr
from scapy.config import conf
from scapy.layers.inet import TCP, UDP, IP
from scapy.sendrecv import AsyncSniffer
from wx.adv import TaskBarIcon
from wx.grid import Grid
from wxasync import WxAsyncApp, StartCoroutine, AsyncBind

from Enums import EventMsg


class TrayIcon(TaskBarIcon):
    def __init__(self, frame):
        TaskBarIcon.__init__(self)
        self.frame = frame
        self.SetIcon(wx.Icon('assets/GameIcon.bmp'), 'Task bar icon')
        self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=1)
        self.Bind(wx.EVT_MENU, self.OnTaskBarDeactivate, id=2)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=3)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(1, 'Show')
        menu.Append(2, 'Hide')
        menu.Append(3, 'Close')
        return menu

    def OnTaskBarClose(self, event):
        self.frame.Close()

    def OnTaskBarActivate(self, event):
        if not self.frame.IsShown():
            self.frame.Show()

    def OnTaskBarDeactivate(self, event):
        if self.frame.IsShown():
            self.frame.Hide()

class HostData:
    def __init__(self, LocalIP, LocalPort, RemoteIP, RemotePort, RemoteHostname, ProtoType):
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
        return f'RemoteHost: {self.RemoteHostname}:{self.RemotePort} - PacketCount: {self.PacketCount} Incoming: {self.IncomingCount} Outgoing: {self.OutgoingCount}'

    def SetRemoteHostname(self, NewRemoteHostname):
        self.RemoteHostname = NewRemoteHostname

    def GetRemoteEndPoint(self):
        return f'{self.RemoteHostname}:{self.RemotePort}'

background_threads = 0


class PROTO(enum.Enum):
    TCP = 0
    UDP = 1


class Model:
    def __init__(self):
        self.Sniffing = False
        self.BackgroundThreads = 0
        self.ReverseResolver = False
        self.UDPConnections = {} # type: Dict[Tuple[str, int], HostData]
        self.TCPConnections = {} # type: Dict[Tuple[str, int], HostData]
        self.Connections = {} #type: Dict[Tuple[str, int, int], HostData]
        self.SnifferEvent = asyncio.Event()
        self.LocalIP = get_if_addr(conf.iface)
        pubsub.pub.subscribe(self.onSniffUpdate, "0xEVT_SNIFFING")
        pubsub.pub.subscribe(self.onSniffClose, "0xEVT_CLOSING")
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self._Sniffer())

    def GetNumBGThreads(self):
        return self.BackgroundThreads

    async def GetHostFromAddr(self, ip):
        """
        GetHostFromAddr(ip) -> fqdn\n
        :param ip: The hosts ip address ie. 192.168.1.1
        :return: Return the fqdn (a string of the form 'sub.example.com') for a host.
        """
        # print('ThreadOpened')
        self.BackgroundThreads += 1
        loop = asyncio.get_event_loop()
        event = asyncio.Event()
        pool = ThreadPool(processes=1)

        thread_result = pool.apply_async(gethostbyaddr, (ip,), callback=lambda x: loop.call_soon_threadsafe(event.set))

        with contextlib.suppress(asyncio.TimeoutError):
            if await asyncio.wait_for(event.wait(), 5):
                result = thread_result.get()[0]
            event.clear()
            pool.close()
            pool.terminate()
            # print('ThreadClosed')
            self.BackgroundThreads -= 1
            return result

    def GetAllConnections(self):
        #all_conn = self.UDPConnections | self.TCPConnections
        #return all_conn.values()
        return self.Connections.values()

    def DumpConnectionsByPKTCount(self):
        tcp = sorted(self.TCPConnections.values(), key=lambda x: x.PacketCount, reverse=True)
        print("---- TCP ----")
        for i in tcp:
            print(i)
        print("---- UDP ----")
        udp = sorted(self.UDPConnections.values(), key=lambda x: x.PacketCount, reverse=True)
        for i in udp:
            print(i)

    def onSniffUpdate(self, data):
        pass
        #print(f'[{datetime.now()}] {data}')
        #self.DumpConnectionsByPKTCount()

    def onSniffClose(self):
        self.SnifferEvent.set()

    def onSniffStart(self):
        if not self.Sniffing:
            self.loop.create_task(self._Sniffer())

    async def _Sniffer(self):

        # filter=f'host 188.138.40.87 or host 51.178.64.97 or host {WOW_WORLD_SERVER}'
        self.SnifferTask = AsyncSniffer(iface=conf.iface, prn=self._PacketCB, store=0)
        self.SnifferTask.start()
        await self.SnifferEvent.wait()
        if self.SnifferTask.running:
            self.SnifferTask.stop()
        self.SnifferEvent.clear()

    async def ConnectionUpdate_OLD(self, remote_host, local_host, conn_type, conn_direction, pkt_size):
        if conn_type == 'TCP':
            if remote_host in self.TCPConnections:
                self.TCPConnections[remote_host].IncrementCount(conn_direction, pkt_size)
            else:
                self.TCPConnections[remote_host] = HostData(*local_host, *remote_host, remote_host[0])
                self.TCPConnections[remote_host].IncrementCount(conn_direction, pkt_size)
                hostname = await self.GetHostFromAddr(remote_host[0])
                print(hostname)
                if hostname:
                    self.TCPConnections[remote_host].SetRemoteHostname(hostname)
            #print(self.TCPConnections[remote_host])
        elif conn_type == 'UDP':
            if remote_host in self.UDPConnections:
                self.UDPConnections[remote_host].IncrementCount(conn_direction, pkt_size)
            else:
                #remote_hostname = getnameinfo((remote_host[0], 0), 0)
                self.UDPConnections[remote_host] = HostData(*local_host, *remote_host, remote_host[0])
                self.UDPConnections[remote_host].IncrementCount(conn_direction, pkt_size)
                hostname = await self.GetHostFromAddr(remote_host[0])
                print(hostname)
                if hostname:
                    self.UDPConnections[remote_host].SetRemoteHostname(hostname)
            #print(self.UDPConnections[remote_host])

    async def ConnectionUpdate(self, conn_signature: Tuple[str, int, int],
                                remote_host, local_host,
                                conn_type, conn_direction, pkt_size):
        if conn_signature in self.Connections:
            self.Connections[conn_signature].IncrementCount(conn_direction, pkt_size)
        else:
            self.Connections[conn_signature] = HostData(*local_host, *remote_host, remote_host[0], conn_type)
            self.Connections[conn_signature].IncrementCount(conn_direction, pkt_size)
            hostname = await self.GetHostFromAddr(conn_signature[0])
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
            #print(f'{proto} and {direction} and {remote_socket} and {local_socket}')
            if proto is not None\
                    and direction is not None \
                    and remote_socket is not None\
                    and local_socket is not None:
                conn_signature = (str(remote_socket[0]), int(remote_socket[1]), int(proto.value))
                self.loop.create_task(self.ConnectionUpdate(conn_signature, remote_socket, local_socket,
                                                             proto.name, direction, len(pkt)))
            else:
                pass
        else:
            pass

    def _PacketCB_OLD(self, pkt: TCP):
        if IP in pkt:
            if TCP in pkt:
                if pkt[IP].dst == self.LocalIP:
                    remote_host = (pkt[IP].src, int(pkt[TCP].sport))
                    local_host = (self.LocalIP, int(pkt[TCP].dport))
                    #print(f'IN : {self.LocalIP}:{pkt[TCP].dport} <-- {pkt[IP].src}:{pkt[TCP].sport}')
                    self.loop.create_task(self.ConnectionUpdate(remote_host, local_host, 'TCP', 'Incoming', len(pkt)))
                elif pkt[IP].src == self.LocalIP:
                    remote_host = (pkt[IP].dst, int(pkt[TCP].dport))
                    local_host = (self.LocalIP, int(pkt[TCP].sport))
                    #print(f'OUT: {self.LocalIP}:{pkt[TCP].sport} --> {pkt[IP].dst}:{pkt[TCP].dport}')
                    self.loop.create_task(self.ConnectionUpdate(remote_host, local_host, 'TCP', 'Outgoing', len(pkt)))

                #pkt[TCP].show()
            elif UDP in pkt:
                if pkt[IP].dst == self.LocalIP:
                    remote_host = (pkt[IP].src, int(pkt[UDP].sport))
                    local_host = (self.LocalIP, int(pkt[UDP].dport))
                    #print(f'IN : {self.LocalIP}:{pkt[UDP].dport} <-- {pkt[IP].src}:{pkt[UDP].sport}')
                    self.loop.create_task(self.ConnectionUpdate(remote_host, local_host, 'UDP', 'Incoming', len(pkt)))
                elif pkt[IP].src == self.LocalIP:
                    remote_host = (pkt[IP].dst, int(pkt[UDP].dport))
                    local_host = (self.LocalIP, int(pkt[UDP].sport))
                    #print(f'OUT: {self.LocalIP}:{pkt[UDP].sport} --> {pkt[IP].dst}:{pkt[UDP].dport}')
                    self.loop.create_task(self.ConnectionUpdate(remote_host, local_host, 'UDP', 'Outgoing', len(pkt)))
                #pkt[UDP].show()
            else:
                pass

class View(wx.Frame):
    def __init__(self, model: Model, *args, **kwds):
        """
        The applications View
        """
        # Core
        self.Model = model
        # Initialize Frame
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        # Icon
        _Icon = wx.Icon('assets/GameIcon.bmp')
        self.SetIcon(_Icon)
        # Menu Bar
        self._MenuBar = wx.MenuBar()
        self._MenuBarMenu = wx.Menu()
        self._MenuBar.Quit_Button = self._MenuBarMenu.Append(wx.NewId(), "Quit", "Exits the application.")
        self.Bind(wx.EVT_MENU, lambda x: pub.sendMessage(EventMsg.ExitGame.value), self._MenuBar.Quit_Button)
        self._MenuBar.Append(self._MenuBarMenu, "File")
        self.SetMenuBar(self._MenuBar)

        # Status Bar
        self._StatusBar = self.CreateStatusBar(2)
        self._StatusBar.SetStatusWidths([-1, 75])
        self._StatusBar.SetStatusText("", 0)
        self._StatusBar.SetStatusText("", 1)
        self.SetStatusBar(self._StatusBar)

        # System Tray
        self.SystemTray = TrayIcon(self)

        # Panels
        self.MainPanel = wx.Panel(self, wx.ID_ANY)
        self.ListPanel = wx.Panel(self.MainPanel, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.ContentPanel = wx.Panel(self.MainPanel, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.ViewPanel = wx.ScrolledWindow(self.ContentPanel, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.ViewPanel.SetScrollRate(10, 10)
        self.ButtonPanel = wx.Panel(self.ContentPanel, wx.ID_ANY, style=wx.BORDER_RAISED)

        # Widgets
        self.TestButton_1 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 1")
        self.TestButton_2 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 2")
        self.TestButton_3 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 3")
        self.TestButton_4 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 4")
        self.ViewGrid = Grid(self.ViewPanel, wx.ID_ANY, size=(1, 1))

        # Layout
        self.__set_properties()
        self.__do_layout()

        # Bindings
        self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_1, id=1)
        self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_2, id=2)
        self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_3, id=3)
        self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_4, id=4)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.grid.EVT_GRID_CMD_CELL_RIGHT_CLICK, self.GridRightClickHandler, source=self.ViewGrid)
        StartCoroutine(self.update_clock, self)

        pubsub.pub.subscribe(self.onSniffUpdate, "0xEVT_SNIFFING")


    def __set_properties(self):
        self.SetSize((1006, 693))
        self.SetTitle("Networking Tools")
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        r=len(self.Model.GetAllConnections())
        # This is to create the grid with same rows as database.
        self.ViewGrid.CreateGrid(r, 7)
        self.ViewGrid.SetColLabelValue(0, "Connection")
        self.ViewGrid.SetColSize(0, 300)
        self.ViewGrid.SetColLabelValue(1, "IP")
        self.ViewGrid.SetColSize(1, 125)
        self.ViewGrid.SetColLabelValue(2, "Proto")
        self.ViewGrid.SetColSize(2, 75)
        self.ViewGrid.SetColLabelValue(3, "Packets")
        self.ViewGrid.SetColSize(3, 75)
        self.ViewGrid.SetColLabelValue(4, "In")
        self.ViewGrid.SetColSize(4, 50)
        self.ViewGrid.SetColLabelValue(5, "Out")
        self.ViewGrid.SetColSize(5, 50)
        self.ViewGrid.SetColLabelValue(6, "Bandwidth")
        self.ViewGrid.SetColSize(6, 75)

        self.refresh_data()

    def __do_layout(self):
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        self.MainSizer.Add(self.MainPanel, 1, wx.EXPAND, 0)
        self.SubSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SubSizer.Add(self.ContentPanel, 3, wx.EXPAND, 0)
        self.ContentSizer = wx.BoxSizer(wx.VERTICAL)
        self.ContentSizer.Add(self.ViewPanel, 10, wx.EXPAND, 0)
        self.ViewSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ViewSizer.Add(self.ViewGrid, 1, wx.EXPAND, 0)
        self.ContentSizer.Add(self.ButtonPanel, 1, wx.EXPAND, 0)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonSizer.Add(self.TestButton_1, 1, wx.EXPAND, 0)
        self.ButtonSizer.Add(self.TestButton_2, 1, wx.EXPAND, 0)
        self.ButtonSizer.Add(self.TestButton_3, 1, wx.EXPAND, 0)
        self.ButtonSizer.Add(self.TestButton_4, 1, wx.EXPAND, 0)
        self.ButtonPanel.SetSizer(self.ButtonSizer)
        self.ViewPanel.SetSizer(self.ViewSizer)
        self.ContentPanel.SetSizer(self.ContentSizer)
        self.MainPanel.SetSizer(self.SubSizer)
        self.SetSizer(self.MainSizer)
        self.Layout()

    def onSniffUpdate(self, data):
        self.refresh_data()

    def refresh_data(self):
        self.SortBy = 'PacketCount'
        all_conn = sorted(self.Model.GetAllConnections(), key=lambda x: x.PacketCount, reverse=True)
        for row in range (0, len(all_conn)):
            host = all_conn[row]
            #print(f'Row: {row} < Rows: {self.ViewGrid.GetNumberRows()}')
            if not row < self.ViewGrid.GetNumberRows():
                self.ViewGrid.AppendRows(1, False)
            self.ViewGrid.SetCellValue(row, 0, str(host.GetRemoteEndPoint()))
            self.ViewGrid.SetCellValue(row, 1, str(host.RemoteIP))
            self.ViewGrid.SetCellValue(row, 2, str(host.ProtoType))
            self.ViewGrid.SetCellValue(row, 3, str(host.PacketCount))
            self.ViewGrid.SetCellValue(row, 4, str(host.IncomingCount))
            self.ViewGrid.SetCellValue(row, 5, str(host.OutgoingCount))
            self.ViewGrid.SetCellValue(row, 6, str(host.BandwidthUsage))



    async def update_clock(self):
        """ StatusBar Coroutine: Updates the clocks time."""
        while True:
            self.StatusBar.SetStatusText(time.strftime('%I:%M:%S %p'), 1)
            await asyncio.sleep(0.5)

    def OnClose(self, event):
        pubsub.pub.sendMessage("0xEVT_Closing")
        self.SystemTray.Destroy()
        self.Destroy()

    def TestButtonCB(self, event: wx.CommandEvent):
        print(f"Button Callback! - {event.GetId()} - {event.GetEventType()} - {event.GetTimestamp()}")
        print(event.GetClientData())


    def onCopy(self, event: wx.CommandEvent, cell_context):
        cell_value = self.ViewGrid.GetCellValue(*cell_context)
        pc.copy(cell_value)

    def onOpenIPInfo(self, event: wx.CommandEvent, cell_context):
        cell_value = self.ViewGrid.GetCellValue(*cell_context)
        url = f'https://ipinfo.io/{cell_value}'
        webbrowser.open(url)

    def GridRightClickHandler(self, event: wx.grid.GridEvent):
        row = event.GetRow()
        col = event.GetCol()

        _Menu = wx.Menu()

        _Item1 = wx.MenuItem(_Menu, wx.NewId(), 'Copy')
        _Menu.Append(_Item1)
        _Menu.Bind(wx.EVT_MENU, lambda e: self.onCopy(e, (row, col)), _Item1)

        if col == 1:
            _Item2 = wx.MenuItem(_Menu, wx.NewId(), 'Open Ipinfo.io')
            _Menu.Append(_Item2)
            _Menu.Bind(wx.EVT_MENU, lambda e: self.onOpenIPInfo(e, (row, col)), _Item2)

        self.PopupMenu(_Menu, event.GetPosition())
        event.Skip()

class Controller:
    def __init__(self):
        self.Model = Model()
        self.View = View(self.Model, None, wx.ID_ANY, "")
        self.View.Show()
        StartCoroutine(self.sniffer, self.View)

    async def sniffer(self):
        while True:
            pubsub.pub.sendMessage("0xEVT_SNIFFING", data="Sniffing...")
            await asyncio.sleep(5)

class NullsecApp(WxAsyncApp):
    """ Main WxAsync Application """
    Version = 0.01

    def __init__(self):
        WxAsyncApp.__init__(self, 0)
        pubsub.pub.subscribe(self._Exit, EventMsg.Exit.value)
    def OnInit(self):
        """ Windows 10 Icon Fix """
        app_id = f'0xStudios.RPGMagnate.RPGMagnate.{self.Version}'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(True)
        except:
            pass
        return True

    async def _Start(self):
        """ Blends the wxPython and asyncio event loops. """
        _C = Controller()
        await self.MainLoop()
        print('WxAsyncLoop Ended')

    def StartLoop(self):
        asyncio.run(self._Start())
        print('asyncio.run() Ended')

    def _Exit(self):
        """ Save & Quit the application """
        pass

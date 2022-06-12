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
import time
import webbrowser
import pyperclip as pc

import pubsub.pub
import wx
from pubsub import pub
from wx.grid import Grid
from wxasync import StartCoroutine

from Enums import EventMsg
from UI.TrayIcon import TrayIcon
from NetToolsApp import NetToolsData



class MainWindow(wx.Frame):
    def __init__(self, _NetToolsData: NetToolsData, *args, **kwds):
        """
        The applications View
        """
        self.Data = _NetToolsData
        self.RefreshRate = 2.5
        # Initialize Frame
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        # Icon
        _Icon = wx.Icon('assets/GameIcon.bmp')
        self.SetIcon(_Icon)
        # Menu Bar
        self._MenuBar = wx.MenuBar()

        # File Menu
        self._FileMenu = wx.Menu()
        # File Menu - Quit Button
        self._MenuBar.Quit_Button = self._FileMenu.Append(wx.NewId(), "Quit", "Exits the application.")
        # File Menu - Quit Button Callback
        self.Bind(wx.EVT_MENU, lambda x: pub.sendMessage(EventMsg.ExitGame.value), self._MenuBar.Quit_Button)
        # File Menu - Add to Menubar
        self._MenuBar.Append(self._FileMenu, "File")
        # End File Menu

        # Sniffer Menu
        self._SniferMenu = wx.Menu()
        # Sniffer Menu - Start Sniffer Button
        self._MenuBar.StartSniff_Button = self._SniferMenu.Append(wx.NewId(), "Start Sniffer", "Start the background sniffer task.")
        # Sniffer Menu - Start Sniffer Button Callback
        self.Bind(wx.EVT_MENU, self.StartSniffingCB, self._MenuBar.StartSniff_Button)
        # Sniffer Menu - Stop Sniffer Button
        self._MenuBar.StopSniff_Button = self._SniferMenu.Append(wx.NewId(), "Stop Sniffer", "Stop the background sniffer task.")
        # Sniffer Menu - Stop Sniffer Button Callback
        self.Bind(wx.EVT_MENU, self.StopSniffingCB, self._MenuBar.StopSniff_Button)
        # Sniffer Menu - Add to Menubar
        self._MenuBar.Append(self._SniferMenu, "Sniffer")
        # End # Sniffer Menu

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
        StartCoroutine(self.update_data, self)

    def __set_properties(self):
        self.SetSize((1006, 693))
        self.SetTitle("Networking Tools")
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        r=len(self.Data.GetAllConnections())
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

    def UpdateCell(self, row, col, value):
        self.ViewGrid.SetCellValue(row, col, value)

    def refresh_data(self):
        self.SortBy = 'PacketCount'
        all_conn = sorted(self.Data.GetAllConnections(), key=lambda x: x.PacketCount, reverse=True)
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

    async def update_data(self):
        while True:
            if self.IsShown():
                self.refresh_data()
            await asyncio.sleep(self.RefreshRate)

    async def update_clock(self):
        """ StatusBar Coroutine: Updates the clocks time."""
        while True:
            if self.IsShown():
                self.GetStatusBar().SetStatusText(time.strftime('%I:%M:%S %p'), 1)
            await asyncio.sleep(0.5)

    def OnClose(self, event):
        pubsub.pub.sendMessage("0xEVT_Closing")
        self.SystemTray.Destroy()
        self.Destroy()

    def StopSniffingCB(self, event: wx.CommandEvent):
        self.Data.SniffStop()

    def StartSniffingCB(self, event: wx.CommandEvent):
        self.Data.SniffStart()

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
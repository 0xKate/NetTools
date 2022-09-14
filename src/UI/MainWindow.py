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

# Traffic[process][connection_dict_key]

import asyncio
import time

import wx
from pubsub import pub
from wxasync import StartCoroutine

from Enums import EventMsg
from Model.SaveFileAsync import SaveFileAsync
from Model.NetworkSniffer import NetworkSniffer
from UI.TrayIcon import TrayIcon
from UI.Widgets.ConnectionsDataGrid import ConnectionsDataGridContainer


class MainWindow(wx.Frame):
    """The main wx.Frame/Window of the program. Holds all panels, sizers, widgets, etc..."""
    def __init__(self, _NetToolsData: NetworkSniffer, *args, **kwds):
        # Model
        self.Data = _NetToolsData

        # Initialize Frame
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # Icon
        _Icon = wx.Icon('assets/icon.png')
        self.SetIcon(_Icon)

        # Menu Bar
        self._MenuBar = wx.MenuBar()

        # File Menu
        self._FileMenu = wx.Menu()
        self.Quit_Button = self._FileMenu.Append(wx.NewId(), "Quit", "Exits the application.") # type: wx.MenuItem
        self.Bind(wx.EVT_MENU, lambda x: pub.sendMessage(EventMsg.Exit.value), self.Quit_Button)
        self.SaveAsNTD_Button = self._FileMenu.Append(
            wx.NewId(), "Save as NTD", "Save the current table of connections "
                                       "to a loadable file format") # type: wx.MenuItem
        self.Bind(wx.EVT_MENU, lambda x: self.SaveFileCB(x, 'ntd'), self.SaveAsNTD_Button)
        self.SaveAsText_Button = self._FileMenu.Append(
            wx.NewId(), "Save as Text", "Save the current table of connections "
                                        "in a human readable format. (CANNOT BE LOADED)") # type: wx.MenuItem
        self.Bind(wx.EVT_MENU, lambda x: self.SaveFileCB(x, 'txt'), self.SaveAsText_Button)
        self._MenuBar.Append(self._FileMenu, "File")
        # End File Menu

        # Sniffer Menu
        self._SnifferMenu = wx.Menu()
        # Sniffer Menu - Start Sniffer Button
        self.StartSniff_Button = self._SnifferMenu.Append(
            wx.NewId(), "Start Sniffer", "Start the background sniffer task.") # type: wx.MenuItem
        self.Bind(wx.EVT_MENU, self.StartSniffingCB, self.StartSniff_Button)
        # Sniffer Menu - Stop Sniffer Button
        self.StopSniff_Button = self._SnifferMenu.Append(
            wx.NewId(), "Stop Sniffer", "Stop the background sniffer task.") # type: wx.MenuItem
        self.StopSniff_Button.Enable(False)
        self.Bind(wx.EVT_MENU, self.StopSniffingCB, self.StopSniff_Button)
        # Sniffer Menu - Add to MenuBar
        self._MenuBar.Append(self._SnifferMenu, "Sniffer")

        # Sniffer Options Submenu
        self._OptionsSubMenu = wx.Menu()
        self.AutoRefreshToggle_Button = self._OptionsSubMenu.AppendCheckItem(
            wx.NewId(), "Auto Refresh", "Toggle Auto Refresh") # type: wx.MenuItem
        self.AutoRefreshToggle_Button.Check()
        self.Bind(wx.EVT_MENU, self.AutoRefreshToggleCB, self.AutoRefreshToggle_Button)
        self._SnifferMenu.Append(wx.ID_ANY, 'Options', self._OptionsSubMenu)
        # End Sniffer Menu

        self.SetMenuBar(self._MenuBar)
        # End Menu Bar

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
        #self.ButtonPanel = wx.Panel(self.ContentPanel, wx.ID_ANY, style=wx.BORDER_RAISED)

        # Widgets
        #self.TestButton_1 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 1")
        #self.TestButton_2 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 2")
        #self.TestButton_3 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 3")
        #elf.TestButton_4 = wx.Button(self.ButtonPanel, wx.ID_ANY, "Test Button 4")

        # Custom UI Containers
        self.ConnectionsDataGridContainer = ConnectionsDataGridContainer(self.ContentPanel, self.Data, wx.ID_ANY,
                                                                         style=wx.BORDER_RAISED)
        # Layout
        self.__set_properties()
        self.__do_layout()

        # Bindings
        #self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_1, id=1)
        #self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_2, id=2)
        #self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_3, id=3)
        #self.Bind(wx.EVT_BUTTON, self.TestButtonCB, source=self.TestButton_4, id=4)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        StartCoroutine(self.UpdateClockLoopAsync, self)

    def __set_properties(self):
        self.SetSize((1280, 1024))
        self.SetTitle("Networking Tools")
        self.SetBackgroundColour(wx.Colour(255, 255, 255))

    def __do_layout(self):
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        self.MainSizer.Add(self.MainPanel, 1, wx.EXPAND, 0)
        self.SubSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SubSizer.Add(self.ContentPanel, 3, wx.EXPAND, 0)
        self.ContentSizer = wx.BoxSizer(wx.VERTICAL)
        self.ContentSizer.Add(self.ConnectionsDataGridContainer, 10, wx.EXPAND, 0)
        self.ViewSizer = wx.BoxSizer(wx.HORIZONTAL)
        #self.ContentSizer.Add(self.ButtonPanel, 1, wx.EXPAND, 0)
        #self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        #self.ButtonSizer.Add(self.TestButton_1, 1, wx.EXPAND, 0)
        #self.ButtonSizer.Add(self.TestButton_2, 1, wx.EXPAND, 0)
        #self.ButtonSizer.Add(self.TestButton_3, 1, wx.EXPAND, 0)
        #self.ButtonSizer.Add(self.TestButton_4, 1, wx.EXPAND, 0)
        #self.ButtonPanel.SetSizer(self.ButtonSizer)
        self.ContentPanel.SetSizer(self.ContentSizer)
        self.MainPanel.SetSizer(self.SubSizer)
        self.SetSizer(self.MainSizer)
        self.Layout()

    async def UpdateClockLoopAsync(self):
        """ StatusBar Coroutine: Updates the clocks time."""
        while True:
            if self.IsShown():
                self.GetStatusBar().SetStatusText(time.strftime('%I:%M:%S %p'), 1)
            await asyncio.sleep(0.5)

    def OnClose(self, _event):
        """ On Window close event handler"""
        self.SystemTray.Destroy()
        self.Destroy()
        pub.sendMessage(EventMsg.Exit.value)

    def StopSniffingCB(self, _event: wx.CommandEvent):
        """MenuBar -> Sniffer -> Stop Sniffing: Callback to stop background sniffer"""
        if self.Data.GetSnifferStatus():
            self.StopSniff_Button.Enable(False)
            self.StartSniff_Button.Enable(True)
            self.Data.SniffStop()

    def StartSniffingCB(self, _event: wx.CommandEvent):
        """MenuBar -> Sniffer -> Stop Sniffing: Callback to start background sniffer"""
        if not self.Data.GetSnifferStatus():
            self.StopSniff_Button.Enable(True)
            self.StartSniff_Button.Enable(False)
            self.Data.SniffStart()

    @staticmethod
    def TestButtonCB(event: wx.CommandEvent):
        """Placeholder Button Callback"""
        print(f"Button Callback! - {event.GetId()} - {event.GetEventType()} - {event.GetTimestamp()}")
        print(event.GetClientData())

    def AutoRefreshToggleCB(self, _event):
        """MenuBar -> Sniffer -> Options -> Autorefresh callback"""
        self.ConnectionsDataGridContainer.AutoRefresh = self.AutoRefreshToggle_Button.IsChecked()

    def SaveFileCB(self, _event, filetype: str):
        """Called by save as dialog, pass a supported filetype via lambda"""
        with wx.FileDialog(self, f"Save {filetype.upper()} file",
                           wildcard=f"{filetype.upper()} files (*.{filetype.lower()})|*.{filetype.lower()}",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
        data = self.Data.GetConnectionsDict()
        SaveFileAsync(data, pathname, filetype)
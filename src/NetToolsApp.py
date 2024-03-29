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

import asyncio
import ctypes
import sys

import pubsub.pub
import wx
from wxasync import WxAsyncApp
from Enums import EventMsg
from Model.NetworkSniffer import NetworkSniffer
from UI.MainWindow import MainWindow


class WxAsyncEngine(WxAsyncApp):
    """ Main WxAsync Application """
    Version = 0.02

    def __init__(self):
        WxAsyncApp.__init__(self, 0)
        pubsub.pub.subscribe(self._Exit, EventMsg.Exit.value)
        self.App = None

    def OnInit(self):
        """ Windows 10 Icon Fix """
        app_id = f'0xStudios.NullSec.NetTools.{self.Version}'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(True)
        except:
            pass
        return True

    async def _StartAsync(self):
        """ Blends the wxPython and asyncio event loops. """
        self.NetToolsData = NetworkSniffer()
        self.MainWindow = MainWindow(self.NetToolsData, None, wx.ID_ANY, "")
        self.MainWindow.Show()
        await self.MainLoop()

    def Start(self):
        """Use the main thread to run our main event loop (ie. GoldenThread)"""
        try:
            asyncio.run(self._StartAsync())
        except BaseException as ex:
            print(f"Caught exception in main event loop, shutting down. : {ex}")
            sys.exit(-1)

    def _Exit(self):
        """ Save & Quit the application """
        self.ExitMainLoop()

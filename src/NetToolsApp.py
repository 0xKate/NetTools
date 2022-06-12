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
import ctypes
import pubsub.pub
import wx
from wxasync import WxAsyncApp
from Enums import EventMsg
from Model.NetToolsData import NetToolsData
from UI.MainWindow import MainWindow

class NetToolsApp:
    def __init__(self):
        self.NetToolsData = NetToolsData()
        self.MainWindow = MainWindow(self.NetToolsData, None, wx.ID_ANY, "")

    def Render(self):
        self.MainWindow.Show()


class WxAsyncEngine(WxAsyncApp):
    """ Main WxAsync Application """
    Version = 0.02

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
        App = NetToolsApp()
        App.Render()
        await self.MainLoop()
        print('WxAsyncLoop Ended')

    def StartLoop(self):
        asyncio.run(self._Start())
        print('asyncio.run() Ended')

    def _Exit(self):
        """ Save & Quit the application """
        pass
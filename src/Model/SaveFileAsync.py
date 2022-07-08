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

import bz2
import pickle
import threading
import time
from typing import Union, Dict, Tuple, List

import wx

from Model.HostData import HostData


class SaveFileAsync(threading.Thread):
    """Take data and write it to disk in a background thread as to not halt the main event loop."""
    def __init__(self, data: Union[Dict[Tuple[str, int, int], HostData], List[HostData]], pathname, filetype):
        """Creating an instance of this class will execute the run function immediately in the background thread.
        :param data: Either the main Connections Dictionary or a View from .items()
        :param pathname: Path to the file to write data
        :param filetype: A str of either txt or ntd (NetTools Data)
        """
        threading.Thread.__init__(self)  # Must be invoked first when subclassing a Thread
        self.setName(f'SaveFileAsyncThread')
        self.Data = data
        self.FilePath = pathname
        self.FileType = filetype
        self.start()

    def _SaveAsTXT(self):
        """Save to text file in human readable format."""
        try:
            with open(self.FilePath, 'w') as file:
                for i in self.Data:  # type: HostData
                    file.writelines(
                        f'EndPoint: {i.GetRemoteEndPoint()}\t<-> {i.LocalIP}:{i.LocalPort} {i.ProtoType} -- '
                        f'PKT: {i.PacketCount}\tIN: {i.IncomingCount}\tOUT: {i.OutgoingCount}\t'
                        f'BW: {i.BandwidthUsage}\tIN: {i.DownloadUsage}\tOUT: {i.DownloadUsage}\t'
                        f'PID: {i.GetPID()}\tFIRST: {i.FirstSeen}\tLAST: {i.LastSeen}\n')
        except IOError:
            wx.LogError(f"Cannot save current data as {self.FileType} in file {self.FilePath}.")

    def _SaveAsNTD(self):
        """Save file as bz2 compressed, python pickled, class data."""
        try:
            with bz2.BZ2File(self.FilePath, 'wb') as bz2file:
                pickle.dump(self.Data, bz2file)
        except IOError:
            wx.LogError(f"Cannot save current data as {self.FileType} in file {self.FilePath}.")

    def run(self) -> None:
        """Start background thread. (Is called automatically after class initialized)"""
        if self.FileType.lower() == 'ntd':
            self._SaveAsNTD()
        elif self.FileType.lower() == 'txt':
            self._SaveAsTXT()

        time.sleep(2)
        print("Finished background file write to", self.FilePath)
        return None
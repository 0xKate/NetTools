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
import logging
import webbrowser
from enum import Enum

import wx
from wx.grid import Grid, GridTableBase, GridStringTable
import pyperclip as pc
from wxasync import StartCoroutine

from Model.NetworkSniffer import NetworkSniffer

class SortBy(Enum):
    Packets = 'PacketCount'
    In = 'IncomingCount'
    Out = 'OutgoingCount'
    Bandwidth = 'BandwidthUsage'
    PID = 'GetPID'
    LastSeen = 'LastSeen'
    FirstSeen = 'FirstSeen'

class ConnectionsDataGridContainer(wx.ScrolledWindow):
    """A scrolled window, holding a sizer, holding a DataGrid,
     contains all bindings to update grid based on data source."""
    def __init__(self, parentPanel, dataSource: NetworkSniffer, *args, **kwargs):
        self.SortDescending = True
        self.SortBy = SortBy.Packets
        self.ParentPanel = parentPanel
        self.DataSource = dataSource
        self.AutoRefresh = True
        self.RefreshRate = 1
        self.Refreshing = False
        wx.ScrolledWindow.__init__(self, parentPanel, *args, **kwargs)
        self.SetScrollRate(10, 10)
        self.DataGrid = Grid(self, wx.ID_ANY, size=(1, 1))
        #self.DataGrid.GetGridCursorCoords()
        #self.DataGrid.DisableDragGridSize()
        self.DataGrid.DisableDragRowSize()
        #self.DataGrid.DisableCellEditControl()
        self.DataGrid.EnableEditing(False)
        #self.DataGrid.DisableDragColSize()
        #self.DataGrid.DisableDragColMove()

        self.__set_properties()
        self.__do_layout()
        self.Bind(wx.grid.EVT_GRID_CMD_CELL_RIGHT_CLICK, self.OnDataGridRightClick, source=self.DataGrid)
        self.Bind(wx.grid.EVT_GRID_CMD_LABEL_RIGHT_CLICK, self.OnDataGridLabelRightClick, source=self.DataGrid)
        self.Bind(wx.grid.EVT_GRID_CMD_LABEL_LEFT_CLICK, self.OnDataGridLabelLeftClick, source=self.DataGrid)
        StartCoroutine(self.UpdateDataGridLoopAsync, self)


    async def UpdateDataGridLoopAsync(self):
        """ DataGrid Coroutine: Constantly Updates all cells in the DataGrid"""
        while True:
            if self.AutoRefresh and self.IsShown():
                self.DataGridRefresh()
            await asyncio.sleep(self.RefreshRate)

    def OnDataGridCopyCell(self, event: wx.CommandEvent, cell_context):
        """Copy cell data to clipboard"""
        cell_value = self.DataGrid.GetCellValue(*cell_context)
        pc.copy(cell_value)
        event.Skip()

    def OnDataGridOpenIPInfo(self, event: wx.CommandEvent, cell_context):
        """Open web browser to https://ipinfo.io/<ip_address>"""
        cell_value = self.DataGrid.GetCellValue(*cell_context)
        webbrowser.open(f'https://ipinfo.io/{cell_value}')
        event.Skip()

    def OnDataGridLabelLeftClick(self, event: wx.grid.GridEvent):
        """Handles right click events for labels on self.DataGrid - EVT_GRID_CMD_LABEL_LEFT_CLICK"""
        col = event.GetCol()
        if col > -1:
            label = self.DataGrid.GetColLabelValue(col)
            if label in ['Packets', 'In', 'Out', 'Bandwidth', 'PID', 'Last Seen', 'First Seen']: # type: str
                print('label:', label)
                if self.SortBy is SortBy[label.replace(' ', '')]:
                    if self.SortDescending:
                        self.SortDescending = False
                    else:
                        self.SortDescending = True
                else:
                    self.SortBy = SortBy[label.replace(' ', '')]
                self.DataGridRefresh()
                print(f"Sorting by: {self.SortBy} Descending: {self.SortDescending}")
        event.Skip()

    def OnDataGridHideColumn(self, evt: wx.grid.GridEvent, col, hide=True):
        if hide:
            self.DataGrid.HideCol(col)
            self.DataGrid.ForceRefresh()
        else:
            self.DataGrid.ShowCol(col)
        evt.Skip()

    def OnDataGridLabelRightClick(self, event: wx.grid.GridEvent):
        col = event.GetCol()
        if col > -1:
            label = self.DataGrid.GetColLabelValue(col)  # type: str
            if label in ['Packets', 'In', 'Out', 'Bandwidth', 'PID', 'Last Seen', 'First Seen']:
                print('label:', label)
                menu = wx.Menu()
                hide_col = wx.MenuItem(menu, wx.NewId(), 'Hide Column')
                menu.Append(hide_col)
                menu.Bind(wx.EVT_MENU, lambda e: self.OnDataGridHideColumn(e, col), hide_col)
                self.PopupMenu(menu, event.GetPosition())
        event.Skip()

    def OnDataGridRightClick(self, event: wx.grid.GridEvent):
        """Handles right click events for cells on self.DataGrid - EVT_GRID_CMD_CELL_RIGHT_CLICK"""
        cell = (event.GetRow(), event.GetCol())
        menu = wx.Menu()
        copy_cell = wx.MenuItem(menu, wx.NewId(), 'Copy')
        menu.Append(copy_cell)
        menu.Bind(wx.EVT_MENU, lambda e: self.OnDataGridCopyCell(e, cell), copy_cell)
        # If right click on IP Column offer option to open Ipinfo.ip/<IP>
        if cell[1] == 1:
            open_ipinfo = wx.MenuItem(menu, wx.NewId(), f'Open Ipinfo.io/{self.DataGrid.GetCellValue(*cell)}')
            menu.Append(open_ipinfo)
            menu.Bind(wx.EVT_MENU, lambda e: self.OnDataGridOpenIPInfo(e, cell), open_ipinfo)
        # Cause a Menu to popup on cursors position, bound to MainWindow.
        self.PopupMenu(menu, event.GetPosition())
        event.Skip()

    def DataGridSetCell(self, row, col, value):
        """Update a cell on the DataGrid"""
        self.DataGrid.SetCellValue(row, col, value)

    @staticmethod
    def __GetSortingValue(x, sortBy):
        attr = getattr(x, sortBy.value)
        if callable(attr):
            return attr()
        else:
            return attr

    def DataGridRefresh(self):
        """Update the entire DataGrid"""
        if self.Refreshing:
            logging.warning('Attempted to redraw grid while still drawing!')
            return

        self.Refreshing = True
        all_conn = sorted(self.DataSource.GetAllConnections(), key=lambda x: self.__GetSortingValue(x, self.SortBy), reverse=self.SortDescending)
        tbl = self.DataGrid.GetTable() # type: GridStringTable
        for row in range (0, len(all_conn)):
            host = all_conn[row]
            if not row < tbl.GetNumberRows():
                tbl.AppendRows()
            tbl.SetValue(row, 0, str(host.GetRemoteEndPoint()))
            tbl.SetValue(row, 1, str(host.RemoteIP))
            tbl.SetValue(row, 2, str(host.ProtoType))
            tbl.SetValue(row, 3, str(host.PacketCount))
            tbl.SetValue(row, 4, str(host.IncomingCount))
            tbl.SetValue(row, 5, str(host.OutgoingCount))
            tbl.SetValue(row, 6, str(host.BandwidthUsage))
            tbl.SetValue(row, 7, str(host.GetPID()))
            tbl.SetValue(row, 8, str(host.LastSeen.replace(microsecond=0)))
            tbl.SetValue(row, 9, str(host.FirstSeen.replace(microsecond=0)))
        self.DataGrid.ForceRefresh()
        self.Refreshing = False

    def __do_layout(self):
        self.DataGridSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.DataGridSizer.Add(self.DataGrid, 1, wx.EXPAND, 0)
        self.SetSizer(self.DataGridSizer)

    def __set_properties(self):
        r = len(self.DataSource.GetAllConnections())
        self.DataGrid.CreateGrid(r, 10)
        self.DataGrid.SetColLabelValue(0, "Connection")
        self.DataGrid.SetColSize(0, 300)
        self.DataGrid.SetColLabelValue(1, "IP")
        self.DataGrid.SetColSize(1, 125)
        self.DataGrid.SetColLabelValue(2, "Proto")
        self.DataGrid.SetColSize(2, 75)
        self.DataGrid.SetColLabelValue(3, "Packets")
        self.DataGrid.SetColSize(3, 75)
        self.DataGrid.SetColLabelValue(4, "In")
        self.DataGrid.SetColSize(4, 50)
        self.DataGrid.SetColLabelValue(5, "Out")
        self.DataGrid.SetColSize(5, 50)
        self.DataGrid.SetColLabelValue(6, "Bandwidth")
        self.DataGrid.SetColSize(6, 75)
        self.DataGrid.SetColLabelValue(7, "PID")
        self.DataGrid.SetColSize(7, 50)
        self.DataGrid.SetColLabelValue(8, "Last Seen")
        self.DataGrid.SetColSize(8, 150)
        self.DataGrid.SetColLabelValue(9, "First Seen")
        self.DataGrid.SetColSize(9, 159)
        self.DataGridRefresh()
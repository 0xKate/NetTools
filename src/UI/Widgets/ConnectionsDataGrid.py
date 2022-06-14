import asyncio
import webbrowser
from enum import Enum

import wx
from wx.grid import Grid
import pyperclip as pc
from wxasync import StartCoroutine

from Model.NetToolsData import NetToolsData

GRID_MAP = {'Packets'}

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
    def __init__(self, parentPanel, dataSource: NetToolsData, *args, **kwargs):
        self.SortDescending = True
        self.SortBy = SortBy.Packets
        self.ParentPanel = parentPanel
        self.DataSource = dataSource
        self.AutoRefresh = True
        self.RefreshRate = 1
        wx.ScrolledWindow.__init__(self, parentPanel, *args, **kwargs)
        self.SetScrollRate(10, 10)
        self.DataGrid = Grid(self, wx.ID_ANY, size=(1, 1))
        self.__set_properties()
        self.__do_layout()
        self.Bind(wx.grid.EVT_GRID_CMD_CELL_RIGHT_CLICK, self.OnDataGridRightClick, source=self.DataGrid)
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
                label = label # type: str
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
        all_conn = sorted(self.DataSource.GetAllConnections(), key=lambda x: self.__GetSortingValue(x, self.SortBy), reverse=self.SortDescending)
        for row in range (0, len(all_conn)):
            host = all_conn[row]
            if not row < self.DataGrid.GetNumberRows():
                self.DataGrid.AppendRows(1, False)
            self.DataGridSetCell(row, 0, str(host.GetRemoteEndPoint()))
            self.DataGridSetCell(row, 1, str(host.RemoteIP))
            self.DataGridSetCell(row, 2, str(host.ProtoType))
            self.DataGridSetCell(row, 3, str(host.PacketCount))
            self.DataGridSetCell(row, 4, str(host.IncomingCount))
            self.DataGridSetCell(row, 5, str(host.OutgoingCount))
            self.DataGridSetCell(row, 6, str(host.BandwidthUsage))
            self.DataGridSetCell(row, 7, str(host.GetPID()))
            self.DataGridSetCell(row, 8, str(host.LastSeen.replace(microsecond=0)))
            self.DataGridSetCell(row, 9, str(host.FirstSeen.replace(microsecond=0)))

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
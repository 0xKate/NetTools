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

import pprint
import netifaces
import socket

import ipcalc



class NetworkInfo:
    """A class that gathers network information about the local network for easy access."""
    def __init__(self):

        self.LocalInterfaceMAC = None
        self.LocalBroadcast = None
        self.LocalInterface = None
        self.LocalInterfaceIP = None
        self.LocalSubnetMask = None
        self.LocalSubnetGateway = None
        self.LocalSubnetNetworkAddress = None
        self.LocalSubnetCidrBlock = None
        self.LocalSubnetCidrSuffix = None
        self.HasInternetAccess = None
        self.__InitIfaceInfo()

    def Dump(self):
        """Print everything for troubleshooting"""
        pprint.PrettyPrinter().pprint(self.__dict__)

    def Refresh(self):
        self.__InitIfaceInfo()

    def __InitIfaceInfo(self):
        _IP = self.__TestForInternetAccess()
        if _IP:
            self.HasInternetAccess = True
            self.LocalInterfaceIP = _IP
            gw = netifaces.gateways()
            for k, v in gw.items():
                if k == 'default':
                    if isinstance(v, dict):
                        for k2, v2 in v.items():
                            self.LocalInterface = v2[1]
                            self.LocalSubnetGateway = v2[0]

        if self.LocalInterface:
            addrs = netifaces.ifaddresses(str(self.LocalInterface))
            l3 = addrs[netifaces.AF_INET][0]
            l2 = addrs[netifaces.AF_LINK][0]
            self.LocalBroadcast = l3['broadcast']
            self.LocalSubnetMask = l3['netmask']
            self.LocalInterfaceIP = l3['addr']
            self.LocalInterfaceMAC = l2['addr']

            x = str(ipcalc.IP(l3['addr'], mask=l3['netmask']).guess_network()).split('/')
            self.LocalSubnetCidrBlock = f'{x[0]}/{x[1]}'
            self.LocalSubnetNetworkAddress = x[0]
            self.LocalSubnetCidrSuffix = f'/{x[1]}'

    @staticmethod
    def __TestForInternetAccess():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 80))
            try:
                r = s.getsockname()[0]
            except Exception as err:
                r = None
                print(f'TestForInternetAccess() - ERROR: {err}')
            finally:
                s.close()
            return r

if __name__ == '__main__':
    NetworkInfo().Dump()


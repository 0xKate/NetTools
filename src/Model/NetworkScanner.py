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
import concurrent.futures
import pprint
import threading
import time
from typing import Dict

import netifaces
import socket

import nmap

from Model.NetworkInfo import NetworkInfo


class NmapAsync(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.Nmap = nmap.PortScanner()
        self.Targets = None
        self.Ports = None
        self.Arguments = None
        self.UserCallback = None
        self.Complete = False

    def __Callback(self, host_data):
        if self.UserCallback is not None and callable(self.UserCallback):
            self.UserCallback(host_data)

    def ScanAsync(self, targets, ports, args, callback=None):
        self.Targets = targets
        self.Ports = ports
        self.Arguments = args
        self.UserCallback = callback
        self.Complete = False
        self.start()

    def __Scan(self):
        for host in self.Targets:
            #print(type(host))
            _out = self.Nmap.scan(hosts=host, ports=self.Ports, arguments=self.Arguments)
            #pprint.PrettyPrinter().pprint(_out)
            #print(type(host))
            if self.Nmap.has_host(host):
                #print(type(host))
                self.__Callback(self.Nmap[host])

    def run(self) -> None:
        self.__Scan()
        time.sleep(2)
        self.Complete = True

class NetworkScanner:
    def __init__(self, loop=None):
        self.LocalNetworkInfo = NetworkInfo()
        self.Loop = loop or asyncio.get_running_loop()
        self.Pool = concurrent.futures.ThreadPoolExecutor()
        self.Running = True
        self.Hosts = {} # type: Dict[str,Dict]
        self.HostsLock = asyncio.Lock

    def cb(self, x):
        if x[1]['nmap']['scanstats']['uphosts'] == '1':
            #print(x[0])
            self.Hosts[f'{x[0]}'] = x[1]['scan'][x[0]]


    def ScannerTask(self, ip, port, arg):
        ns = nmap.PortScannerYield()
        for x in ns.scan(ip, port, arg):
            self.cb(x)
        return True

    async def MainLoop(self):
        print(self.LocalNetworkInfo.LocalSubnetCidrBlock)
        # noinspection PyTypeChecker
        f = self.Loop.run_in_executor(None, self.ScannerTask, self.LocalNetworkInfo.LocalSubnetCidrBlock, None, '') # type: asyncio.Task
        while not f.done():
            print('Working...')
            await asyncio.sleep(1)

        if f.result() is True:
            print("Completed!")
            for k,v in self.Hosts.items():
                print(f'HostsKey: {k}')
                for kk, vv in v.items():
                    if kk == 'tcp':

                        for x,y in v['tcp'].items():
                            print(f'Port: {x} Info: {y}')
                    else:
                        print(f'Key: {kk} Val: {vv}')


async def something_bg():
    c = 0
    while c < 30:
        print('Doing Something Else...')
        await asyncio.sleep(1)
        c +=1

import socket
import concurrent.futures
import asyncio

def __TryGetHostFromAddr(ip):
    try:
        return socket.gethostbyaddr(ip)
    except socket.herror as err:
        #print(f'__GetHostFromAddrAsync - ERROR: [{type(err)}] {err}')
        return None

async def GetHostFromAddrAsync(ip):
    """
    GetHostFromAddr(ip) -> fqdn\n
    :param ip: The hosts ip address ie. 192.168.1.1
    :return: Return the fqdn (a string of the form 'sub.example.com') for a host.
    """
    loop = asyncio.get_event_loop()
    pool = concurrent.futures.ThreadPoolExecutor()
    return await loop.run_in_executor(pool, __TryGetHostFromAddr, ip)




if __name__ == '__main__-OLD':
    n = NetworkScanner(loop=asyncio.new_event_loop())
    t = []
    for i in range(11):
        print(i)
        t.append(n.Loop.create_task(GetHostFromAddrAsync('10.0.0.'+str(i))))
    r = n.Loop.run_until_complete(something_bg())
    for ii in t:
        print(ii.result())

if __name__ == '__main__':
    n = NetworkScanner(loop=asyncio.new_event_loop())
    n.Loop.run_until_complete(n.MainLoop())
import asyncio
import re
import subprocess
import sys
import time

from pyats import aetest, topology

from ssh_config import commands
from lib.connectors.async_telnet_conn import TelnetConnection

print(sys.path)


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def load_testbed(self, steps):
        with steps.start("Load testbed"):
            self.tb = topology.loader.load('testbed1.yaml')
            self.parent.parameters.update(tb=self.tb)


    @aetest.subsection
    def bring_up_router_interface(self, steps):
        for device in self.tb.devices:
            if self.tb.devices[device].type != 'ftd':
                continue
            with steps.start(f'Bring up management interface {device}', continue_=True):

                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue

                    intf_obj = self.tb.devices[device].interfaces[interface]
                    conn_class = self.tb.devices[device].connections.get('telnet', {}).get('class', None)
                    assert conn_class, 'No connection for device {}'.format(device)
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port
                    conn: TelnetConnection = conn_class(ip, port)

                    async def setup():
                        await conn.connect()
                        time.sleep(1)
                        conn.write('')
                        time.sleep(1)
                        out = await conn.read(n=1000)
                        print(out)
                        result = re.search(r'^{?P<login>firepower login:}', out)
                        if result.group('login'):
                            conn.write('admin')
                            time.sleep(0.1)
                            conn.write('Admin123')
                            time.sleep(1)

                        out = await conn.read(n=1000)

                        if 'EULA:' in out:
                            conn.write('\n')
                            while True:
                                time.sleep(1)
                                out = await conn.read(n=1000)
                                if '--More--' in out:
                                    conn.write(' ')
                                elif 'EULA:' in out:
                                    conn.write('\n')
                                    time.sleep(1)
                                    out = await conn.read(n=1000)
                                    break
                                else:
                                    print('No string found in output')

                        if 'password:' in out:
                            conn.write(self.tb.devices[device].connections.telnet.credentials.login.password.plaintext)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                            if 'password:' in out:
                                conn.write(self.tb.devices[device].connections.telnet.credentials.login.password.plaintext)
                                time.sleep(1)
                                out = await conn.read(n=1000)

                        if 'IPv4? (y/n) [y]:' in out:
                            conn.write('\n')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if 'IPv6? (y/n) [n]:' in out:
                            conn.write('\n')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        # result = re.search(r' DHCP or manually? (dhcp/manual) ...:')
                        if '[manual]:' in out:
                            conn.write('\n')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[192.168.45.45]:' in out:
                            conn.write(intf_obj.ipv4.ipv4.ip.compressed)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[255.255.255.0]:' in out:
                            conn.write(intf_obj.ipv4.netmask.exploded)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[192.168.45.1]:' in out:
                            conn.write((intf_obj.ipv4.ip+1).compressed)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '::35]:' in out:
                            conn.write('')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if "'none' []:" in out:
                            conn.write('')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if 'locally? (yes/no) [yes]:' in out:
                            conn.write('')
                            time.sleep(1)
                            out = await conn.read(n=1000)


                    asyncio.run(setup())




class ConfigureInterfaces(aetest.Testcase):

    @aetest.setup
    def configure(self):
        tb = self.parent.parameters['tb']
        conn = tb.devices.IOU1.connections.telnet['class']
        print(conn)


if __name__ == '__main__':
    aetest.main()
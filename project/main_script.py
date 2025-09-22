import re
import time

from pyats import aetest, topology
import subprocess
from pyats.datastructures import AttrDict
import sys
import asyncio
from ssh_config import commands
from lib.connectors.async_telnet_conn import TelnetConnection

obj = AttrDict()
print(sys.path)

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def load_testbed(self, steps):
        with steps.start('Load testbed'):
            self.tb = topology.loader.load('main_testbed.yaml')
            self.parent.parameters.update(tb = self.tb)

    @aetest.subsection
    def bring_up_server_interface(self, steps):
        server = self.tb.devices['UbuntuServer']
        for intf_name, intf in server.interfaces.items():
            # intf = server.interfaces[interface]
            with steps.start(f'Bring up interface {intf_name}'):
                subprocess.run(['sudo', 'ip', 'addr', 'add', f'{intf.ipv4}', 'dev', f'{intf_name}'])
                subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', f'{intf_name}', 'up'])

        with steps.start('Adding routes'):
            subnets = set()
            for device in self.tb.devices:
                if self.tb.devices[device].type != 'router':
                    continue
                gateway = self.tb.devices[device].interfaces['initial'].ipv4.ip.compressed
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name == 'management':
                        continue
                    subnet = self.tb.devices[device].interfaces[interface].ipv4.network.compressed
                    subnets.add(subnet)
            for sub in subnets:
                subprocess.run(['sudo', 'ip', 'route', 'add', f'{sub}', 'via', f'{gateway}'])


    @aetest.subsection
    def configure_ssh(self, steps):
        for device in self.tb.devices:
            if self.tb.devices[device].type != 'router' and self.tb.devices[device].custom.role != 'router':
                continue
            with steps.start(f'Configuring SSH on {device}', continue_=True):
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue
                    intf_obj = self.tb.devices[device].interfaces[interface]
                    conn_class = self.tb.devices[device].connections.get('telnet', {}).get('class', None)
                    assert conn_class, 'No connection for device {}'.format(device)
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port

                    formatted_commands = list(map(
                        lambda s: s.format(
                            interface = interface,
                            ip = intf_obj.ipv4.ip.compressed,
                            sm = intf_obj.ipv4.netmask.exploded,
                            hostname = device,
                            domain = self.tb.devices[device].custom.get('domain', None),
                            username = self.tb.devices[device].connections.ssh.credentials.login.username,
                            password = self.tb.devices[device].connections.ssh.credentials.login.password.plaintext,
                        ),
                        commands
                    ))
                    conn: TelnetConnection = conn_class(ip, port)
                    async def conf():
                        await conn.connect()
                        time.sleep(1)
                        await conn.execute_commands(formatted_commands, '#')
                    asyncio.run(conf())

    @aetest.subsection
    def bring_up_router_interface(self, steps):
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'firewall':
                continue
            with steps.start(f'Bringing up management interface on {device}', continue_=True) as step:  # type: Step
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue

                    intf_obj = self.tb.devices[device].interfaces[interface]
                    hostname = self.tb.devices[device].custom.hostname
                    gateway = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                    conn_class = self.tb.devices[device].connections.get('telnet', {}).get('class',None)
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
                        time.sleep(1)
                        print(out)
                        result = re.search(r'^\s*(?P<login>firepower login:)', out)
                        if not result:
                            step.skipped(reason='Configuration not required')
                        if result.group('login'):
                            conn.write('admin')
                            time.sleep(1)
                            conn.write('Admin123')
                            time.sleep(5)

                        out = await conn.read(n=1000)
                        time.sleep(1)
                        if 'Press <ENTER> to display the EULA: ' in out:
                            conn.write('')
                            while True:
                                time.sleep(1)
                                out = await conn.read(n=1000)
                                if '--More--' in out:
                                    conn.write(' ')
                                elif "Please enter 'YES' or press <ENTER> to AGREE to the EULA: " in out:
                                    conn.write('')
                                    time.sleep(2)
                                    out = await conn.read(n=1000)
                                    break
                                else:
                                    print('No string found in output')

                        if 'password:' in out:
                            conn.write(self.tb.devices[device].connections.telnet.credentials.login.password.plaintext)
                            time.sleep(2)
                            out = await conn.read(n=1000)
                            if 'password:' in out:
                                conn.write(self.tb.devices[device].connections.telnet.credentials.login.password.plaintext)
                                time.sleep(2)
                                out = await conn.read(n=1000)

                        if 'IPv4? (y/n) [y]:' in out:
                            conn.write('')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if 'IPv6? (y/n) [n]:' in out:
                            conn.write('')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        # result = re.search(r' DHCP or manually? (dhcp/manual) ...:')
                        if '[manual]:' in out:
                            conn.write('')
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[192.168.45.45]:' in out:
                            conn.write(intf_obj.ipv4.ip.compressed)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[255.255.255.0]:' in out:
                            conn.write(intf_obj.ipv4.netmask.exploded)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[192.168.45.1]:' in out:
                            conn.write(gateway)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if '[firepower]:' in out:
                            conn.write(hostname)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if "'none' []:" in out:
                            conn.write(gateway)
                            time.sleep(1)
                            out = await conn.read(n=1000)
                        if "'none' []:" in out:
                            conn.write('none')
                            time.sleep(5)
                            out = await conn.read(n=1000)
                        if 'Manage the device locally? (yes/no) [yes]:' in out:
                            conn.write('')
                            await asyncio.sleep(1)
                            out = await conn.read(n=1000)

                    asyncio.run(setup())


if __name__ == '__main__':
    aetest.main()

"""
This test will configure all devices.
"""
import time
import subprocess
import sys
import asyncio

from bravado.exception import HTTPError
from pyats import aetest, topology
from pyats.datastructures import AttrDict
from pyats.topology import Device
from genie.libs.conf.interface.iosxe import Interface
from genie.libs.conf.ospf import Ospf
from lib.connectors.ssh_conn import SSHConnection
from lib.connectors.swagger_conn import SwaggerConnector
from lib.connectors.async_telnet_conn import TelnetConnection
from ssh_config import commands
from int_config import add_ips
from ospf_config import ospf_commands
from ssh_acl import acl_commands

obj = AttrDict()
print(sys.path)


async def telnet_configure_ssh(conn: TelnetConnection, templates, prompt, **kwargs):
    """This is a helper function that is being called inside pyats in order to configure the SSH connection on the devices."""
    await conn.connect()
    time.sleep(1)
    return await conn.configure_ssh(templates=templates, prmt=prompt, **kwargs)


async def telnet_configure_ftd(conn: TelnetConnection, hostname, ip, netmask, gateway, password):
    """This is a helper function that is being called inside pyats in order to configure FTD's initial setup."""
    await conn.connect()
    time.sleep(1)
    return await conn.configure_ftd(
        hostname=hostname,
        ip=ip,
        netmask=netmask,
        gateway=gateway,
        password=password,
    )


class CommonSetup(aetest.CommonSetup):
    """This class is used as a general class. It contains every method used to configure all devices."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tb = None
        self.dev = None

    @aetest.subsection
    def load_testbed(self, steps):
        """This method loads the testbed that provides details about whole topology."""
        with steps.start('Loading testbed'):
            self.tb = topology.loader.load('main_testbed.yaml')
            self.parent.parameters.update(tb=self.tb)

    @aetest.subsection
    def bring_up_server_interface(self, steps):
        """This method adds an IP address and some routes to the container"""
        server = self.tb.devices['UbuntuServer']
        for intf_name, intf in server.interfaces.items():
            # intf = server.interfaces[interface]
            with steps.start(f'Bring up interface {intf_name}'):
                subprocess.run(['sudo', 'ip', 'addr', 'replace',
                                f'{intf.ipv4}',
                                'dev', f'{intf_name}'],
                               check=True)
                subprocess.run(['sudo', 'ip', 'link', 'set', 'dev',
                                f'{intf_name}', 'up'],
                               check=True)

        with steps.start('Adding routes'):
            for device in self.tb.devices:
                if self.tb.devices[device].type != 'router':
                    continue
                gateway = self.tb.devices[device].interfaces['initial'].ipv4.ip.compressed
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name == 'management':
                        continue
                    subnet = self.tb.devices[device].interfaces[interface].ipv4.network.compressed
                    subprocess.run(['sudo', 'ip', 'route', 'replace',
                                    f'{subnet}',
                                    'via', f'{gateway}'],
                                   check = True)


    @aetest.subsection
    def configure_ssh(self, steps):
        """This method configures the SSH connection."""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
                continue
            with steps.start(f'Configuring SSH on {device}', continue_=True):
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue
                    intf_obj = self.tb.devices[device].interfaces[interface]
                    conn_class = self.tb.devices[device].connections.get(
                        'telnet', {}
                    ).get('class', None)
                    assert conn_class, f'No connection for device {device}'
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port
                    username = self.tb.devices[device].connections.ssh.credentials.login.username
                    password = self.tb.devices[device].connections.ssh.credentials.login.password.plaintext
                    domain = self.tb.devices[device].custom.get('domain', None)
                    try:
                        conn: TelnetConnection = conn_class(ip, port)

                        asyncio.run(
                            telnet_configure_ssh(
                                conn,
                                templates=commands,
                                prompt='#',
                                interface=interface,
                                ip=intf_obj.ipv4.ip.compressed,
                                sm=intf_obj.ipv4.netmask.exploded,
                                hostname=device,
                                username=username,
                                password=password,
                                domain=domain,
                            )
                        )
                    except Exception as e:
                        print(f'Failed to connect to device {device}', e)
                        continue

    @aetest.subsection
    def bring_up_ftd_interface(self, steps):
        """This method adds an ip address to FTD's management interface."""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'firewall':
                continue
            with steps.start(f'Bringing up management interface on {device}', continue_=True):
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue

                    intf_obj = self.tb.devices[device].interfaces[interface]
                    hostname = self.tb.devices[device].custom.hostname
                    gateway = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                    conn_class = self.tb.devices[device].connections.get('telnet', {}).get('class', None)
                    assert conn_class, f'No connection for device {device}'
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port
                    password = self.tb.devices[device].connections.telnet.credentials.login.password.plaintext
                    conn: TelnetConnection = conn_class(ip, port)

                    asyncio.run(
                        telnet_configure_ftd(
                            conn,
                            hostname=hostname,
                            ip=intf_obj.ipv4.ip.compressed,
                            netmask=intf_obj.ipv4.netmask.exploded,
                            gateway=gateway,
                            password=password,
                        )
                    )

    @aetest.subsection
    def configure_via_genie(self, steps):
        """This method configure CSR via Genie."""
        self.dev: Device = self.tb.devices.CSR
        self.dev.connect(log_stdout=True,
                         via = 'unicon',
                         )

        @aetest.subsection
        def configure_ospf_via_genie(steps):
        with steps.start("Configure other interfaces on CSR"):
            intf = Interface(
                name='GigabitEthernet2'
            )
            intf.device = self.dev
            intf.ipv4 = self.dev.interfaces['GigabitEthernet2'].ipv4
            intf.enabled = True
            config = intf.build_config(apply=False)
            self.dev.configure(config.cli_config.data)

            intf = Interface(
                name='GigabitEthernet3'
            )
            intf.device = self.dev
            intf.ipv4 = self.dev.interfaces['GigabitEthernet3'].ipv4
            intf.enabled = True
            config = intf.build_config(apply=False)
            self.dev.configure(config.cli_config.data)

        with steps.start("Configure OSPF on CSR"):
            dev = self.dev

            ospf = Ospf()
            da = ospf.device_attr[dev]
            va = da.vrf_attr['default']
            va.instance = '1'

            for ifname in ["GigabitEthernet2", "GigabitEthernet3"]:
                ia = va.area_attr['0'].interface_attr[ifname]
                ia.if_admin_control = True

            cfg = da.build_config(apply=False)
            dev.configure(cfg.cli_config.data)

        with steps.start("Configure SSH ACL on CSR"):
            container_ip = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
            dev = self.dev
            cfg = """
            ip access-list standard SSH
             permit host {container_ip}
             deny any
            line vty 0 4
             access-class SSH in
             transport input ssh
            """.format(container_ip=container_ip )
            dev.configure(cfg)

    @aetest.subsection
    def configure_via_ssh(self, steps):
        """This method configures the devices through SSH."""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in self.tb.devices[device].connections:
                continue
            with steps.start(f'Connecting via SSH on {device}', continue_=True):
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name == 'management':
                        continue
                    intf_obj = self.tb.devices[device].interfaces[interface]
                    conn_class = self.tb.devices[device].connections.get(
                        'ssh', {}).get(
                        'class', None)
                    assert conn_class, f'No connection for device {device}'
                    conn: SSHConnection = conn_class(
                        host=str(self.tb.devices[device].connections.ssh['ip']),
                        port=str(self.tb.devices[device].connections.ssh['port']),
                        username=self.tb.devices[device].connections.
                        ssh.credentials.login['username'],
                        password=self.tb.devices[device].connections.
                        ssh.credentials.login['password'].plaintext)

                    conn.connect()
                    print(
                        conn.configure(
                            add_ips,
                            interface=interface,
                            ip = intf_obj.ipv4.ip.compressed,
                            sm = intf_obj.ipv4.netmask.exploded,
                        )
                    )
                    conn.close()

            with steps.start(f'Configuring OSPF on {device}', continue_=True):
                for interface in self.tb.devices[device].interfaces:
                    conn_class = self.tb.devices[device].connections.get(
                        'ssh', {}).get(
                        'class', None)
                    assert conn_class, f'No connection for device {device}'
                    conn: SSHConnection = conn_class(
                        host=str(self.tb.devices[device].connections.ssh['ip']),
                        port=str(self.tb.devices[device].connections.ssh['port']),
                        username=self.tb.devices[device].connections.
                        ssh.credentials.login['username'],
                        password=self.tb.devices[device].connections.
                        ssh.credentials.login['password'].plaintext)

                    conn.connect()
                    print(conn.configure(ospf_commands, interface=interface))
                    conn.close()

            with steps.start(f'Configuring SSH ACL on {device}', continue_=True):
                conn_class = self.tb.devices[device].connections.get(
                    'ssh', {}).get(
                    'class', None)
                assert conn_class, f'No connection for device {device}'
                conn: SSHConnection = conn_class(
                    host=str(self.tb.devices[device].connections.ssh['ip']),
                    port=str(self.tb.devices[device].connections.ssh['port']),
                    username=self.tb.devices[device].connections.
                    ssh.credentials.login['username'],
                    password=self.tb.devices[device].connections.
                    ssh.credentials.login['password'].plaintext)

                container_ip = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                conn.connect()
                print(conn.configure(acl_commands, ssh_container=container_ip))
                conn.close()

    @aetest.subsection
    def configure_via_swagger_ftd(self, steps):
        """This method is being used to finish initial FTD setup and continue configuring it."""
        with steps.start("Connecting  via swagger"):
            for device in self.tb.devices:
                if self.tb.devices[device].custom.role != 'firewall':
                    continue
                if "swagger" not in self.tb.devices[device].connections:
                    continue
                connection: SwaggerConnector = self.tb.devices[device].connect(via='swagger')
                swagger = connection.get_swagger_client()
                if not swagger:
                    self.failed('No swagger connection')
                print(swagger)
                try:
                    connection.finish_initial_setup()
                except HTTPError:
                    print('Initial setup is complete')
        ftd_ep2 = connection.device.interfaces['ftd_ep2']
        csr_ftd = connection.device.interfaces['csr_ftd']
        with steps.start("Delete existing DHCP server"):
            try:
                print(connection.delete_existing_dhcp_sv())
            except HTTPError:
                print('No existing DHCP server')

        with steps.start('Configuring FTD Interfaces'):
            try:
                print(connection.configure_ftd_interfaces(csr_ftd, ftd_ep2))
            except HTTPError:
                print('FTD interfaces already configured')


        with steps.start("Configure new DHCP server"):
            try:
                print(connection.configure_new_dhcp_sv(ftd_ep2))
            except HTTPError:
                print('Could not configure new DHCP server')

        with steps.start("Configuring OSPF on FTD"):
            try:
                ospf = connection.configure_ospf(
                    vrf_id='default',
                    name='ospf_1',
                    process_id='1',
                    area_id='0',
                    if_to_cidr=[
                        ('csr_ftd', '192.168.204.0/24'),
                        ('ftd_ep2', '192.168.205.0/24'),
                    ],
                )
                print(ospf)
                lst = connection.get_swagger_client().OSPF.getOSPFList(vrfId="default").result()
                for item in lst["items"]:
                    print(item)
            except HTTPError:
                print('Could not configure OSPF on FTD')

        with steps.start("Deploying changes on FTD"):
            try:
                res = connection.deploy(force=True)
            except HTTPError:
                print('Deployment failed')

        with steps.start("Adding allow rule"):
            pass


if __name__ == '__main__':
    aetest.main()

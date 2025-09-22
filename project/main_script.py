"""
This test will configure all devices.
"""
import re
import time
import subprocess
import sys
import asyncio
from pyats import aetest, topology
from pyats.datastructures import AttrDict
from lib.connectors.ssh_conn import SSHConnection
from lib.connectors.swagger_conn import SwaggerConnector
from lib.connectors.async_telnet_conn import TelnetConnection
from ssh_config import commands
from int_config import add_ips
from ospf_config import ospf_commands
from ssh_acl import acl_commands

obj = AttrDict()
print(sys.path)


class CommonSetup(aetest.CommonSetup):
    """This class is used as a general class. It contains every method used to configure all devices."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tb = None

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
                subprocess.run(['sudo', 'ip', 'addr', 'add',
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
                    subprocess.run(['sudo', 'ip', 'route', 'add',
                                    f'{subnet}',
                                    'via', f'{gateway}'],
                                   check = False)


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

                    conn: TelnetConnection = conn_class(ip, port)

                    async def conf():
                        await conn.connect()
                        time.sleep(1)
                        await conn.configure_ssh(
                            templates=commands,
                            prmt='#',
                            interface=interface,
                            ip=intf_obj.ipv4.ip.compressed,
                            sm=intf_obj.ipv4.netmask.exploded,
                            hostname=device,
                            username=username,
                            password=password,
                            domain=domain,
                        )

                    asyncio.run(conf())

    @aetest.subsection
    def bring_up_FTD_interface(self, steps):
        """This method adds an ip address to FTD's management interface."""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'firewall':
                continue
            with steps.start(f'Bringing up management interface on {device}',continue_=True):
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue

                    intf_obj = self.tb.devices[device].interfaces[interface]
                    hostname = self.tb.devices[device].custom.hostname
                    gateway = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                    conn_class = self.tb.devices[device].connections.get('telnet', {}).get('class', None)
                    assert conn_class, 'No connection for device {}'.format(device)
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port
                    password = self.tb.devices[device].connections.telnet.credentials.login.password.plaintext
                    conn: TelnetConnection = conn_class(ip, port)

                    async def setup():
                        await conn.connect()
                        time.sleep(1)
                        await conn.configure_ftd(hostname=hostname,
                                                 ip=intf_obj.ipv4.ip.compressed,
                                                 netmask=intf_obj.ipv4.netmask.exploded,
                                                 gateway=gateway,
                                                 password=password,
                                                 )

                    asyncio.run(setup())

    @aetest.subsection
    def configure_via_ssh(self, steps):
        """This method configures the devices through SSH."""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
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

    # @aetest.subsection
    # def configure_via_swagger_FTD(self, steps):
    #     with steps.start("Connecting  via swagger"):
    #         for device in self.tb.devices:
    #             if self.tb.devices[device].custom.role != 'firewall':
    #                 continue
    #             if "swagger" not in self.tb.devices[device].connections:
    #                 continue
    #             connection: SwaggerConnector = self.tb.devices[device].connect(via='swagger')
    #             print(connection)
    #             swagger = connection.get_swagger_client()
    #             if not swagger:
    #                 self.failed('No swagger connection')
    #             print(swagger)
    #
    #     # with steps.start("Delete existing DHCP server"):
    #     #         dhcp_servers = swagger.DHCPServerContainer.getDHCPServerContainerList().result()
    #     #         for dhcp_server in dhcp_servers['items']:
    #     #             dhcp_serv_list = dhcp_server['servers']
    #     #             print(dhcp_serv_list)
    #     #             dhcp_server.servers = []
    #     #             response = swagger.DHCPServerContainer.editDHCPServerContainer(
    #     #                 objId=dhcp_server.id,
    #     #                 body = dhcp_server,
    #     #             ).result()
    #     #             print(response)
    #
    #     with steps.start('Configuring FTD Interfaces'):
    #         existing_interfaces = swagger.Interface.getPhysicalInterfaceList().result()
    #         ftd_ep2 = connection.device.interfaces['ftd_ep2']
    #         csr_ftd = connection.device.interfaces['csr_ftd']
    #         for interface in existing_interfaces['items']:
    #             if interface.hardwareName == csr_ftd.name:
    #                 interface.ipv4.ipAddress.ipAddress = csr_ftd.ipv4.ip.compressed
    #                 interface.ipv4.ipAddress.netmask = csr_ftd.ipv4.netmask.exploded
    #                 interface.ipv4.dhcp = False
    #                 interface.ipv4.ipType = 'STATIC'
    #                 interface.enable = True
    #                 interface.name = csr_ftd.alias
    #                 response = swagger.Interface.editPhysicalInterface(
    #                     objId=interface.id,
    #                     body=interface,
    #                 ).result()
    #                 print(response)
    #
    #             if interface.hardwareName == ftd_ep2.name:
    #                 interface.ipv4.ipAddress.ipAddress = ftd_ep2.ipv4.ip.compressed
    #                 interface.ipv4.ipAddress.netmask = ftd_ep2.ipv4.netmask.exploded
    #                 interface.ipv4.dhcp = False
    #                 interface.ipv4.ipType = 'STATIC'
    #                 interface.enable = True
    #                 interface.name = ftd_ep2.alias
    #                 response = swagger.Interface.editPhysicalInterface(
    #                     objId=interface.id,
    #                     body=interface,
    #                 ).result()
    #                 interface_for_dhcp = interface
    #                 print(response)
    #     # with steps.start("Configure new DHCP server"):
    #     #     dhcp_servers = swagger.DHCPServerContainer.getDHCPServerContainerList().result()
    #     #     for dhcp_server in dhcp_servers['items']:
    #     #         dhcp_serv_list = dhcp_server['servers']
    #     #         print(dhcp_serv_list)
    #     #         dhcp_server_model = swagger.get_model('DHCPServer')
    #     #         interface_ref_model = swagger.get_model('ReferenceModel')
    #     #         dhcp_server.servers = [
    #     #             dhcp_server_model(
    #     #                 addressPool='192.168.205.100-192.168.205.200',
    #     #                 enableDHCP=True,
    #     #                 interface=interface_ref_model(
    #     #                     # hardwareName=interface_for_dhcp.hardwareName,
    #     #                     id=interface_for_dhcp.id,
    #     #                     name=interface_for_dhcp.name,
    #     #                     type='physicalinterface',
    #     #                     # version='be5gwpeongcmt'
    #     #                 ),
    #     #                 type='dhcpserver'
    #     #             )
    #     #         ]
    #     #         response = swagger.DHCPServerContainer.editDHCPServerContainer(
    #     #             objId=dhcp_server.id,
    #     #             body=dhcp_server,
    #     #         ).result()
    #     #         print(response)
    #
    #     with steps.start("Adding routes to FTD"):
    #         pass
    #
    #     with steps.start("Adding allow rule"):
    #         pass


if __name__ == '__main__':
    aetest.main()

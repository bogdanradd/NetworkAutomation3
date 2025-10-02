#!/usr/bin/env python3
"""
Option B refactor: keep only CommonSetup.load_testbed in CommonSetup, and move
all actionable steps into Testcase/@aetest.test methods so you can cherry-pick
execution via --uids. Bodies are taken from your original subsections.
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


# --------------------------- Helpers (as in your script) ----------------------
async def telnet_configure_ssh(conn: TelnetConnection, templates, prompt, **kwargs):
    await conn.connect()
    time.sleep(1)
    return await conn.configure_ssh(templates=templates, prmt=prompt, **kwargs)


async def telnet_configure_ftd(conn: TelnetConnection, hostname, ip, netmask, gateway, password):
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
    """Only the common prep stays here. All actions moved to Testcases below."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tb = None
        self.dev = None
        self._swagger_conn = None

    # your helper methods remain here and will be accessed via `cs` param
    def ensure_csr_connection(self):
        if not self.dev:
            self.dev: Device = self.tb.devices.CSR
        if not getattr(self.dev, "connected", False):
            self.dev.connect(log_stdout=True, via='unicon')
        return self.dev

    def ensure_ssh_connection(self, device_name):
        dev = self.tb.devices[device_name]
        conn_class = dev.connections.get("ssh", {}).get("class", None)
        assert conn_class, f"No SSH connection for {device_name}"
        conn: SSHConnection = conn_class(
            host=str(dev.connections.ssh['ip']),
            port=str(dev.connections.ssh['port']),
            username=dev.connections.ssh.credentials.login['username'],
            password=dev.connections.ssh.credentials.login['password'].plaintext,
        )
        conn.connect()
        return conn

    def ensure_swagger_connection(self):
        if self._swagger_conn is not None:
            return self._swagger_conn
        for device in self.tb.devices:
            dev = self.tb.devices[device]
            if dev.custom.role != 'firewall':
                continue
            if "swagger" not in dev.connections:
                continue
            connection: SwaggerConnector = dev.connect(via='swagger')
            swagger = connection.get_swagger_client()
            if not swagger:
                self.failed('No swagger connection')
            self._swagger_conn = connection
            return self._swagger_conn

    @aetest.subsection
    def load_testbed(self):
        self.tb = topology.loader.load('main_testbed.yaml')
        # expose both tb and the CommonSetup instance (for helper methods)
        self.parent.parameters.update(tb=self.tb, cs=self)


# ---------------------------- Testcases per area ------------------------------
class Container(aetest.Testcase):
    @aetest.test
    def bring_up_server_interface(self, tb):
        server = tb.devices['UbuntuServer']
        for intf_name, intf in server.interfaces.items():
            subprocess.run(['sudo', 'ip', 'addr', 'replace', f'{intf.ipv4}', 'dev', f'{intf_name}'], check=True)
            subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', f'{intf_name}', 'up'], check=True)
        for device in tb.devices:
            if tb.devices[device].type != 'router':
                continue
            gateway = tb.devices[device].interfaces['initial'].ipv4.ip.compressed
            for interface in tb.devices[device].interfaces:
                if tb.devices[device].interfaces[interface].link.name == 'management':
                    continue
                subnet = tb.devices[device].interfaces[interface].ipv4.network.compressed
                subprocess.run(['sudo', 'ip', 'route', 'replace', f'{subnet}', 'via', f'{gateway}'], check=True)


class TelnetBootstrap(aetest.Testcase):
    @aetest.test
    def configure_ssh(self, tb):
        for device in tb.devices:
            if tb.devices[device].custom.role != 'router':
                continue
            for interface in tb.devices[device].interfaces:
                if tb.devices[device].interfaces[interface].link.name != 'management':
                    continue
                intf_obj = tb.devices[device].interfaces[interface]
                conn_class = tb.devices[device].connections.get('telnet', {}).get('class', None)
                assert conn_class, f'No connection for device {device}'
                ip = tb.devices[device].connections.telnet.ip.compressed
                port = tb.devices[device].connections.telnet.port
                username = tb.devices[device].connections.ssh.credentials.login.username
                password = tb.devices[device].connections.ssh.credentials.login.password.plaintext
                domain = tb.devices[device].custom.get('domain', None)
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


class FTDMgmt(aetest.Testcase):
    @aetest.test
    def bring_up_ftd_interface(self, tb):
        for device in tb.devices:
            if tb.devices[device].custom.role != 'firewall':
                continue
            for interface in tb.devices[device].interfaces:
                if tb.devices[device].interfaces[interface].link.name != 'management':
                    continue
                intf_obj = tb.devices[device].interfaces[interface]
                hostname = tb.devices[device].custom.hostname
                gateway = tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                conn_class = tb.devices[device].connections.get('telnet', {}).get('class', None)
                assert conn_class, f'No connection for device {device}'
                ip = tb.devices[device].connections.telnet.ip.compressed
                port = tb.devices[device].connections.telnet.port
                password = tb.devices[device].connections.telnet.credentials.login.password.plaintext
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


class GenieCSR(aetest.Testcase):
    @aetest.test
    def configure_other_interfaces(self, cs):
        dev = cs.ensure_csr_connection()
        for ifname in ("GigabitEthernet2", "GigabitEthernet3"):
            intf = Interface(name=ifname)
            intf.device = dev
            intf.ipv4 = dev.interfaces[ifname].ipv4
            intf.enabled = True
            cfg = intf.build_config(apply=False)
            dev.configure(cfg.cli_config.data)

    @aetest.test
    def configure_ospf(self, cs):
        dev = cs.ensure_csr_connection()
        ospf = Ospf()
        da = ospf.device_attr[dev]
        va = da.vrf_attr['default']
        va.instance = '1'
        for ifname in ("GigabitEthernet2", "GigabitEthernet3"):
            ia = va.area_attr['0'].interface_attr[ifname]
            ia.if_admin_control = True
        cfg = da.build_config(apply=False)
        dev.configure(cfg.cli_config.data)

    @aetest.test
    def configure_ssh_acl(self, tb, cs):
        dev = cs.ensure_csr_connection()
        container_ip = tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
        cfg = f"""
        ip access-list standard SSH
         permit host {container_ip}
         deny any
        line vty 0 4
         access-class SSH in
         transport input ssh
        """
        dev.configure(cfg)


class SSHRouters(aetest.Testcase):
    @aetest.test
    def configure_interfaces(self, tb, cs):
        for device in tb.devices:
            if tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in tb.devices[device].connections:
                continue
            conn = cs.ensure_ssh_connection(device)
            try:
                for interface in tb.devices[device].interfaces:
                    if tb.devices[device].interfaces[interface].link.name == 'management':
                        continue
                    intf_obj = tb.devices[device].interfaces[interface]
                    print(
                        conn.configure(
                            add_ips,
                            interface=interface,
                            ip=intf_obj.ipv4.ip.compressed,
                            sm=intf_obj.ipv4.netmask.exploded,
                        )
                    )
            finally:
                conn.close()

    @aetest.test
    def configure_ospf(self, tb, cs):
        for device in tb.devices:
            if tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in tb.devices[device].connections:
                continue
            conn = cs.ensure_ssh_connection(device)
            try:
                for interface in tb.devices[device].interfaces:
                    print(conn.configure(ospf_commands, interface=interface))
            finally:
                conn.close()

    @aetest.test
    def configure_acl(self, tb, cs):
        for device in tb.devices:
            if tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in tb.devices[device].connections:
                continue
            conn = cs.ensure_ssh_connection(device)
            try:
                container_ip = tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                print(conn.configure(acl_commands, ssh_container=container_ip))
            finally:
                conn.close()


class SwaggerFTD(aetest.Testcase):
    @aetest.test
    def connect_and_initial_setup(self, cs):
        connection = cs.ensure_swagger_connection()
        swagger = connection.get_swagger_client()
        print(swagger)
        try:
            connection.finish_initial_setup()
        except HTTPError:
            print('Initial setup is complete')

    @aetest.test
    def delete_existing_dhcp(self, cs):
        connection = cs.ensure_swagger_connection()
        try:
            print(connection.delete_existing_dhcp_sv())
        except HTTPError:
            print('No existing DHCP server')

    @aetest.test
    def configure_ftd_interfaces(self, cs):
        connection = cs.ensure_swagger_connection()
        ftd_ep2 = connection.device.interfaces['ftd_ep2']
        csr_ftd = connection.device.interfaces['csr_ftd']
        try:
            print(connection.configure_ftd_interfaces(csr_ftd, ftd_ep2))
        except HTTPError:
            print('FTD interfaces already configured')

    @aetest.test
    def configure_new_dhcp(self, cs):
        connection = cs.ensure_swagger_connection()
        ftd_ep2 = connection.device.interfaces['ftd_ep2']
        try:
            print(connection.configure_new_dhcp_sv(ftd_ep2))
        except HTTPError:
            print('Could not configure new DHCP server')

    @aetest.test
    def configure_ospf(self, cs):
        connection = cs.ensure_swagger_connection()
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

    @aetest.test
    def deploy(self, cs):
        connection = cs.ensure_swagger_connection()
        try:
            connection.deploy(force=True)
        except HTTPError:
            print('Deployment failed')


if __name__ == '__main__':
    aetest.main()
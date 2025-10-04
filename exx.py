import asyncio
import re
import subprocess
import ipaddress
import multiprocessing
import sys
import time
import bravado.exception
from multiprocessing import Queue, Process
import ipaddress

from pyats import aetest, topology
from pyats.aetest.steps import Step

from connectors.telnet_conn import TelnetConnection
from connectors.ssh_conn import SshConnection
from connectors.rest_conn import RESTConnector
from connectors.swagger_conn import SwaggerConnector
from final_project_V1.tools import router_config, static_route_config


def show_CLI_menu():
    print("\n=== Device Configuration Menu ===")
    print("1. Configure Ubuntu Server (PC)")
    print("2. Configure Routers (IOU/IOSv/CSR)")
    print("3. Configure FTD Initial Setup")
    print("4. Configure FTD Interfaces")
    print("5. Deploy FTD Configuration")
    print("6. Ping End Devices")
    print("7. Diagnose CSR")
    print("8. Configure All Devices")
    print("0. Exit")
    print("=================================\n")

    #option = input("Enter your option: ")
    option = "7"
    return option

def get_user_options():
    selected = set()
    while True:
        option = show_CLI_menu()
        match option:
            case "1":
                selected.add("server")
            case "2":
                selected.add("routers")
            case "3":
                selected.add("ftd_initial")
            case "4":
                selected.add("ftd_interfaces")
            case "5":
                selected.add("ftd_deploy")
            case "6":
                selected.add("ping_end_devices")
            case "7":
                selected.add("diagnose")
            case "8":
                selected.update(["server", "routers", "ftd_initial", "ftd_interfaces", "ftd_deploy", "diagnose"])
            case "0":
                print("Exiting...")
                sys.exit(0)
            case _:
                print("Invalid option, try again.")
                continue

        #another = input("Add another selection? (y/n): ").lower()
        another="n"
        if another != "y":
            break
    return selected


def create_ipv4(swagger, interface):
    """Ensure interface has ipv4.ipAddress initialized with HAIPv4Address if missing"""
    if not interface.ipv4:
        ipv4_model = swagger.get_model('InterfaceIPv4')
        interface.ipv4 = ipv4_model()

    if not interface.ipv4.ipAddress:
        ha_model = swagger.get_model('HAIPv4Address')
        interface.ipv4.ipAddress = ha_model(
            ipAddress=None,
            netmask=None,
            standbyIpAddress=None,
            type='haipv4address'
        )

    return interface

def ping_endpoints() -> bool:
    return True

class CommonSetup(aetest.CommonSetup):

    def find_gateway(self, device, intf_obj):
        """
        Find the correct gateway for a given device interface
        by matching link name parts against other devices' aliases.
        """
        link_name = intf_obj.link.name
        link_parts = link_name.split('_')

        for neighbor in self.tb.devices.values():
            if neighbor is device:
                continue
            if getattr(neighbor, "alias", None) in link_parts:
                # Pick neighbor's IP from interface on the same link
                for nbr_intf in neighbor.interfaces.values():
                    if nbr_intf.link.name == link_name:
                        return nbr_intf.ipv4.ip.compressed
        return None

    @aetest.subsection
    def load_testbed(self, steps):
        with steps.start("Load testbed"):
            self.tb = topology.loader.load('testbeds/testbed.yaml')
            self.parent.parameters.update(tb=self.tb)

    #@aetest.subsection
    # def load_testbed(self, steps):
    #     """ This method will load the testbed """
    #     with steps.start("Load testbed"):
    #         tb = topology.loader.load('testbed.yaml')
    #         self.parent.parameters.update(tb=tb)

    # Ubuntu Server Configuration
    @aetest.subsection
    def activate_server_interface(self, steps):
        #tb = self.parent.parameters.get('tb')
        server = self.tb.devices['UbuntuServer']
        for interface in server.interfaces:
            intf = server.interfaces[interface]
            with steps.start(f"Bring up interface {interface}", continue_=True) as step: #type: Step
                if "server" not in USER_SELECTION:
                    step.skipped("User skipped Ubuntu Server configuration")
                    return
                subprocess.run(['sudo', 'ip', 'addr', 'add', f'{intf.ipv4}', 'dev', f'{interface}'])
                subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', f'{interface}', 'up'])

        with steps.start("Add routes", continue_=True) as step: #type: Step
            if "server" not in USER_SELECTION:
                step.skipped("User skipped Ubuntu Server configuration")
                return
            for device in self.tb.devices:
                if self.tb.devices[device].type not in ('router', 'ftd'):
                    continue
                try:
                    gateway = self.tb.devices[device].interfaces['initial'].ipv4.ip.compressed
                except KeyError:
                    gateway = self.tb.devices[device].interfaces['csr_initial'].ipv4.ip.compressed

                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name=='management':
                        continue
                    subnet = self.tb.devices[device].interfaces[interface].ipv4.network.network_address.compressed
                    print("subnet:",subnet)
                    print("gateway:",gateway)

                    subprocess.run(
                        ['sudo', 'ip', 'route', 'add', f'{subnet}', 'via', f'{gateway}', 'metric', '100'])

    #IOU ,IOSv and CSR configuration
    @aetest.subsection
    def activate_routers(self, steps):
        is_csr = False
        csr_init = False
        #tb = self.parent.parameters.get('tb')
        for device in self.tb.devices:
            if self.tb.devices[device].type != 'router':
                continue
            with steps.start(f'Bring up interface {device}', continue_=True) as step: #type: Step
                if "routers" not in USER_SELECTION:
                    step.skipped("User skipped Ubuntu Server configuration")
                    return

                for interface in self.tb.devices[device].interfaces:
                    intf_obj=self.tb.devices[device].interfaces[interface]
                    conn_class=self.tb.devices[device].connections.get('telnet',{}).get('class',None)
                    assert conn_class,'No connection for device {}'.format(device)
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port

                    csr_commands=[]

                    #if router interface is not of the form GigabitEthernet0/0, it means the device is a csr router
                    if r'0/' not in intf_obj.name and intf_obj.link.name == "management":
                        csr_commands=['en','conf t', 'hostname CSR', 'exit']
                        is_csr=True

                    commands=router_config.interface_commands
                    intf_commands=list(map(
                        lambda s: s.format(
                            interface=interface,
                            ip=intf_obj.ipv4.ip.compressed,
                            sm=intf_obj.ipv4.netmask.exploded,
                        ),
                        commands
                    ))
                    interface_commands = intf_commands

                    #conn: TelnetConnection = conn_class(ip, port)

                    ssh_config_commands=[]

                    if intf_obj.link.name == 'management':
                        commands=router_config.ssh_commands
                        ssh_commands=csr_commands+list(map(
                            lambda s: s.format(
                                hostname=self.tb.devices[device].custom.get('hostname', device),
                                domain=self.tb.devices[device].custom.get('domain',''),
                                username=self.tb.devices[device].connections.telnet.credentials.login.username,
                                password=self.tb.devices[device].connections.telnet.credentials.login.password.plaintext,
                                en_password=self.tb.devices[device].connections.telnet.credentials.enable.password.plaintext,

                            ),
                            commands
                        ))

                        ssh_config_commands = ssh_commands

                    route_commands = []

                    if intf_obj.link.name !='management':
                        own_subnet = intf_obj.ipv4.network.network_address.compressed
                        own_subnet_third_byte=own_subnet.split('.')[2]
                        print(own_subnet)

                        if self.tb.devices[device].alias in intf_obj.link.name.split('_')[1]:
                            for i in range(210, int(own_subnet_third_byte), 10):
                                subnet="192.168." + str(i) + ".0"

                                mask = str(intf_obj.ipv4.netmask)

                                gateway = self.find_gateway(self.tb.devices[device], intf_obj)
                                print(gateway)
                                if not gateway:
                                    continue

                                route_commands += list(map(
                                    lambda s: s.format(subnet=subnet, mask=mask, gateway=gateway),
                                    static_route_config.commands
                                ))

                        if self.tb.devices[device].alias in intf_obj.link.name.split('_')[0]:
                            for i in range(int(own_subnet_third_byte)+10, 251, 10):
                                subnet="192.168." + str(i) + ".0"

                                mask = str(intf_obj.ipv4.netmask)

                                gateway = self.find_gateway(self.tb.devices[device], intf_obj)
                                print(gateway)
                                if not gateway:
                                    continue

                                route_commands += list(map(
                                    lambda s: s.format(subnet=subnet, mask=mask, gateway=gateway),
                                    static_route_config.commands
                                ))


                    # Final command list
                    formatted_commands = csr_commands + interface_commands + ssh_config_commands + route_commands
                    print(formatted_commands)

                    conn: TelnetConnection = conn_class(ip, port)

                    async def setup():
                        nonlocal csr_init
                        await conn.connect()
                        time.sleep(1)
                        if is_csr and not csr_init:
                            await conn.initialize_csr()
                            csr_init = True
                        await conn.enter_commands(formatted_commands, '#')
                    asyncio.run(setup())

    #CSR configuration
    # @aetest.subsection
    # def activate_CSR_interface(self, steps):
    #     #tb = self.parent.parameters.get('tb')
    #     for device in self.tb.devices:
    #         if self.tb.devices[device].type != 'csr_router':
    #             continue
    #         else:
    #             with steps.start(f'Bring up interface {device}',continue_=True):
    #                 for interface in self.tb.devices[device].interfaces:
    #                     if self.tb.devices[device].interfaces[interface].link.name !='management':
    #                         continue
    #
    #                     intf_obj=self.tb.devices[device].interfaces[interface]
    #                     conn_class=self.tb.devices[device].connections.get('telnet',{}).get('class',None)
    #                     assert conn_class,'No connection for device {}'.format(device)
    #                     ip = self.tb.devices[device].connections.telnet.ip.compressed
    #                     port = self.tb.devices[device].connections.telnet.port
    #                     q=multiprocessing.Queue()
    #
    #                     commands=['conf t', 'hostname CSR', 'exit']
    #
    #                     commands+=ssh_config.commands
    #                     formatted_commands=list(map(
    #                         lambda s: s.format(
    #                             interface=interface,
    #                             ip=intf_obj.ipv4.ip.compressed,
    #                             sm=intf_obj.ipv4.netmask.exploded,
    #                             hostname=device,
    #                             domain=self.tb.devices[device].custom.get('domain',''),
    #                             username=self.tb.devices[device].connections.telnet.credentials.login.username,
    #                             password=self.tb.devices[device].connections.telnet.credentials.login.password.plaintext,
    #
    #                         ),
    #                         commands
    #                     ))
    #
    #                     conn: TelnetConnection = conn_class(ip, port)
    #
    #
    #                     async def setup():
    #                         await conn.connect()
    #                         time.sleep(1)
    #                         await conn.enter_commands(formatted_commands, '#')
    #                     asyncio.run(setup())

    #Initial FTD configuration
    @aetest.subsection
    def configure_initial_FTD(self, steps):
        #tb = self.parent.parameters.get('tb')
        for device in self.tb.devices:
            if self.tb.devices[device].type != 'ftd':
                continue
            with steps.start(f'Bring up management interface {device}', continue_=True) as step: # type: Step
                if "ftd_initial" not in USER_SELECTION:
                    step.skipped("User skipped Ubuntu Server configuration")
                    return
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
                        await asyncio.sleep(1)
                        conn.writer.write('\n')
                        time.sleep(3)
                        out = await conn.read(n=1000)
                        print(out)
                        while out!='>':
                            result=re.search(r'^\s*(?P<login>firepower login:)', out)
                            print(result)
                            if not result:
                                step.skipped(reason='No login')

                            while not result.group('login'):
                                time.sleep(5)
                            else:
                                conn.write('admin')
                                await conn.readuntil('Password:')
                                time.sleep(2)
                                conn.write('Admin123')
                                time.sleep(2)

                            while not 'EULA:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                while True:
                                    time.sleep(5)
                                    out = await conn.read(n=1000)
                                    if '--More--' in out:
                                        conn.writer.write(' ')
                                    elif 'EULA:' in out:
                                        conn.writer.write('\n')
                                        time.sleep(5)
                                        out = await conn.read(n=1000)
                                        break
                                    else:
                                        print('no str found in eula')

                            while not 'password:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                #time.sleep(5)
                                tmp=self.tb.devices[device].credentials.default.password.plaintext
                                print(tmp)
                                conn.writer.write(self.tb.devices[device].credentials.default.password.plaintext +'\n')
                                time.sleep(3)
                                out = await conn.read(n=1000)
                                if 'password:' in out:
                                    time.sleep(5)
                                    tmp=self.tb.devices[device].credentials.default.password.plaintext
                                    print(tmp)
                                    conn.writer.write(self.tb.devices[device].credentials.default.password.plaintext+ '\n')
                                    time.sleep(3)
                                    out = await conn.read(n=1000)

                            # out = await conn.read(n=1000)
                            # print(out)

                            while not 'IPv4? (y/n) [y]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not 'IPv6? (y/n) [n]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not '[manual]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not '[192.168.45.45]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write(intf_obj.ipv4.ip.compressed + '\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not '[255.255.255.0]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write(intf_obj.ipv4.netmask.exploded + '\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not '[192.168.45.1]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                                if 're-enter.' in out:
                                    break
                            else:
                                conn.writer.write((intf_obj.ipv4.network.network_address+1).compressed + '\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not '[firepower]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not '::35]:' in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not "'none' []:" in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(1)
                                out = await conn.read(n=1000)

                            while not "locally? (yes/no) [yes]:" in out:
                                time.sleep(5)
                                out = await conn.read(n=1000)
                            else:
                                conn.writer.write('\n')
                                time.sleep(5)
                                out = await conn.read(n=1000)
                        else:
                            print("initial configuration already completed")

                    try:
                        asyncio.run(setup())
                    except BaseException as e:
                        print(e)
                        print(e.args)

    # Place this step BEFORE "Configure FTD Interfaces"
    @aetest.subsection
    def cleanup_and_create_zones(self, steps):
        global USER_SELECTION
        """Cleans up old zones and rules, then creates new zones."""

        # --- Cleanup Access Rules ---
        with steps.start("Cleaning up existing Access Rules", continue_=True) as step: #type: Step
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return
            for device in self.tb.devices:
                if self.tb.devices[device].type != 'ftd':
                    continue
                if "swagger" not in self.tb.devices[device].connections:
                    continue
                while True:
                    try:
                        connection: SwaggerConnector = self.tb.devices[device].connect(via="swagger")
                        # print(connection)
                        swagger = connection.get_swagger_client()
                        break
                    except bravado.exception.HTTPServiceUnavailable:
                        print('FTD Device is still performing initialization! Please wait a few minutes and try again.')
                        ftd_opt = input("Would you like to try again? [y/n]: ").lower()
                        if ftd_opt == 'y' or ftd_opt == 'yes':
                            continue
                        elif ftd_opt == 'n' or ftd_opt == 'no':
                            step.skipped("User skipped FTD interface configuration")
                            tmp_list=list(USER_SELECTION)
                            idx = tmp_list.index("ftd_interfaces")
                            del tmp_list[idx]
                            USER_SELECTION = set(tmp_list)
                            print(USER_SELECTION)
                            return
                        else:
                            step.skipped("Wrong option entered, defaulting to 'no'")
                            tmp_list=list(USER_SELECTION)
                            idx = tmp_list.index("ftd_interfaces")
                            del tmp_list[idx]
                            USER_SELECTION = set(tmp_list)
                            print(USER_SELECTION)
                            return
                try:
                    connection.accept_eula()
                except bravado.exception.HTTPUnprocessableEntity as e:
                    print('Initial configuration already completed:', e)

                if not swagger:
                    self.failed('No swagger connection')
                print(swagger)

                try:
                    policy_id = swagger.AccessPolicy.getAccessPolicyList().result()['items'][0].id
                    rules = swagger.AccessPolicy.getAccessRuleList(parentId=policy_id).result().get('items', [])
                    for rule in rules:
                        if rule.name in ["Allow_Inside_to_Outside", "Allow_Outside_to_Inside"]:
                            #print(f"Deleting existing rule: {rule.name}")
                            swagger.AccessPolicy.deleteAccessRule(parentId=policy_id, objId=rule.id).result()
                except Exception as e:
                   print(f"Could not clean up access rules: {e}")

        # --- Cleanup Security Zones ---
        with steps.start("Cleaning up existing Access Rules", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return
            try:
                policy_id = self.swagger.AccessPolicy.getAccessPolicyList().result()['items'][0].id
                rules = self.swagger.AccessPolicy.getAccessRuleList(parentId=policy_id).result().get('items', [])
                for rule in rules:
                    if rule.name in ["Allow_Inside_to_Outside", "Allow_Outside_to_Inside"]:
                        #print(f"Deleting existing rule: {rule.name}")
                        self.swagger.AccessPolicy.deleteAccessRule(parentId=policy_id, objId=rule.id).result()
            except Exception as e:
                print(f"Could not clean up access rules: {e}")

        # --- Cleanup Security Zones ---
        with steps.start("Cleaning up existing Security Zones", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return
            try:
                zones = self.swagger.SecurityZone.getSecurityZoneList().result().get('items', [])
                for zone in zones:
                    if zone.name in ["Inside-Zone", "Outside-Zone"]:
                        #print(f"Deleting existing zone: {zone.name}")
                        self.swagger.SecurityZone.deleteSecurityZone(objId=zone.id).result()
            except Exception as e:
                print(f"Could not clean up security zones: {e}")

    #FTD interface configuration
    @aetest.subsection
    def configure_ftd_and_deploy(self, steps):
        # --- Step 1: Connect and establish swagger client ---
        with steps.start("Connect via REST", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return
            for device in self.parent.parameters['tb'].devices:
                if self.tb.devices[device].type != 'ftd':
                    continue
                    # connection = device.connect(via="swagger")
                    # # CORRECTED: Store swagger client on self for use in all steps
                    # self.swagger = connection.get_swagger_client()
                    # self.connection = connection # Store connection as well

                if "swagger" not in self.tb.devices[device].connections:
                    continue
                connection: SwaggerConnector = self.tb.devices[device].connect(via="swagger")
                # print(connection)
                self.swagger = connection.get_swagger_client()
                self.connection = connection
                try:
                    connection.accept_eula()
                except bravado.exception.HTTPUnprocessableEntity as e:
                    print('Initial configuration already completed:', e)

                # if not swagger:
                #     self.failed('No swagger connection')
                # print(swagger)

                break
            if not self.swagger:
                step.failed("Failed to get Swagger client")

        with steps.start("Delete existing DHCP server", continue_=True) as step: #type: Step
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped Ubuntu Server configuration")
                return
            dhcp_servers = self.swagger.DHCPServerContainer.getDHCPServerContainerList().result()
            for dhcp_server in dhcp_servers['items']:
                dhcp_serv_list = dhcp_server['servers']
                print(dhcp_serv_list)
                dhcp_server.servers = []
                response = self.swagger.DHCPServerContainer.editDHCPServerContainer(
                    objId=dhcp_server.id,
                    body=dhcp_server,
                ).result()
                print(response)

        # --- Step 2: Configure Interfaces ---
        with steps.start('Configure FTD Interfaces', continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return
            # Get live interface objects from FTD
            existing_interfaces = self.swagger.Interface.getPhysicalInterfaceList().result()
            # Get interface config from testbed YAML
            csr_ftd_config = self.connection.device.interfaces['csr_ftd']
            ftd_ep2_config = self.connection.device.interfaces['ftd_ep2']

            csr_ftd_swagger = None
            ftd_ep2_swagger = None
            for interface in existing_interfaces['items']:
                if interface.hardwareName == csr_ftd_config.name:
                    csr_ftd_swagger = interface
                if interface.hardwareName == ftd_ep2_config.name:
                    interface = create_ipv4(self.swagger, interface)
                    ftd_ep2_swagger = interface

            if not (csr_ftd_swagger and ftd_ep2_swagger):
                step.failed("Could not find both required interfaces on the FTD.", goto=['exit'])

            # Configure IPs and basic settings
            csr_ftd_swagger.name = csr_ftd_config.alias
            csr_ftd_swagger.ipv4.ipAddress.ipAddress = csr_ftd_config.ipv4.ip.compressed
            csr_ftd_swagger.ipv4.ipAddress.netmask = csr_ftd_config.ipv4.netmask.exploded
            csr_ftd_swagger.ipv4.dhcp = False
            csr_ftd_swagger.ipv4.ipType = 'STATIC'
            csr_ftd_swagger.enable = True
            csr_ftd_swagger.name = csr_ftd_config.alias
            self.swagger.Interface.editPhysicalInterface(objId=csr_ftd_swagger.id, body=csr_ftd_swagger).result()

            ftd_ep2_swagger.name = ftd_ep2_config.alias
            ftd_ep2_swagger.ipv4.ipAddress.ipAddress = ftd_ep2_config.ipv4.ip.compressed
            ftd_ep2_swagger.ipv4.ipAddress.netmask = ftd_ep2_config.ipv4.netmask.exploded
            ftd_ep2_swagger.ipv4.dhcp = False
            ftd_ep2_swagger.ipv4.ipType = 'STATIC'
            ftd_ep2_swagger.name = ftd_ep2_config.alias
            ftd_ep2_swagger.securityLevel = 100
            ftd_ep2_swagger.managementOnly = False
            ftd_ep2_swagger.enable = True
            ftd_ep2_swagger.enabled = True
            self.swagger.Interface.editPhysicalInterface(objId=ftd_ep2_swagger.id, body=ftd_ep2_swagger).result()

            interface_for_dhcp = ftd_ep2_swagger
            print(response)

            # Store for later steps
            self.csr_ftd_swagger = csr_ftd_swagger
            self.ftd_ep2_swagger = ftd_ep2_swagger
            step.passed("Successfully configured IP addresses on interfaces.")


        with steps.start("Add DHCP server to interface", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped Ftd interface configuration")
                return
            dhcp_servers = self.swagger.DHCPServerContainer.getDHCPServerContainerList().result()
            for dhcp_server in dhcp_servers['items']:
                dhcp_serv_list = dhcp_server['servers']
                print(dhcp_serv_list)
                dhcp_server_model = self.swagger.get_model('DHCPServer')
                interface_ref_model = self.swagger.get_model('ReferenceModel')

                # if interface_for_dhcp.id not in [ref.id for ref in dhcp_server.interfaces]:
                #     continue

                dhcp_server.servers = [
                    dhcp_server_model(
                        addressPool='192.168.250.100-192.168.250.200',
                        enableDHCP=True,
                        interface=interface_ref_model(
                            # hardwareName=interface_ref_model.hardwareName,
                            id=interface_for_dhcp.id,
                            name=interface_for_dhcp.name,
                            type='physicalinterface',
                            # version='be5qwpeonqcmt'
                        ),
                        type='dhcpserver'
                    )
                ]
                response = self.swagger.DHCPServerContainer.editDHCPServerContainer(
                    objId=dhcp_server.id,
                    body=dhcp_server,
                ).result()
                print(response)


        # --- Step 3: Create Security Zones with Interface Assignments ---
        with steps.start("Create Security Zones and Assign Interfaces", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return

            # This logic is now in the same scope and uses the correct swagger objects
            inside_zone_body = {
                "name": "Inside-Zone", "mode": "ROUTED", "type": "securityzone",
                "interfaces": [{"type": "physicalinterface", "id": self.csr_ftd_swagger.id, "name": self.csr_ftd_swagger.name}]
            }
            self.inside_zone = self.swagger.SecurityZone.addSecurityZone(body=inside_zone_body).result()

            outside_zone_body = {
                "name": "Outside-Zone", "mode": "ROUTED", "type": "securityzone",
                "interfaces": [{"type": "physicalinterface", "id": self.ftd_ep2_swagger.id, "name": self.ftd_ep2_swagger.name}]
            }
            self.outside_zone = self.swagger.SecurityZone.addSecurityZone(body=outside_zone_body).result()
            step.passed(f"Created zones and assigned interfaces: {self.csr_ftd_swagger.name} -> Inside, {self.ftd_ep2_swagger.name} -> Outside")

        # --- Step 4: Add Static Routes ---
        #Static FTD routes
        with steps.start("Add routes", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD route configuration")
                return

            # 1. GET THE DEVICE ID TO USE AS THE parentId
            # ==========================================================
            try:
                # The objId for the FDM's own system information is the literal string "default".
                system_info = self.swagger.SystemInformation.getSystemInformation(
                    objId="default"
                ).result()

                # The device ID is a direct attribute of the returned object.
                device_id = system_info.id
                print(f"Found Device ID (parentId): {device_id}")

            except Exception as e:
                self.failed(f"Failed to retrieve device ID: {e}")
                # ==========================================================

            # Grab the FTD interfaces we already matched earlier
            csr_ftd = connection.device.interfaces['csr_ftd']
            ftd_ep2 = connection.device.interfaces['ftd_ep2']
            existing_interfaces = self.swagger.Interface.getPhysicalInterfaceList().result()

            csr_ftd_swagger = None
            ftd_ep2_swagger = None

            for interface in existing_interfaces['items']:
                if interface.hardwareName == csr_ftd.name:
                    csr_ftd_swagger = interface
                if interface.hardwareName == ftd_ep2.name:
                    ftd_ep2_swagger = interface

            # Helper: create a network object for a subnet
            def create_network_object(name, cidr):
                obj = {
                    "name": name,
                    "value": cidr,
                    "subType": "NETWORK",
                    "type": "networkobject"
                }
                return self.swagger.NetworkObject.addNetworkObject(body=obj).result()

            # Helper: create a host object for a gateway IP
            def create_host_object(name, ip):
                obj = {
                    "name": name,
                    "value": ip,
                    "subType": "HOST",
                    "type": "networkobject"
                }
                return self.swagger.NetworkObject.addNetworkObject(body=obj).result()

            routes_to_add = []

            # Route guest1 network
            if csr_ftd_swagger:
                net_obj = create_network_object("net_guest2", "192.168.210.0/24")
                gw_obj = create_host_object("gw_guest2", "192.168.240.4")

                routes_to_add.append({
                    "name": "route_to_guest1",
                    "iface": {
                        "id": csr_ftd_swagger.id,
                        "name": csr_ftd_swagger.name,
                        "type": "physicalinterface"
                    },
                    "networks": [{
                        "id": net_obj["id"],
                        "name": net_obj["name"],
                        "type": net_obj["type"]
                    }],
                    "gateway": {
                        "id": gw_obj["id"],
                        "name": gw_obj["name"],
                        "type": gw_obj["type"]
                    },
                    "metricValue": 1,
                    "ipType": "IPv4",
                    "type": "staticrouteentry"
                })

                # Route: IOU/IOSv subnet
                net_obj = create_network_object("ftd_iou_iosv", "192.168.220.0/24")
                gw_obj = create_host_object("gw_iou_iosv", "192.168.240.4")

                routes_to_add.append({
                    "name": "route_to_iou_iosv",
                    "iface": {
                        "id": csr_ftd_swagger.id,
                        "name": csr_ftd_swagger.name,
                        "type": "physicalinterface"
                    },
                    "networks": [{
                        "id": net_obj["id"],
                        "name": net_obj["name"],
                        "type": net_obj["type"]
                    }],
                    "gateway": {
                        "id": gw_obj["id"],
                        "name": gw_obj["name"],
                        "type": gw_obj["type"]
                    },
                    "metricValue": 1,
                    "ipType": "IPv4",
                    "type": "staticrouteentry"
                })

                # Route to IOSv-CSR subnet
                net_obj = create_network_object("ftd_iosv_csr", "192.168.230.0/24")
                gw_obj = create_host_object("gw_iosv_csr", "192.168.240.4")

                routes_to_add.append({
                    "name": "route_to_iosv_csr",
                    "iface": {
                        "id": csr_ftd_swagger.id,
                        "name": csr_ftd_swagger.name,
                        "type": "physicalinterface"
                    },
                    "networks": [{
                        "id": net_obj["id"],
                        "name": net_obj["name"],
                        "type": net_obj["type"]
                    }],
                    "gateway": {
                        "id": gw_obj["id"],
                        "name": gw_obj["name"],
                        "type": gw_obj["type"]
                    },
                    "metricValue": 1,
                    "ipType": "IPv4",
                    "type": "staticrouteentry"
                })

            # 2. PUSH ROUTES USING THE CORRECT parentId
            # ==========================================================
            if routes_to_add:
                for route in routes_to_add:
                    print(f"Adding static route '{route['name']}'...")
                    # Pass the fetched device_id as the parentId
                    response = self.swagger.Routing.addStaticRouteEntry(
                        parentId=device_id,
                        body=route
                    ).result()
                    print("Added static route:", response)
            else:
                print("No static routes to add")
                # ==========================================================

        # --- Step 5: Add Access Control Rules ---
        with steps.start("Add Access Control Rules", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return

            policy_id = self.swagger.AccessPolicy.getAccessPolicyList().result()['items'][0].id

            rule1_body = {
                "name": "Allow_Inside_to_Outside", "action": "PERMIT", "enabled": True, "type": "accessrule",
                "sourceZones": [{"id": self.inside_zone.id, "type": "securityzone"}],
                "destinationZones": [{"id": self.outside_zone.id, "type": "securityzone"}]
            }
            self.swagger.AccessPolicy.addAccessRule(parentId=policy_id, body=rule1_body).result()

            rule2_body = {
                "name": "Allow_Outside_to_Inside", "action": "PERMIT", "enabled": True, "type": "accessrule",
                "sourceZones": [{"id": self.outside_zone.id, "type": "securityzone"}],
                "destinationZones": [{"id": self.inside_zone.id, "type": "securityzone"}]
            }
            self.swagger.AccessPolicy.addAccessRule(parentId=policy_id, body=rule2_body).result()
            step.passed("Successfully created bidirectional access rules.")

        # --- Step 6: Deploy All Pending Changes ---
        with steps.start("Deploy Pending Changes", continue_=True) as step:
            if "ftd_interfaces" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return
            deployment_request = {"type": "deploymentrequest", "forceDeploy": True}
            task = self.swagger.Deployment.addDeployment(body=deployment_request).result()
            #print(f"Deployment initiated. Waiting 60 seconds...")
            import time
            time.sleep(60) # Simple wait for the deployment to apply
            step.passed("Deployment assumed complete.")

    @aetest.subsection
    def verify_guest_connectivity_diagnose_csr(self, steps):
        global USER_SELECTION
        """Connects to Guest-1 via Telnet and pings Guest-2."""

        with steps.start(f"Pinging from end devices via Telnet") as step:
            if "ping_end_devices" not in USER_SELECTION:
                step.skipped("User skipped FTD interface configuration")
                return

            # Get the device objects from the testbed
            source_guest = self.tb.devices['UbuntuDockerGuest-1']
            dest_guest = self.tb.devices['UbuntuDockerGuest-2']
            destination_ip = dest_guest.custom['ping_ip']

            ping_success=False

            conn_class=source_guest.connections.get('telnet',{}).get('class',None)
            assert conn_class,'No connection for device {}'.format(source_guest)
            ip = source_guest.connections.telnet.ip.compressed
            port = source_guest.connections.telnet.port

            conn: TelnetConnection = conn_class(ip, port)

            async def setup():
                nonlocal ping_success
                await conn.connect()
                time.sleep(1)
                ping_success = await conn.ping_end_device(destination_ip)
            asyncio.run(setup())

            if ping_success:
                step.passed(f"Successfully pinged {destination_ip}. Found '0% packet loss' in output. No diagnose needed")
            else:
                step.failed(f"Failed to ping {destination_ip}.")
                diag_opt=input("Would you like to start diagnose process? [y/n]: ").lower()
                if diag_opt == "n":
                    step.skipped("User skipped FTD interface configuration")
                    return
                elif diag_opt == "y":
                    print("Starting diagnose process")
                    if "diagnose" not in USER_SELECTION:
                        USER_SELECTION.add("diagnose")

    @aetest.subsection
    def self_diagnose_CSR(self, steps):
        with steps.start("Diagnose CSR", continue_=True) as step: #type: Step
            if "diagnose" not in USER_SELECTION:
                step.skipped("User skipped CSR Diagnose")
                return
            pass

            # --- Step 1: Get the device object and connect ---
            csr_obj=self.tb.devices['CSR']
            conn_class=csr_obj.connections.get('telnet',{}).get('class',None)
            assert conn_class,'No connection for device {}'.format(csr_obj)
            ip = csr_obj.connections.telnet.ip.compressed
            port = csr_obj.connections.telnet.port

            conn: TelnetConnection = conn_class(ip, port)

            #Get information from other devices
            for device in self.tb.devices:
                if self.tb.devices[device].type not in ['router', 'ftd']:
                    continue
                if device == csr_obj:
                    continue
                # get only neighboring interfaces
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name == 'management':
                        continue
                    if 'csr' in self.tb.devices[device].interfaces[interface].link.alias.split('_')[1]:
                        iosv_intf=self.tb.devices[device].interfaces[interface]
                    if 'csr' in self.tb.devices[device].interfaces[interface].link.alias.split('_')[0]:
                        ftd_intf=self.tb.devices[device].interfaces[interface]

            fixes_applied = False

            async def setup():
                nonlocal fixes_applied
                await conn.connect()
                time.sleep(1)
                # --- Step 2: Parse the live configuration to get the 'actual state' ---
                #print("Parsing 'show ip interface' and 'show ip route' from csr_obj...")
                try:
                    csr_interfaces_raw = await conn.get_response('show ip int br')
                    intf_lines = csr_interfaces_raw.splitlines()

                    parsed_routes_raw = await conn.get_response('show run | i ip route')
                    route_lines = parsed_routes_raw.splitlines()
                except Exception as e:
                    step.failed(f"Failed to parse configuration from CSR: {e}")
                    return

                # List to hold any configuration commands needed to fix issues
                commands_to_fix = []

                # --- Step 3: Manual Parsing of Interface IPs ---
                actual_interface_ips = {}
                for line in intf_lines:
                    parts = line.split()
                    if len(parts) > 2 and parts[1][0].isdigit(): # Basic check for a line with an IP
                        actual_interface_ips[parts[0]] = parts[1]

                print(f"Found live interface IPs: {actual_interface_ips}")

                # --- Step 4: Diagnose Interfaces ---
                print("Diagnosing interface configurations...")
                interfaces_to_check = {
                    'GigabitEthernet2': iosv_intf,
                    'GigabitEthernet3': ftd_intf
                }

                for intf_name, peer_intf_config in interfaces_to_check.items():
                    intended_csr_ipv4 = csr_obj.interfaces[intf_name].ipv4
                    peer_ipv4 = peer_intf_config.ipv4

                    # Check if the IPs on the link are in the same subnet
                    if intended_csr_ipv4.network != peer_ipv4.network:
                        print(
                            f"TESTBED MISCONFIGURATION on link for {intf_name}. "
                            f"CSR is on {intended_csr_ipv4.network} but peer is on {peer_ipv4.network}."
                        )

                    # Check if the live IP on CSR matches the intended IP from testbed
                    if actual_interface_ips.get(intf_name) != str(intended_csr_ipv4.ip):
                        print(f"IP MISMATCH on {intf_name}. Generating fix.")
                        commands_to_fix.extend([
                            f'interface {intf_name}',
                            f'ip address {intended_csr_ipv4.ip} {intended_csr_ipv4.netmask}',
                            'no shutdown'
                        ])

                # --- Step 5: Manual Parsing of Static Routes ---
                actual_static_routes = {}
                for line in route_lines:
                    parts = line.split()
                    if len(parts) == 5 and parts[0] == 'ip' and parts[1] == 'route':
                        # ip route <network> <mask> <gateway>
                        network, mask, gateway = parts[2], parts[3], parts[4]
                        prefix = ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
                        actual_static_routes[f"{network}/{prefix}"] = gateway

                print(f"Found live static routes: {actual_static_routes}")

                # --- Step 6: Diagnose Static Routes ---
                print("Diagnosing static routes...")
                expected_routes = {
                    '192.168.210.0/24': '192.168.230.3',
                    '192.168.220.0/24': '192.168.230.3',
                    '192.168.250.0/24': '192.168.240.5',
                }

                for network, gateway in expected_routes.items():
                    if actual_static_routes.get(network) != gateway:
                        print(f"ROUTE MISMATCH for {network}. Generating fix.")
                        net = ipaddress.IPv4Network(network)
                        commands_to_fix.append(f'ip route {net.network_address} {net.netmask} {gateway}')

                # --- Step 7: Apply Fixes if Necessary ---
                if commands_to_fix:
                    fixes_applied = True
                    print(f"Found configuration issues. Applying {len(commands_to_fix)} fixes...")

                    # Prepare commands for configuration mode
                    config_session_commands = ['conf t'] + commands_to_fix + ['end']

                    # Use your existing async method to apply the configuration
                    await conn.enter_commands(config_session_commands, '#')
                    print("Successfully applied configuration fixes.")
                else:
                    print("No configuration issues found on CSR.")

            # --- Run the async setup function ---
            asyncio.run(setup())

            # --- Final step result ---
            if fixes_applied:
                step.passed("Completed diagnose process and applied fixes. Please re-run the ping test.")
            else:
                step.passed("No configuration issues were found on CSR")
if __name__ == "__main__":
    opt=True
    while opt:
        USER_SELECTION = get_user_options()
        print(f"\nSelected: {USER_SELECTION}\n")
        aetest.main()
        flag=True
        while True:
            #opt_input=input("Do you want to continue configuration? [y/n] ")
            opt_input="n"
            if opt_input == "y":
                opt=True
                break
            elif opt_input == "n":
                opt=False
                break
            else:
                print("Please enter y or n")
                continue

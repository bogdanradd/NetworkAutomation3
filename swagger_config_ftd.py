from pyats import aetest, topology
from lib.connectors.swagger_conn import SwaggerConnector


class ConnectFTDREST(aetest.Testcase):
    @aetest.test
    def load_testbed(self, steps):
        with steps.start("Load testbed"):
            self.tb = topology.loader.load('testbed_ftd.yaml')
            self.parent.parameters.update(tb=self.tb)

    @aetest.test
    def connect_via_rest(self, steps):
        with steps.start("Connect via rest"):
            for device in self.tb.devices:
                if self.tb.devices[device].type != 'ftd':
                    continue
                if "swagger" not in self.tb.devices[device].connections:
                    continue
                connection: SwaggerConnector = self.tb.devices[device].connect()
                print(connection)
                swagger = connection.get_swagger_client()
                if not swagger:
                    self.failed('No swagger connection')
                print(swagger)

        # with steps.start("Delete existing DHCP server"):
        #         dhcp_servers = swagger.DHCPServerContainer.getDHCPServerContainerList().result()
        #         for dhcp_server in dhcp_servers['items']:
        #             dhcp_serv_list = dhcp_server['servers']
        #             print(dhcp_serv_list)
        #             dhcp_server.servers = []
        #             response = swagger.DHCPServerContainer.editDHCPServerContainer(
        #                 objId=dhcp_server.id,
        #                 body = dhcp_server,
        #             ).result()
        #             print(response)

        with steps.start('configure FTD Interfaces'):
            existing_interfaces = swagger.Interface.getPhysicalInterfaceList().result()
            ftd_ep2 = connection.device.interfaces['ftd_ep2']
            csr_ftd = connection.device.interfaces['csr_ftd']
            for interface in existing_interfaces['items']:
                if interface.hardwareName == csr_ftd.name:
                    interface.ipv4.ipAddress.ipAddress = csr_ftd.ipv4.ip.compressed
                    interface.ipv4.ipAddress.netmask = csr_ftd.ipv4.netmask.exploded
                    interface.ipv4.dhcp = False
                    interface.ipv4.ipType = 'STATIC'
                    interface.enable = True
                    interface.name = csr_ftd.alias
                    response = swagger.Interface.editPhysicalInterface(
                        objId=interface.id,
                        body = interface,
                    ).result()
                    print(response)

                if interface.hardwareName == ftd_ep2.name:
                    interface.ipv4.ipAddress.ipAddress = ftd_ep2.ipv4.ip.compressed
                    interface.ipv4.ipAddress.netmask = ftd_ep2.ipv4.netmask.exploded
                    interface.ipv4.dhcp = False
                    interface.ipv4.ipType = 'STATIC'
                    interface.enable = True
                    interface.name = ftd_ep2.alias
                    response = swagger.Interface.editPhysicalInterface(
                        objId=interface.id,
                        body=interface,
                    ).result()
                    interface_for_dhcp = interface
                    print(response)
        with steps.start("Configure new DHCP server"):
            dhcp_servers = swagger.DHCPServerContainer.getDHCPServerContainerList().result()
            for dhcp_server in dhcp_servers['items']:
                dhcp_serv_list = dhcp_server['servers']
                print(dhcp_serv_list)
                dhcp_server_model = swagger.get_model('DHCPServer')
                interface_ref_model = swagger.get_model('ReferenceModel')
                dhcp_server.servers = [
                    dhcp_server_model(
                        addressPool='192.168.205.100-192.168.205.200',
                        enableDHCP = True,
                        interface=interface_ref_model(
                            # hardwareName=interface_for_dhcp.hardwareName,
                            id=interface_for_dhcp.id,
                            name=interface_for_dhcp.name,
                            type='physicalinterface',
                            # version='be5gwpeongcmt'
                        ),
                        type='dhcpserver'
                    )
                ]
                response = swagger.DHCPServerContainer.editDHCPServerContainer(
                    objId=dhcp_server.id,
                    body = dhcp_server,
                ).result()
                print(response)

        with steps.start("Add routes"):
            pass

        with steps.start("Add allow rule"):
            pass






if __name__ == '__main__':
    aetest.main()
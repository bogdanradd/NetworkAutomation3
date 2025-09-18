from pyats import aetest, topology


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
                connection = self.tb.devices[device].connect()
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
            for interface in existing_interfaces['items']:
                if interface.hardwareName == connection.device.interfaces['csr_ftd'].name:
                    interface.ipv4.ipAddress.ipAddress = connection.device.interfaces['csr_ftd'].ipv4.ip.compressed
                    interface.ipv4.ipAddress.netmask = connection.device.interfaces['csr_ftd'].ipv4.ip.netmask.exploded
                    interface.ipv4.dhcp = False
                    interface.ipv4.ipType = 'STATIC'
                    interface.enable = True
                    interface.name = connection.device.interfaces['csr_ftd'].alias
                    response = swagger.Interface.editPhysicalInterface(
                        objId=interface.id,
                        body = interface,
                    ).result()
                    print(response)
                print('step')



if __name__ == '__main__':
    aetest.main()
import ipaddress
import json
import requests
import urllib3
import time
from bravado.client import SwaggerClient
from pyats.topology import Device
from bravado.requests_client import RequestsClient
from urllib3.exceptions import InsecureRequestWarning


class SwaggerConnector:

    def __init__(self, device: Device, **kwargs):
        self.device: Device = device
        self.client = None
        self.connected = False
        self._session = None
        self._headers = None
        self._auth = None
        self._url = None
        self.__access_token = None
        self.__refresh_token = None
        self.__token_type = None
        urllib3.disable_warnings(InsecureRequestWarning)

    def connect(self):
        host = self.device.connections.swagger.ip
        port = self.device.connections.swagger.port
        protocol = self.device.connections.swagger.protocol
        self._url = f'{protocol}://{host}:{port}'
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        self.__login()
        self.connected = True
        return self

    def __login(self):
        endpoint = '/api/fdm/latest/fdm/token'
        response = requests.post(
            url=self._url + endpoint,
            headers=self._headers,
            verify=False,
            data=json.dumps(
                {
                'username': self.device.connections.telnet.credentials.login.username,
                'password': self.device.connections.telnet.credentials.login.password.plaintext,
                'grant_type': 'password',
                }
            )
        )
        self.__access_token = response.json()['access_token']
        self.__refresh_token = response.json()['refresh_token']
        self.__token_type = response.json()['token_type']
        self._headers.update({'Authorization': f'{self.__token_type} {self.__access_token}'})

    def get_swagger_client(self):
        endpoint = '/apispec/ngfw.json'
        http_client = RequestsClient()
        http_client.session.verify = False
        http_client.ssl_verify = False
        http_client.session.headers = self._headers
        self.client = SwaggerClient.from_url(
            spec_url=self._url + endpoint,
            http_client=http_client,
            request_headers=self._headers,
            config={'validate_certificate': False, 'validate_responses': False},
        )
        return self.client

    def finish_initial_setup(self):

        body = {
            "type": "initialprovision",
            "id": "default",
            "acceptEULA": True,
            "startTrialEvaluation": True,
            "selectedPerformanceTierId": "FTDv5",
        }

        return self.client.InitialProvision.addInitialProvision(body=body).result()

    def delete_existing_dhcp_sv(self):
        dhcp_servers = self.client.DHCPServerContainer.getDHCPServerContainerList().result()
        for dhcp_server in dhcp_servers['items']:
            dhcp_serv_list = dhcp_server['servers']
            print(dhcp_serv_list)
            dhcp_server.servers = []
            response = self.client.DHCPServerContainer.editDHCPServerContainer(
                objId=dhcp_server.id,
                body=dhcp_server,
            ).result()
            return response

    def configure_ftd_interfaces(self, interface1, interface2):
        existing_interfaces = self.client.Interface.getPhysicalInterfaceList().result()
        responses = []
        for interface in existing_interfaces['items']:
            if interface.hardwareName == interface1.name:
                interface.ipv4.ipAddress.ipAddress = interface1.ipv4.ip.compressed
                interface.ipv4.ipAddress.netmask = interface1.ipv4.netmask.exploded
                interface.ipv4.dhcp = False
                interface.ipv4.ipType = 'STATIC'
                interface.enable = True
                interface.name = interface1.alias
                response1 = self.client.Interface.editPhysicalInterface(
                    objId=interface.id,
                    body=interface,
                ).result()
                responses.append(response1)

            if interface.hardwareName == interface2.name:
                interface.ipv4.ipAddress.ipAddress = interface2.ipv4.ip.compressed
                interface.ipv4.ipAddress.netmask = interface2.ipv4.netmask.exploded
                interface.ipv4.dhcp = False
                interface.ipv4.ipType = 'STATIC'
                interface.enable = True
                interface.name = interface2.alias
                response2 = self.client.Interface.editPhysicalInterface(
                    objId=interface.id,
                    body=interface,
                ).result()
                responses.append(response2)
        return responses

    def configure_new_dhcp_sv(self, iface):
        interface_for_dhcp = None
        existing_interfaces = self.client.Interface.getPhysicalInterfaceList().result()
        for interface in existing_interfaces['items']:
            if interface.hardwareName == iface.name:
                interface_for_dhcp = interface
        dhcp_servers = self.client.DHCPServerContainer.getDHCPServerContainerList().result()
        for dhcp_server in dhcp_servers['items']:
            dhcp_serv_list = dhcp_server['servers']
            print(dhcp_serv_list)
            dhcp_server_model = self.client.get_model('DHCPServer')
            interface_ref_model = self.client.get_model('ReferenceModel')
            dhcp_server.servers = [
                dhcp_server_model(
                    addressPool='192.168.205.100-192.168.205.200',
                    enableDHCP=True,
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
            response = self.client.DHCPServerContainer.editDHCPServerContainer(
                objId=dhcp_server.id,
                body=dhcp_server,
            ).result()
            return response


    def configure_ospf(self, vrf_id, name, process_id,
                           area_id, if_to_cidr):
        """
        Create OSPF process with area 0 and two (or more) areaNetworks, each
        tied to a *distinct* network object matching the interface subnet.
        Example if_to_cidr: [("csr_ftd","192.168.204.0/24"), ("ftd_ep2","192.168.205.0/24")]
        """
        Ref = self.client.get_model("ReferenceModel")

        def ensure_netobj(cidr: str):
            net = ipaddress.ip_network(cidr, strict=False)
            name = f"NET_{net.network_address}_{net.prefixlen}"
            existing = self.client.NetworkObject.getNetworkObjectList(
                filter=f"name:{name}"
            ).result()
            if existing["items"]:
                return existing["items"][0]
            body = {"type": "networkobject", "name": name, "subType": "NETWORK",
                    "value": f"{net.network_address}/{net.prefixlen}"}
            return self.client.NetworkObject.addNetworkObject(body=body).result()

        if_list = self.client.Interface.getPhysicalInterfaceList().result()["items"]
        name_to_if = {i.name: i for i in if_list}

        area_networks = []
        for if_name, cidr in if_to_cidr:
            itf = name_to_if[if_name]
            netobj = ensure_netobj(cidr)
            area_networks.append({
                "type": "areanetwork",
                "ipv4Network": Ref(id=netobj.id, name=netobj.name, type="networkobject"),
                "tagInterface": Ref(
                    id=itf.id, name=itf.name, type="physicalinterface",
                    hardwareName=getattr(itf, "hardwareName", None)
                ),
            })

        body = {
            "type": "ospf",
            "name": name,
            "processId": str(process_id),
            "areas": [{
                "type": "area",
                "areaId": str(area_id),
                "areaNetworks": area_networks,
                "virtualLinks": [],
                "areaRanges": [],
                "filterList": [],
            }],
            "neighbors": [],
            "summaryAddresses": [],
            "redistributeProtocols": [],
            "filterRules": [],
            "logAdjacencyChanges": {"type": "logadjacencychanges", "logType": "DETAILED"},
            "processConfiguration": {
                "type": "processconfiguration",
                "administrativeDistance": {
                    "type": "administrativedistance",
                    "intraArea": 110, "interArea": 110, "external": 110
                },
                "timers": {
                    "type": "timers",
                    "floodPacing": 33,
                    "lsaArrival": 1000,
                    "lsaGroup": 240,
                    "retransmission": 66,
                    "lsaThrottleTimer": {
                        "type": "lsathrottletimer",
                        "initialDelay": 0, "minimumDelay": 5000, "maximumDelay": 5000
                    },
                    "spfThrottleTimer": {
                        "type": "spfthrottletimer",
                        "initialDelay": 5000, "minimumHoldTime": 10000, "maximumWaitTime": 10000
                    }
                }
            }
        }

        return self.client.OSPF.addOSPF(vrfId=vrf_id, body=body).result()

    def deploy(self, force=True):
        res = self.client.Deployment.addDeployment(body={"forceDeploy": True}).result()
        dep_id = getattr(res, "id", None) or res.get("id")

        terminal = {"DEPLOYED", "FAILED", "ERROR", "CANCELLED", "CANCELED"}
        while True:
            cur = self.client.Deployment.getDeployment(objId=dep_id).result()
            state = (getattr(cur, "state", None) or cur.get("state") or "").upper()
            if state in terminal:
                print(getattr(cur, "statusMessage", None) or cur.get("statusMessage"))
                break
            time.sleep(2)






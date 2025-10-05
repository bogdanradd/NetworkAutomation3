"""Unit tests for swagger connector"""
import warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

import unittest
from unittest.mock import MagicMock, patch


class TestCase(unittest.TestCase):
    """Test cases for swagger connection"""

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_connect(self, post_mock):
        """Test swagger connect method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        result = conn.connect()
        self.assertTrue(conn.connected)
        self.assertEqual(conn, result)

    @patch('lib.connectors.swagger_conn.requests.post')
    @patch('lib.connectors.swagger_conn.SwaggerClient.from_url')
    def test_get_swagger_client(self, swagger_client_mock, post_mock):
        """Test get_swagger_client method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_client = MagicMock()
        swagger_client_mock.return_value = mock_client
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        result = conn.get_swagger_client()
        self.assertEqual(mock_client, result)
        self.assertEqual(mock_client, conn.client)

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_finish_initial_setup(self, post_mock):
        """Test finish_initial_setup method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        mock_client = MagicMock()
        mock_client.InitialProvision.addInitialProvision.return_value.result.return_value = {'status': 'success'}
        conn.client = mock_client
        result = conn.finish_initial_setup()
        mock_client.InitialProvision.addInitialProvision.assert_called_once()
        self.assertEqual({'status': 'success'}, result)

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_deploy(self, post_mock):
        """Test deploy method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        mock_client = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 'deploy_123'
        mock_deployment.state = 'DEPLOYED'
        mock_deployment.statusMessage = 'Deployment successful'
        mock_client.Deployment.addDeployment.return_value.result.return_value = mock_deployment
        mock_client.Deployment.getDeployment.return_value.result.return_value = mock_deployment
        conn.client = mock_client
        conn.deploy()
        mock_client.Deployment.addDeployment.assert_called_once_with(body={"forceDeploy": True})

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_delete_existing_dhcp_sv(self, post_mock):
        """Test delete_existing_dhcp_sv method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        mock_client = MagicMock()

        mock_dhcp_server = MagicMock()
        mock_dhcp_server.id = 'dhcp_123'
        mock_dhcp_server.servers = [MagicMock()]
        mock_client.DHCPServerContainer.getDHCPServerContainerList.return_value = {'items': [mock_dhcp_server]}
        mock_client.DHCPServerContainer.editDHCPServerContainer.return_value.result.return_value = {'status': 'success'}
        conn.client = mock_client

        result = conn.delete_existing_dhcp_sv()
        mock_client.DHCPServerContainer.editDHCPServerContainer.assert_called_once()
        self.assertEqual({'status': 'success'}, result)

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_configure_ftd_interfaces(self, post_mock):
        """Test configure_ftd_interfaces method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()

        mock_client = MagicMock()
        mock_interface1 = MagicMock()
        mock_interface1.hardwareName = 'GigabitEthernet0/0'
        mock_interface1.id = 'if1_id'
        mock_interface2 = MagicMock()
        mock_interface2.hardwareName = 'GigabitEthernet0/1'
        mock_interface2.id = 'if2_id'

        mock_client.Interface.getPhysicalInterfaceList.return_value = {'items': [mock_interface1, mock_interface2]}
        mock_client.Interface.editPhysicalInterface.return_value.result.return_value = {'status': 'success'}
        conn.client = mock_client

        interface1 = MagicMock()
        interface1.name = 'GigabitEthernet0/0'
        interface1.alias = 'outside'
        interface1.ipv4.ip.compressed = '192.168.1.1'
        interface1.ipv4.netmask.exploded = '255.255.255.0'

        interface2 = MagicMock()
        interface2.name = 'GigabitEthernet0/1'
        interface2.alias = 'inside'
        interface2.ipv4.ip.compressed = '192.168.2.1'
        interface2.ipv4.netmask.exploded = '255.255.255.0'

        result = conn.configure_ftd_interfaces(interface1, interface2)
        self.assertEqual(2, mock_client.Interface.editPhysicalInterface.call_count)
        self.assertEqual(2, len(result))

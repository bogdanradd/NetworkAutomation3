"""Unit tests for swagger connector"""
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

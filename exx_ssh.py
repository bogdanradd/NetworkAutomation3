from pyats import aetest, topology

from lib.connectors.ssh_conn import SSHConnection


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def load_testbed(self, steps):
        with steps.start("Load testbed"):
            tb = topology.loader.load('testbed1.yaml')
            self.parent.parameters.update(tb=tb)


class ConfigureGenie(aetest.Testcase):
    @aetest.setup
    def connect(self, steps):
        tb = self.parent.parameters.get("tb")
        conn: SSHConnection = tb.devices.CSR.connections.ssh['class'](
            host=str(tb.devices.CSR.connections.ssh['ip']),
            port=str(tb.devices.CSR.connections.ssh['port']),
            username=tb.devices.CSR.connections.ssh.credentials.login['username'],
            password=tb.devices.CSR.connections.ssh.credentials.login['password'].plaintext,
        )
        conn.connect()
        conn.configure()


if __name__ == '__main__':
    aetest.main()
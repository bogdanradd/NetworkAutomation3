from pyats import aetest, topology
from genie.libs.conf.interface.iosxe import Interface
from pyats.topology import Testbed


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def load_testbed(self, steps):
        with steps.start("Load testbed"):
            tb = topology.loader.load('testbed_genie.yaml')
            self.parent.parameters.update(tb=tb)


class ConfigureGenie(aetest.Testcase):
    @aetest.setup
    def test1(self, steps):
        tb: Testbed = self.parent.parameters.get("tb")
        dev = tb.devices.CSR
        dev.connect(log_stdout=True)
        print(dev)

if __name__ == '__main__':
    aetest.main()
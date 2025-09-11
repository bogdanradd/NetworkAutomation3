from lib.connectors.ssh_conn import SSHConnection
import threading

devices = [{'host': '192.168.100.1',
            'port': 22,
            'username': 'admin',
            'password': 'admin',},

            {'host': '192.168.100.2',
            'port': 22,
            'username': 'admin',
            'password': 'admin',}
           ]


def configure_ip(host, port, user, passwd ):
    ssh = SSHConnection(host, port, user, passwd)
    ssh.connect()
    ssh.configure()

threads = []
for device in devices:
    t = threading.Thread(
        target=configure_ip,
        args = (device['host'], device['port'], device['username'], device['password']))
    threads.append(t)
for thd in threads:
    thd.start()
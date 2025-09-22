import time

from netmiko import ConnectHandler


HOST = '192.168.100.1'
PORT = 22

class SSHConnection:

    def __init__(self, host, port, username, password, device_type = 'cisco_ios'):
        self.device_type = device_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.conn = None


    def connect(self):
        self.conn = ConnectHandler(
            device_type=self.device_type,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )
        try:
            self.conn.enable()
        except Exception:
            pass
        self.conn.send_command('terminal length 0')

    def send_config_set(self, commands: list):
        return self.conn.send_config_set(commands)


    def configure(self):
        print(self.conn.send_command('show ip int brief'))


    def close(self):
        if self.conn:
            try:
                self.conn.disconnect()
            finally:
                self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

if __name__ == '__main__':
    conn = SSHConnection(HOST, PORT, 'admin', 'admin')
    conn.connect()
    conn.configure()
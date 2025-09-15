import time

import paramiko


HOST = '192.168.100.1'
PORT = 22

class SSHConnection:

    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh = None


    def connect(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    def configure(self):
        stdin, stdout, stderr = self.ssh.exec_command('show version')
        time.sleep(1)
        print(stdout.read())


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

if __name__ == '__main__':
    conn = SSHConnection(HOST, PORT, 'admin', 'admin')
    conn.connect()
    conn.configure()
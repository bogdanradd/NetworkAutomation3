import asyncio
import time
import telnetlib3
from multiprocessing import Queue
from jinja2 import Environment, FileSystemLoader

HOST = '92.81.55.146'
PORT = 5104  # replace with yours
IOU_CONFIG = {
    "ints": [
        {"name": "e0/0", "ip": "192.168.200.1"},
        {"name": "e0/1", "ip": "192.168.201.1"},
        {"name": "e0/2", "ip": "192.168.202.1"},
    ]
}
IOS_CONFIG = {
    "ints": [
        {"name": "g0/0", "ip": "192.168.200.2"},
        {"name": "g0/1", "ip": "192.168.202.2"},
        {"name": "g0/2", "ip": "192.168.203.2"},
    ]
}
CSR_CONFIG = {
    "ints": [
        {"name": "g1", "ip": "192.168.200.3"},
        {"name": "g2", "ip": "192.168.203.3"},
        {"name": "g3", "ip": "192.168.204.3"},
    ]
}

class TelnetConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    async def connect(self):
        self.reader, self.writer = await telnetlib3.open_connection(self.host, self.port)

    def print_info(self):
        print('Reader: {}'.format(self.reader))
        print('Writer: {}'.format(self.writer))

    async def readuntil(self, separator: str):
        response = await self.reader.readuntil(separator.encode())
        return response.decode()

    async def read(self, n: int):
        return await self.reader.read(n)

    def write(self, data: str):
        self.writer.write(data + '\n')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write('\n')

    async def apply_config(self, path: str):
        with open(path, 'r') as f:
            for line in f.readlines():
                command = line.strip()
                self.write(command + '\r\n')
                out = await self.readuntil('#')
                print(out)

    async def execute_commands(self, command: list, prompt):
        self.write('')
        time.sleep(1)
        init_prompt = await self.read(n = 500)
        if '>' in init_prompt:
            self.write('en')
            await self.readuntil('#')
        for cmd in command:
            self.write(cmd)
            await self.readuntil(prompt)




    async def configure(self, completed: Queue = None, j2_file = "set_ips.j2"):
        pass



if __name__ == '__main__':
    conn = TelnetConnection(HOST, PORT)

    async def main():
        await conn.connect()
        conn.write('\n')
        await conn.readuntil('\n')
        conn.print_info()

    asyncio.run(main())

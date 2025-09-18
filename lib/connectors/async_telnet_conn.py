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
        self.writer.write(data + '\r\n')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write('\n')

    async def apply_config(self, path: str):
        with open(path, 'r') as f:
            for line in f.readlines():
                command = line.strip()
                self.write(command + '\n')
                out = await self.readuntil('#')
                print(out)

    async def execute_commands(self, command: list, prompt: str):
        for cmd in command:
            self.write(cmd + '\n')
            await self.readuntil(prompt)



    async def configure(self, completed: Queue = None, j2_file = "set_ips.j2"):
        self.write('\n')
        await self.readuntil('#')

        self.write('conf t\n')
        prompt = await self.readuntil('(config)#')

        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(j2_file)


        if "IOU" in prompt:
            with open("IOU.txt", "w") as f:
                f.write(template.render(IOU_CONFIG))

            await self.apply_config("IOU.txt")
            # completed.put({"IOU1": "192.168.100.1"})

        elif "IOSV" in prompt:
            with open("IOS.txt", "w") as f:
                f.write(template.render(IOS_CONFIG))

            await self.apply_config("IOS.txt")

        elif "Router" in prompt:
            with open("CSR.txt", "w") as f:
                f.write(template.render(CSR_CONFIG))

            await self.apply_config("CSR.txt")

            # completed.put({"Router": "192.168.100.2"})


if __name__ == '__main__':
    conn = TelnetConnection(HOST, PORT)

    async def main():
        await conn.connect()
        conn.write('\n')
        await conn.readuntil('\n')
        conn.print_info()

    asyncio.run(main())

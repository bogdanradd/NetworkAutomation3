import asyncio
import re
import time
import telnetlib3

HOST = '92.81.55.146'
PORT = 5104

def render_commands(templates, **kwargs):
    return [str(t).format(**kwargs) for t in templates]

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


    async def execute_commands(self, command: list, prompt):
        output = []
        self.write('')
        time.sleep(1)
        init_prompt = await self.read(n = 500)
        self.write('terminal length 0')
        time.sleep(1)
        if '>' in init_prompt:
            self.write('en')
            out = await self.readuntil('#')
            output.append(out)
        for cmd in command:
            self.write(cmd)
            out = await self.readuntil(prompt)
            output.append(out)
        return output


    async def configure_ssh(self, templates, prmt, **kwargs):
        commands = render_commands(templates, **kwargs)
        return await self.execute_commands(commands, prmt)

    async def configure_ftd(self,
                            hostname,
                            ip,
                            netmask,
                            gateway,
                            password,
                            ):
        self.write('')
        time.sleep(1)
        out = await self.read(n=1000)
        time.sleep(1)
        print(out)
        result = re.search(r'^\s*(?P<login>firepower login:)', out)
        if result.group('login'):
            self.write('admin')
            time.sleep(1)
            self.write('Admin123')
            time.sleep(5)

        out = await self.read(n=1000)
        time.sleep(1)
        if 'Press <ENTER> to display the EULA: ' in out:
            self.write('')
            while True:
                time.sleep(1)
                out = await self.read(n=1000)
                if '--More--' in out:
                    self.write(' ')
                elif "Please enter 'YES' or press <ENTER> to AGREE to the EULA: " in out:
                    self.write('')
                    time.sleep(2)
                    out = await self.read(n=1000)
                    break
                else:
                    print('No string found in output')

        if 'password:' in out:
            self.write(password)
            time.sleep(2)
            out = await self.read(n=1000)
            if 'password:' in out:
                self.write(password)
                time.sleep(3)
                out = await self.read(n=1000)

        if 'IPv4? (y/n) [y]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)
        if 'IPv6? (y/n) [n]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)
        if '[manual]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)
        if '[192.168.45.45]:' in out:
            self.write(ip)
            time.sleep(1)
            out = await self.read(n=1000)
        if '[255.255.255.0]:' in out:
            self.write(netmask)
            time.sleep(1)
            out = await self.read(n=1000)
        if '[192.168.45.1]:' in out:
            self.write(gateway)
            time.sleep(1)
            out = await self.read(n=1000)
        if '[firepower]:' in out:
            self.write(hostname)
            time.sleep(1)
            out = await self.read(n=1000)
        if '::35]:' in out:
            self.write(gateway)
            time.sleep(1)
            out = await self.read(n=1000)
        if "'none' []:" in out:
            self.write('')
            time.sleep(10)
            out = await self.read(n=1000)
        if 'Manage the device locally? (yes/no) [yes]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)



if __name__ == '__main__':
    conn = TelnetConnection(HOST, PORT)

    async def main():
        await conn.connect()
        conn.write('\n')
        await conn.readuntil('\n')
        conn.print_info()

    asyncio.run(main())

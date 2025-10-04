"""This module represents a connector for telnet connections"""

import asyncio
import re
import time
import telnetlib3



def render_commands(templates, **kwargs):
    """This method is used to render commands and format them"""
    return [str(t).format(**kwargs) for t in templates]


class TelnetConnection:
    """This class is used to take care of the telnet connection"""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    def __enter__(self):
        return self

    async def connect(self):
        """This method is used to connect through telnet and return the reader and writer"""
        self.reader, self.writer = await telnetlib3.open_connection(self.host, self.port)

    async def readuntil(self, separator: str):
        """This method is used to read until command is received"""
        response = await self.reader.readuntil(separator.encode())
        return response.decode()

    async def read(self, n: int):
        """This method is used to read n bytes"""
        return await self.reader.read(n)

    def write(self, data: str):
        """This method is used to send commands in CLI"""
        self.writer.write(data + '\n')


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write('\n')

    async def execute_commands(self, command: list, prompt):
        """This method is used to execute certain sets of commands in CLI"""
        output = []
        time.sleep(1)
        self.write('\r')
        time.sleep(1)
        init_prompt = await self.read(n=500)
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
        """This method is used to configure SSH on devices"""
        commands = render_commands(templates, **kwargs)
        return await self.execute_commands(commands, prmt)

    async def initialize_csr(self):
        """This method is used to initialize CSR"""
        self.write('\r')
        time.sleep(1)
        out = await self.read(n=1000)
        if 'dialog? [yes/no]' in out:
            self.write('no')
            time.sleep(2)
            out = await self.read(n=1000)
        if 'autoinstall? [yes]' in out:
            self.write('')
            time.sleep(20)

    async def configure_ftd(self, hostname, ip, netmask, gateway, password):
        """This method is used to configure FTD initial setup"""
        self.write('')
        time.sleep(1)
        out = await self.read(n=1000)
        time.sleep(1)
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
            time.sleep(15)
            out = await self.read(n=1000)
        if 'Manage the device locally? (yes/no) [yes]:' in out:
            self.write('')
            time.sleep(15)

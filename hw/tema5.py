from lib.connectors.telnet_con import TelnetConnection
import asyncio

HOST = '92.81.55.146'
PORT = 5104

IOU1_CONFIG = {
    'e0/0': '192.168.200.1',
    'e0/1': '192.168.201.1',
    'e0/2': '192.168.202.1',
}


async def add_ips(conn: TelnetConnection):
    conn.write('\n')
    await conn.readuntil('IOU1#')
    conn.write('conf t')
    await conn.readuntil('IOU1(config)#')
    for key, val in IOU1_CONFIG.items():
        conn.write(f'int {key}')
        await conn.readuntil('IOU1(config-if)#')
        conn.write(f'ip add {val} 255.255.255.0')
        await conn.readuntil('IOU1(config-if)#')
        conn.write('no sh')
        await conn.readuntil('IOU1(config-if)#')
    conn.write('end')
    await conn.readuntil('IOU1#')

async def dhcp_sv(conn: TelnetConnection):
    conn.write('\n')
    await conn.readuntil('IOU1#')
    conn.write('conf t')
    await conn.readuntil('IOU1(config)#')
    conn.write('ip dhcp pool ETH0/1')
    await conn.readuntil('IOU1(dhcp-config)#')
    conn.write('network 192.168.201.0 255.255.255.0')
    await conn.readuntil('IOU1(dhcp-config)#')
    conn.write('default-router 192.168.201.1')
    await conn.readuntil('IOU1(dhcp-config)#')
    conn.write('exit')
    await conn.readuntil('IOU1(config)#')
    conn.write('ip dhcp excluded-address 192.168.201.1 192.168.201.9')
    await conn.readuntil('IOU1(config)#')
    conn.write('end')
    await conn.readuntil('IOU1#')

async def ssh_config(conn: TelnetConnection):
    conn.write('\n')
    await conn.readuntil('IOU1#')
    conn.write('conf t')
    await conn.readuntil('IOU1(config)#')
    conn.write('username admin password pynet3')
    await conn.readuntil('IOU1(config)#')
    conn.write('ip domain name example.com')
    await conn.readuntil('IOU1(config)#')
    conn.write('line vty 0 4')
    await conn.readuntil('IOU1(config-line)#')
    conn.write('transport input ssh')
    await conn.readuntil('IOU1(config-line)#')
    conn.write('login local')
    await conn.readuntil('IOU1(config-line)#')
    conn.write('exit')
    await conn.readuntil('IOU1(config)#')
    conn.write('crypto key generate rsa modulus 2048')
    await conn.readuntil('IOU1(config)#')
    conn.write('ip ssh version 2')
    await conn.readuntil('IOU1(config)#')
    conn.write('enable secret pynet3')
    await conn.readuntil('IOU1(config)#')
    conn.write('end')
    await conn.readuntil('IOU1#')



async def main():
    conn = TelnetConnection(HOST, PORT)
    await conn.connect()
    await add_ips(conn)
    await dhcp_sv(conn)
    await ssh_config(conn)

asyncio.run(main())
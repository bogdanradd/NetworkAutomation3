import time

from tema6 import ParseConfig
from lib.connectors.async_telnet_conn import TelnetConnection
import asyncio

HOST = '92.81.55.146'
PORT = [5011, 5005]

def get_current_configs():
    with ParseConfig('iou1_running_config.txt') as config:
        config.reduce_config()
        config.rewrite_file()
    with ParseConfig('iosv_running_config.txt') as config:
        config.reduce_config()
        config.rewrite_file()

async def reset_to_factory(conn: TelnetConnection):
    conn.write('')
    prompt = await conn.readuntil('#')
    if '(config' in prompt:
        conn.write('end')
        await conn.readuntil('#')
    conn.write('erase startup-config\n')
    await conn.readuntil('#')
    conn.write('reload')
    await conn.readuntil('[yes/no]:')
    conn.write('no')
    await conn.readuntil('[confirm]')
    conn.write('')
    await conn.readuntil('[yes/no]:')
    conn.write('no')
    await conn.readuntil('[yes]')
    conn.write('')
    time.sleep(15)

async def get_current_config(conn: TelnetConnection):
    conn.write('')
    await conn.readuntil('>')
    conn.write('en')
    await conn.readuntil('#')
    conn.write('sh run')
    out = await conn.read(1000)
    while '--More--' in out:
        conn.write(' ')
        out = await conn.read(1000)




async def main():
    get_current_configs()
    conn1= TelnetConnection(HOST, PORT[0])
    await conn1.connect()
    await reset_to_factory(conn1)
    conn2= TelnetConnection(HOST, PORT[1])
    await conn2.connect()
    await reset_to_factory(conn2)


asyncio.run(main())




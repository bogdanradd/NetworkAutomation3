import time

from tema6 import ParseConfig
from lib.connectors.async_telnet_conn import TelnetConnection
import asyncio

HOST = '92.81.55.146'
PORT = [5104, 5105]

def get_current_configs():
    with ParseConfig('iou1_running_config.txt') as config:
        config.reduce_config()
        config.rewrite_file()
    with ParseConfig('iosv_running_config.txt') as config:
        config.reduce_config()
        config.rewrite_file()

async def reset_to_factory(conn: TelnetConnection):
    conn.write('\n')
    await conn.readuntil('#')
    conn.write('erase startup-config\n\n')
    await conn.readuntil('#')
    conn.write('reload\n\n')
    time.sleep(10)
    await conn.connect()
    conn.write('no\n')
    conn.write('yes\n')
    time.sleep(5)
    conn.write('\n\n')
    await conn.readuntil('>')
    conn.write('en\n')
    await conn.readuntil('#')

get_current_configs()

async def main():
    conn1= TelnetConnection(HOST, PORT[0])
    await conn1.connect()
    await reset_to_factory(conn1)

asyncio.run(main())




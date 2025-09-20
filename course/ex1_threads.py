# configure in different threads different interfaces on same IOU1 device

import threading
import asyncio
from lib.connectors.async_telnet_conn import TelnetConnection

HOST = "92.81.55.146"
PORT = 5104
lock = threading.Lock()

async def config_int(interface, ip):
    conn = TelnetConnection(HOST, PORT)
    await conn.connect()

    conn.write('\n')
    await conn.readuntil('#')
    conn.write('conf t\n')
    await conn.readuntil('(config)#')
    conn.write(f'int {interface}\n')
    await conn.readuntil('(config-if)#')
    conn.write(f'ip add {ip} 255.255.255.0\n')
    await conn.readuntil('(config-if)#')
    conn.write('no sh\n')
    await conn.readuntil('(config-if)#')
    conn.write('end\n')
    await conn.readuntil('#')

def config_threads(interface, ip):
    with lock:
        asyncio.run(config_int(interface, ip))

t1 = threading.Thread(target=config_threads, args =('e0/0', '192.168.100.1'))
t2 = threading.Thread(target=config_threads, args =('e0/1', '192.168.101.1'))
t1.start()
t2.start()
t1.join()
t2.join()







import asyncio
import os
import time
import re
import subprocess
from multiprocessing import Queue, Process

from lib.connectors.async_telnet_conn import TelnetConnection


PORTS = [5104, 5105]
HOST = "92.81.55.146"
CONNS: list[TelnetConnection] = []

for port in PORTS:
    CONNS.append(
        TelnetConnection(HOST, port)
    )

async def producer(q: Queue):

    await asyncio.gather(*(conn.connect() for conn in CONNS))
    await asyncio.gather(*(conn.configure(q) for conn in CONNS))


def ping_device(ip):
    print(f'Pinging {ip}...')
    subprocess.run(['ping', '-c', '4', ip])

def consumer(q: Queue):
    while not q.empty():
        msg = q.get()
        ip = next(iter(msg.values()))
        ping_device(ip)
    print(f'Consumer {os.getpid()} done')

if __name__ == '__main__':
    q = Queue()
    asyncio.run(producer(q))
    # p1 = Process(target = consumer, args = (q,))
    # p2 = Process(target = consumer, args = (q,))
    # p1.start()
    # p2.start()
    # p1.join()
    # p2.join()

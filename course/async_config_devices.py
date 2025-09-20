#connect to all devices in list
#call function to configure management interface
#close all connections
import asyncio
from lib.connectors.async_telnet_conn import TelnetConnection

HOST = "92.81.55.146"
PORTS = [5104, 5105]
CONNS: list[TelnetConnection] = []

for port in PORTS:
    CONNS.append(
        TelnetConnection(HOST, port)
    )

async def main():
    await asyncio.gather(*(con.connect() for con in CONNS))
    await asyncio.gather(*(con.configure() for con in CONNS))





asyncio.run(main())
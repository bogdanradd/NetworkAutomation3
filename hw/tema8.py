import time
import asyncio
from project.config_helper import ParseConfig
from lib.connectors.async_telnet_conn import TelnetConnection

HOST = '92.81.55.146'
PORT = 5011



def get_current_configs():
    with ParseConfig('iou1_running_config.txt') as config:
        config.reduce_config()
        config.rewrite_file()
    return 'iou1_running_config.txt'


async def reset_to_factory(conn: TelnetConnection):
    conn.write('')
    prompt = await conn.readuntil('#')
    if '(config' in prompt:
        conn.write('end')
        await conn.readuntil('#')
    conn.write('erase startup-config\n')
    await conn.readuntil('#')
    conn.write('reload')
    out = await conn.read(n=1000)
    if '[yes/no]' in out:
        conn.write('no')
        await conn.readuntil('[confirm]')
        conn.write('')
    else:
        conn.write('')
    await conn.readuntil('[yes/no]:')
    conn.write('no')
    await conn.readuntil('[yes]')
    conn.write('')
    time.sleep(15)


async def get_current_config(conn: TelnetConnection):
    conn.write('')
    prompt = await conn.read(n=1000)
    if '>' in prompt:
        conn.write('en')
        await conn.readuntil('#')
    conn.write('terminal length 0')
    await conn.readuntil('#')
    conn.write('sh run')
    out = await conn.readuntil('#')
    with open('iou1_current_config.txt', 'w') as f:
        f.write(out)
    return 'iou1_current_config.txt'


def compare_configs(config1, config2):
    missing_blocks = []
    with ParseConfig(config1) as old_config, ParseConfig(config2) as new_config:
        old_config.reduce_config()
        new_config.reduce_config()

        for line in old_config.lines:
            if line.startswith("interface "):
                block = old_config.get_config_block(line.strip())
                block_in_new = new_config.get_config_block(line.strip())
                if not block_in_new:
                    missing_blocks.append(block)
                elif block != block_in_new:
                    missing_lines = [
                        l for l in block.splitlines(True)
                        if l not in block_in_new
                    ]
                    if missing_lines:
                        missing_blocks.append(''.join(missing_lines))
            elif line not in new_config.lines:
                missing_blocks.append(line)

    return missing_blocks



async def apply_missing_config(conn: TelnetConnection, missing_blocks):
    conn.write('conf t')
    await conn.readuntil('(config)#')

    current_mode = 'global'

    for block in missing_blocks:
        for raw in block.splitlines():
            line = raw.strip()
            if not line:
                continue

            # --- ENTER SUBMODES ---
            if line.startswith('ip dhcp pool '):
                if current_mode != 'dhcp':
                    conn.write(line)
                    await conn.readuntil('(dhcp-config)#')
                    current_mode = 'dhcp'
                continue
            if line.startswith('interface '):
                if current_mode != 'interface':
                    conn.write(line)
                    await conn.readuntil('(config-if)#')
                    current_mode = 'interface'
                continue
            if line.startswith('line vty '):
                if current_mode != 'line':
                    conn.write(line)
                    await conn.readuntil('(config-line)#')
                    current_mode = 'line'
                continue

            # --- EXIT if wrong mode for this command ---
            if current_mode == 'dhcp' and not line.startswith(('network', 'default-router', 'dns-server')):
                conn.write('exit')
                await conn.readuntil('(config)#')
                current_mode = 'global'
            if current_mode == 'interface' and not line.startswith(('ip address', 'no shutdown', 'shutdown', 'description')):
                conn.write('exit')
                await conn.readuntil('(config)#')
                current_mode = 'global'
            if current_mode == 'line' and not line.startswith(('exec-timeout', 'privilege level', 'login')):
                conn.write('exit')
                await conn.readuntil('(config)#')
                current_mode = 'global'

            # --- SEND command ---
            conn.write(raw)
            await conn.readuntil('(config')

    # --- EXIT any leftover submode ---
    if current_mode != 'global':
        conn.write('exit')
        await conn.readuntil('(config)#')

    conn.write('end')
    await conn.readuntil('#')
    conn.write('wr')
    await conn.readuntil('#')

async def main():
    golden_config = get_current_configs()
    conn1 = TelnetConnection(HOST, PORT)
    await conn1.connect()

    current_config = await get_current_config(conn1)
    missing_blocks = compare_configs(golden_config, current_config)

    if missing_blocks:
        print("Applying missing configuration...")
        await apply_missing_config(conn1, missing_blocks)
    else:
        print("Device is already configured like earlier.")


asyncio.run(main())

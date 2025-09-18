import subprocess
import re
import time

result = subprocess.run(['ip', 'addr', 'show'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                        )
# print(result.stdout)
have_ip = re.compile(r'inet.*ens4')
ip_done = None
try:
    response = re.search(have_ip, result.stdout)
    print(response.group(0))
except Exception as e:
    print('ens4 does not have an ip add\nadding one...')
    sudo_job = subprocess.Popen(['sudo', 'su'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                shell=True
                                )
    time.sleep(1)
    std_out, std_err = sudo_job.communicate("osboxes.org")
    print(std_out)

    ip_done = subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.200.254/24', 'dev', 'ens4'])

    ens4_up = subprocess.run(['sudo', 'ip', 'link', 'set', 'dev', 'ens4', 'up'])


result = subprocess.run(['ip', 'addr', 'show'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                        )
try:
    result = re.search(have_ip, result.stdout).group(0).split()[1].split('/')[0]
    print(f'the ip address is: {result}')
except Exception as e:
    print('ip was tried to be given, though somehow failed' + str(e))

try:
    add_route = subprocess.run(['sudo', 'ip', 'route', 'add', '192.168.201.0/24', 'via', '192.168.200.1'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True,
                               check=True)
    print(add_route.stdout)
except Exception as e:
    print('Route was already added')

try:
    print("Incoming ping...")
    ping = subprocess.run(['ping', '-c', '4', '192.168.200.4'],
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          text=True,
                          check=True)
    print(ping.stdout)
except Exception as e:
    print('Ping failed :(', str(e))
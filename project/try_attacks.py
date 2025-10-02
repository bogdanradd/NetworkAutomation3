import os
import subprocess
import threading
import time

REMOTE = 'osboxes@192.168.201.100'
SSH_KEY = f"/home/{os.environ['SUDO_USER']}/.ssh/guest2_ed25519"


def run_ping():
    ping = subprocess.Popen(['ping','-c','15', '192.168.200.1'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            text=True
                            )
    for line in ping.stdout:
        print(line, end='')
    ping.wait()


def run_nmap():
    nmap = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'sudo', '-n', 'nmap', '-sS', '--top-ports', '100', '-T4', '192.168.200.0/24',
        ],
        capture_output=True, text=True
    )
    print(nmap.stdout)


def run_dos():
    dos = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'sudo', '-n', 'timeout', '10s', 'hping3', '-S', '-p', '80', '--flood', '-q', '192.168.200.254',
        ],
        capture_output=True, text=True
    )
    print(dos.stdout)
    print(dos.stderr)

def ping_and_dos():
    t1 = threading.Thread(target=run_ping)
    t2 = threading.Thread(target=run_dos)
    t1.start()
    time.sleep(3.5)
    print("Incoming DOS...")
    t2.start()
    t1.join()
    t2.join()


if __name__ == '__main__':
    t1 = threading.Thread(target=run_ping)
    t2 = threading.Thread(target=run_dos)
    t1.start()
    time.sleep(2)
    t2.start()
    t1.join()
    t2.join()

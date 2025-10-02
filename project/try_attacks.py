"""This module is used to define every attack"""

import os
import subprocess
import threading
import time

REMOTE = 'osboxes@192.168.201.100'
SSH_KEY = f"/home/{os.environ['SUDO_USER']}/.ssh/guest2_ed25519"


def test_ssh_acl():
    dos = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'ssh', '-l', 'admin', '192.168.201.1'
        ],
        capture_output=True,
        text=True,
    )
    print(dos.stdout)

def run_ping_1():
    """This method is used to send a ping from the main container to DockerGuest-1"""
    with (subprocess.Popen(['ping', '-c', '15', '192.168.205.100'],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           stdin=subprocess.PIPE,
                           text=True,
                           )
    ) as ping:
        for line in ping.stdout:
            print(line, end='')
        ping.wait()


def run_ping_2():
    """This method is used to send a ping from Attacker to DockerGuest-1"""
    dos = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'ping', '-c', '5', '192.168.205.100'
        ],
        capture_output=True,
        text=True,
    )
    print(dos.stdout)


def run_nmap():
    """This method is used to launch a nmap from Attacker to DockerGuest-1"""
    nmap = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'sudo', '-n', 'nmap', '-sS', '--top-ports', '5', '-T5', '192.168.205.100',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    print(nmap.stdout)


def run_dos():
    """This method is used to launch a DoS attack from Attacker to DockerGuest-1"""
    dos = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'sudo', '-n', 'timeout', '10s', 'hping3', '-S', '-p', '80', '--flood', '-q', '192.168.205.100',
        ],
        capture_output=True,
        text=True,
    )
    print(dos.stdout)
    print(dos.stderr)


def ping_and_dos():
    """This method combines both PING and DoS and runs them in separate Threads"""
    t1 = threading.Thread(target=run_ping_1)
    t2 = threading.Thread(target=run_dos)
    t1.start()
    time.sleep(3.5)
    print("Incoming DOS...")
    t2.start()
    t1.join()
    t2.join()

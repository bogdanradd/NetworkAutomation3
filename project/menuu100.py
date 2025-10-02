import sys
import subprocess
import pathlib
from try_attacks import run_ping, run_nmap, run_dos, ping_and_dos


def configure_devices():
    script = pathlib.Path("/tmp/pycharm_project_844/project/menu_main_script.py")
    subprocess.run([sys.executable, str(script)], check=False)


def display_menu():
    while True:
        print("""
        ############### MENU ###############\n
        1) Configure devices
        2) Run PING from main container to IOU1
        3) Run NMAP from Attacker to 192.168.200.0/24
        4) Run DOS from Attacker to 192.168.200.254
        5) Run PING and DOS at the same time
        0) Exit
        """)

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            try:
                configure_devices()
            except Exception as e:
                print('Configuration script failed', e)
        elif choice == '2':
            try:
                run_ping()
            except Exception as e:
                print('Failed to send PING', e)
        elif choice == '3':
            try:
                run_nmap()
            except Exception as e:
                print('Failed to send NMAP', e)
        elif choice == '4':
            try:
                run_dos()
            except Exception as e:
                print('Failed to send DOS', e)
        elif choice == '5':
            try:
                ping_and_dos()
            except Exception as e:
                print('Failed to run PING and DOS', e)
        elif choice == '0':
            break


if __name__ == '__main__':
    display_menu()

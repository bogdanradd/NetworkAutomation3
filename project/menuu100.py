"""This module displays a menu and interacts with the user"""

import sys
import subprocess
import pathlib
from try_attacks import run_ping_1, run_ping_2, run_nmap, run_dos, ping_and_dos, test_ssh_acl


def configure_devices():
    """This method runs the pyats script that configures the devices"""
    script = pathlib.Path("/tmp/pycharm_project_844/project/menu_main_script.py")
    subprocess.run([sys.executable, str(script)], check=False)

def configure_ftd_defence():
    """This method runs the pyats script that configures FTD defence policies"""
    script = pathlib.Path("/tmp/pycharm_project_844/project/add_defence_ftd.py")
    subprocess.run([sys.executable, str(script)], check=False)



def display_menu():
    """This method displays the menu and calls the desired function"""
    while True:
        print("""
        ############### MENU ###############\n
        1) Configure devices
        2) Run PING from main container to DockerGuest-1
        3) Run PING from Attacker to DockerGuest-1
        4) Run NMAP from Attacker to DockerGuest-1
        5) Run DOS from Attacker to DockerGuest-1
        6) Run PING and DOS at the same time
        7) Add defence policies on FTD
        8) Test SSH ACL (Attacker -> IOU1)
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
                run_ping_1()
            except Exception as e:
                print('Failed to send PING', e)
        elif choice == '3':
            try:
                run_ping_2()
            except Exception as e:
                print('Failed to send PING', e)
        elif choice == '4':
            try:
                run_nmap()
            except Exception as e:
                print('Failed to send NMAP', e)
        elif choice == '5':
            try:
                run_dos()
            except Exception as e:
                print('Failed to send DOS', e)
        elif choice == '6':
            try:
                ping_and_dos()
            except Exception as e:
                print('Failed to run PING and DOS', e)
        elif choice == '7':
            try:
                configure_ftd_defence()
            except Exception as e:
                print('Failed to configure FTD defence', e)
        elif choice == '8':
            try:
                test_ssh_acl()
            except Exception as e:
                print('Failed to test SSH ACL', e)
        elif choice == '0':
            break


if __name__ == '__main__':
    display_menu()

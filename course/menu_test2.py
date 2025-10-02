#!/usr/bin/env python3
"""
Menu that runs **specific parts** of the refactored AEtest script via --uids.
Targets `configure_all_option_b.py`. You get full pyATS banners & summary for
exactly the selected tests.
"""

import sys
import subprocess
from pathlib import Path

SCRIPT = "menu_test.py"   # path to the refactored script
LOAD   = "CommonSetup.load_testbed"     # always run setup first

MENU = (
    """
1) Configure container networking (server IF + routes)
2) Configure SSH on devices (via Telnet bootstrap)
3) Bring up FTD management (via Telnet)
------------------------------------------
4) Genie: configure CSR interfaces
5) Genie: configure OSPF on CSR
6) Genie: configure SSH ACL on CSR
------------------------------------------
7) SSH: configure router interfaces (IP + no shut)
8) SSH: configure OSPF on routers
9) SSH: configure SSH ACL on routers
------------------------------------------
10) Swagger: connect & initial setup (FTD)
11) Swagger: delete existing DHCP server (FTD)
12) Swagger: configure FTD interfaces
13) Swagger: configure new DHCP server (FTD)
14) Swagger: configure OSPF on FTD
15) Swagger: deploy pending changes (FTD)
------------------------------------------
a) Run ALL Genie (4,5,6)
b) Run ALL SSH (7,8,9)
c) Run ALL Swagger (10..15 in order)
q) Quit
"""
)

UIDS = {
    # Single actions (match class.method names in configure_all_option_b.py)
    "1": ["Container.bring_up_server_interface"],
    "2": ["TelnetBootstrap.configure_ssh"],
    "3": ["FTDMgmt.bring_up_ftd_interface"],
    "4": ["GenieCSR.configure_other_interfaces"],
    "5": ["GenieCSR.configure_ospf"],
    "6": ["GenieCSR.configure_ssh_acl"],
    "7": ["SSHRouters.configure_interfaces"],
    "8": ["SSHRouters.configure_ospf"],
    "9": ["SSHRouters.configure_acl"],
    "10": ["SwaggerFTD.connect_and_initial_setup"],
    "11": ["SwaggerFTD.delete_existing_dhcp"],
    "12": ["SwaggerFTD.configure_ftd_interfaces"],
    "13": ["SwaggerFTD.configure_new_dhcp"],
    "14": ["SwaggerFTD.configure_ospf"],
    "15": ["SwaggerFTD.deploy"],
    # Batches
    "a": [
        "GenieCSR.configure_other_interfaces",
        "GenieCSR.configure_ospf",
        "GenieCSR.configure_ssh_acl",
    ],
    "b": [
        "SSHRouters.configure_interfaces",
        "SSHRouters.configure_ospf",
        "SSHRouters.configure_acl",
    ],
    "c": [
        "SwaggerFTD.connect_and_initial_setup",
        "SwaggerFTD.delete_existing_dhcp",
        "SwaggerFTD.configure_ftd_interfaces",
        "SwaggerFTD.configure_new_dhcp",
        "SwaggerFTD.configure_ospf",
        "SwaggerFTD.deploy",
    ],
}

def _check_script():
    if not Path(SCRIPT).exists():
        print(f"[FATAL] Can't find '{SCRIPT}'. Adjust SCRIPT path.")
        sys.exit(1)


def run(uids):
    final = [LOAD] + uids
    cmd = [sys.executable, SCRIPT, "--uids", ";".join(final)]
    print("\n>>> ", " ".join(cmd))
    print("--- BEGIN pyATS OUTPUT ---")
    rc = subprocess.run(cmd).returncode
    print("--- END pyATS OUTPUT ---\n")
    if rc != 0:
        print(f"[WARN] pyATS exited with code {rc}")


def main():
    _check_script()
    while True:
        print(MENU)
        choice = input("Select an option: ").strip().lower()
        if choice == 'q':
            print('Bye.')
            break
        if choice not in UIDS:
            print('Unknown option. Try again.')
            continue
        run(UIDS[choice])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(130)

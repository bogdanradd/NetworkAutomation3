import textwrap
from pyats import aetest

# Import your pyATS test script
import menu_main_script as testscript


from pyats import aetest

def run_uids(uids_to_run):
    """
    Run a subset of sections by UID in the testscript.
    Always run 'common_setup' as the parent of its subsections.
    """
    # requested leaf uids
    requested = list(dict.fromkeys(uids_to_run))  # keep order, dedupe
    # make sure parent is included so subsections can run
    targets = set(requested) | {"common_setup"}

    print("\n=== Running the following sections ===")
    for uid in ["common_setup.load_testbed", *requested]:
        print(f" - {uid}")
    print("======================================\n")

    def uid_filter(node):
        # node may be a string or an object with .uid
        uid = getattr(node, "uid", node)
        if not isinstance(uid, str):
            uid = str(uid)

        # allow exact target, any parent of a target, or any child of a target
        if uid in targets:
            return True
        for t in targets:
            if uid.startswith(t + ".") or t.startswith(uid + "."):
                return True
        return False

    try:
        aetest.main(module=testscript, uids=uid_filter)
    except SystemExit as exc:
        rc = getattr(exc, "code", 0)
        print(f"\n(pyATS finished with exit code {rc})\n")


def menu():
    choices = textwrap.dedent(
        """
        ================== MENU ==================
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
        ==========================================
        """
    )

    mapping = {
        # Container / bootstrap
        "1": ["common_setup.bring_up_server_interface"],
        "2": ["common_setup.configure_ssh"],
        "3": ["common_setup.bring_up_ftd_interface"],

        # Genie
        "4": ["common_setup.genie_configure_other_interfaces"],
        "5": ["common_setup.genie_configure_ospf"],
        "6": ["common_setup.genie_configure_ssh_acl"],

        # SSH
        "7": ["common_setup.ssh_configure_interfaces"],
        "8": ["common_setup.ssh_configure_ospf"],
        "9": ["common_setup.ssh_configure_acl"],

        # Swagger (FTD)
        "10": ["common_setup.swagger_connect_and_initial_setup"],
        "11": ["common_setup.swagger_delete_existing_dhcp"],
        "12": ["common_setup.swagger_configure_ftd_interfaces"],
        "13": ["common_setup.swagger_configure_new_dhcp"],
        "14": ["common_setup.swagger_configure_ospf"],
        "15": ["common_setup.swagger_deploy"],

        # Bundles
        "a": [
            "common_setup.genie_configure_other_interfaces",
            "common_setup.genie_configure_ospf",
            "common_setup.genie_configure_ssh_acl",
        ],
        "b": [
            "common_setup.ssh_configure_interfaces",
            "common_setup.ssh_configure_ospf",
            "common_setup.ssh_configure_acl",
        ],
        "c": [
            "common_setup.swagger_connect_and_initial_setup",
            "common_setup.swagger_delete_existing_dhcp",
            "common_setup.swagger_configure_ftd_interfaces",
            "common_setup.swagger_configure_new_dhcp",
            "common_setup.swagger_configure_ospf",
            "common_setup.swagger_deploy",
        ],
    }

    while True:
        print(choices)
        sel = input("Select an option: ").strip().lower()
        if sel in ("q", "quit", "exit"):
            print("Bye!")
            return
        if sel not in mapping:
            print("Invalid choice. Try again.\n")
            continue

        run_uids(mapping[sel])

        again = input("\nRun another option? [Y/n]: ").strip().lower()
        if again in ("n", "no"):
            print("Bye!")
            return


if __name__ == "__main__":
    menu()

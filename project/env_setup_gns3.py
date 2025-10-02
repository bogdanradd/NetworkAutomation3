#!/usr/bin/env python3
"""
Create positioned nodes in a GNS3 project (gns3fy 1.0.0rc3).

- Uses Project.create_node(...) to create from existing templates
- Verifies/patches canvas coordinates via raw API if needed
"""

from typing import List, Tuple
from gns3fy import Server
from gns3fy.projects import Project

# === EDIT THESE ===
GNS3_URL   = "http://92.81.55.146:3080"
PROJECT_ID = "309a3014-2d94-41c8-b044-de716c3160a0"

# name, template, x, y
NODES: List[Tuple[str, str, int, int]] = [
    ("IOU-1",  "Cisco IOU L3 17.12.1",     -800, -400),
    ("IOSv-1", "Cisco IOSv 15.9(3)M6",        0, -400),
    ("CSR-1",  "Cisco CSR1000v 17.03.08a",  800, -400),
    ("FTD-1",  "Cisco FTDv 7.7.0 (89)",     -800,  200),
]

def ensure_project_open(proj: Project) -> None:
    proj.get()
    if proj.status != "opened":
        print(f"[i] Project status is '{proj.status}', opening…")
        proj.open()
        proj.get()

def template_exists(srv: Server, name: str) -> bool:
    srv.get_templates()
    return any(t.name == name for t in srv.templates or [])

def set_position_raw(srv: Server, proj_id: str, node_id: str, x: int, y: int) -> None:
    """
    Some emulators ignore x/y during creation.
    Use a minimal raw PUT to avoid rc3 serialization issues.
    """
    srv.connector.http_put(
        f"/v2/projects/{proj_id}/nodes/{node_id}",
        {"x": x, "y": y}
    )

def main() -> None:
    srv  = Server(GNS3_URL)
    proj = Project(project_id=PROJECT_ID, connector=srv)

    ensure_project_open(proj)

    # Pre-validate templates so we fail fast with a helpful message
    srv.get_templates()
    existing_templates = {t.name for t in (srv.templates or [])}
    missing = [tpl for _, tpl, _, _ in NODES if tpl not in existing_templates]
    if missing:
        print("[!] The following template names were not found on the GNS3 server:")
        for tpl in missing:
            print(f"    - {tpl}")
        print("    Tip: In GNS3 GUI, create/import these templates (same names), or adjust NODES[].")
        return

    for name, template, x, y in NODES:
        # If a node with this name already exists, skip create and just reposition
        existing = proj.search_node(name)
        if existing:
            node_id = existing.node_id
            print(f"[=] Node '{name}' already exists (id={node_id}). Repositioning to ({x},{y})…")
            try:
                set_position_raw(srv, proj.project_id, node_id, x, y)
                print(f"[✓] Repositioned '{name}' to ({x},{y}).")
            except Exception as e:
                print(f"[x] Failed to reposition '{name}': {e}")
            continue

        # Create the node at a desired position
        try:
            print(f"[*] Creating '{name}' from template '{template}' at ({x},{y})…")
            node = proj.create_node(name=name, template=template, x=x, y=y)
            node.get()  # refresh to see server’s stored coordinates
            node_id = node.node_id

            # If coords didn’t stick, patch them with a minimal PUT
            if node.x != x or node.y != y:
                print(f"[i] Adjusting position for '{name}' "
                      f"(server has ({node.x},{node.y}), want ({x},{y}))…")
                set_position_raw(srv, proj.project_id, node_id, x, y)

            print(f"[✓] Created '{name}' (id={node_id}) at ({x},{y}).")
        except Exception as e:
            print(f"[x] Failed to create '{name}': {e}")

    print("\nDone.")

if __name__ == "__main__":
    main()

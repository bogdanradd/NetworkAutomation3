from gns3fy import Gns3Connector, Project, Node


def main():
    server = Gns3Connector("http://92.81.55.146:3080")

    project = Project(project_id="309a3014-2d94-41c8-b044-de716c3160a0", connector=server)
    project.get()

    new_node = Node(
        project_id=project.project_id,
        connector=server,
        name="IOSv2",
        template="Cisco IOSv 15.9(3)M6",
        x=0,
        y=0
    )
    try:
        new_node.create()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()

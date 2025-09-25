import subprocess

with subprocess.Popen(['ansible-playbook', '-i', 'inv.ini', 'r1_add_static_route.yaml', '--ask-vault-pass'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    stdin=subprocess.PIPE,
    text=True,
                      ) as p:
    p.communicate(input='pynet3')
    return_code = p.wait()
    if return_code == 0:
        print("Successfully deployed ansible playbook")
    else:
        print("Failed to deploy ansible playbook")
    print(p.stdout)


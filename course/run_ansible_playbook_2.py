import ansible_runner

out = ansible_runner.run(
    private_data_dir='../project',
    playbook='r1_add_static_route.yaml',
    inventory='inv.ini',
    json_mode=True,
)
print(out)
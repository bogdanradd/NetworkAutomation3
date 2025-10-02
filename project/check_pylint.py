"""Module to check pylint grade"""
import subprocess
import sys

def run(label, target):
    """Method to run pylint check commands"""
    print(f"-- {label} --")
    subprocess.run([sys.executable, '-m', 'pylint', '--rcfile', 'pylintrc_main', target, '--exit-zero'], check=False)

run('project', '../project')
run('lib/connectors', '../lib/connectors')

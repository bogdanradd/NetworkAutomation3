import pylint
import sys
print(sys.path)

args = ['--rcfile=pylintrc_main' ,'try_attacks.py']
pylint.run_pylint(args)
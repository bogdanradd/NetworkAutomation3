import pylint
import sys
print(sys.path)

args = ['--rcfile=pylintrc_main' ,'menu_main_script.py']
pylint.run_pylint(args)
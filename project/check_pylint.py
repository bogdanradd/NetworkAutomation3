import pylint
import sys
print(sys.path)

args = ['--rcfile=pylintrc_main' ,'swagger_main_ex.py']
pylint.run_pylint(args)
import pylint
import sys
print(sys.path)

args = ['--rcfile=pylintrc_main' ,'../lib/connectors']
pylint.run_pylint(args)
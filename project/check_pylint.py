import pylint
# args = ['--rcfile=pylintrc_main' ,'../lib/connectors']
# pylint.run_pylint(args)
args = ['--rcfile=pylintrc_main' ,'../project']
pylint.run_pylint(args)
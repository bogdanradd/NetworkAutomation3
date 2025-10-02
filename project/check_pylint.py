import pylint
args = ['--rcfile=pylintrc_main' ,'../lib/connectors/swagger_conn.py']
pylint.run_pylint(args)
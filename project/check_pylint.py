"""Module to check pylint grade"""
import pylint

args = ['--rcfile=pylintrc_main', '../project']
pylint.run_pylint(args)

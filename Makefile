SHELL := /bin/bash

.PHONY: help prepare-dev test lint run

VENV_NAME?=venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

MODULE_NAME=tap_solarvista
MODULE_CMD=tap-solarvista

.DEFAULT: help
help:
	@echo "make prepare-dev"
	@echo "       prepare development environment, use only once"
	@echo "make clean"
	@echo "       clean the development environment, you'll need to 'make prepare-dev' again after this"
	@echo "make test"
	@echo "       build and test the module"
	@echo "make lint"
	@echo "       build and run pylint and mypy"
	@echo "make install"
	@echo "       install this module locally and use your ide with your local virtual environment instead of this makefile's venv"
	@echo "make run"
	@echo "       run the module"
	@echo "make doc"
	@echo "       build sphinx documentation"

prepare-dev:
	# sudo apt-get -y install python3.5 python3-pip python3-venv
	make venv

# Requirements are in setup.py, so whenever setup.py is changed, re-run installation of dependencies.
venv: $(VENV_NAME)/bin/activate
$(VENV_NAME)/bin/activate: setup.py
	test -d $(VENV_NAME) || python3 -m venv $(VENV_NAME)
	${PYTHON} -m pip install -U pip setuptools
	${PYTHON} -m pip install sphinx
	${PYTHON} -m pip install sphinx-rtd-theme
	${PYTHON} -m pip install -e .[test]
	${PYTHON} -m pip install -e .
	touch $(VENV_NAME)/bin/activate

test: venv
	${PYTHON} -m pytest -o junit_family=xunit2 --junitxml=./target/test_report.xml

lint: venv
	${PYTHON} -m pylint ${MODULE_NAME}

run: venv
	source $(VENV_NAME)/bin/activate && ${MODULE_CMD} --version

# install locally, not using venv
install:
	python -m pip install -e .[test]
	python -m pip install -e .

doc: venv
	$(VENV_ACTIVATE) && cd docs; make gen html

clean:
	rm -rf docs/build/
	rm -f .coverage
	rm -rf .eggs/
	rm -rf *.egg-info
	rm -rf venv/
	rm -rf build/
	rm -rf dist/
	rm -rf logs/
	rm -rf target/
	rm -rf .pytest_cache
	find . -type f -name '*.pyc' -delete
	find . -depth -type d -name '__pycache__' -delete

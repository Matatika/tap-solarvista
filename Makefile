.PHONY: help prepare-dev test lint run

VENV_NAME?=venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

MODULE_NAME=tap_solarvista

.DEFAULT: help
help:
	@echo "make prepare-dev"
	@echo "       prepare development environment, use only once"
	@echo "make test"
	@echo "       build and test the module"
	@echo "make lint"
	@echo "       build and run pylint and mypy"
	@echo "make run"
	@echo "       run the module"

prepare-dev:
	sudo apt-get -y install python3.5 python3-pip
	python3 -m pip install virtualenv
	make venv

# Requirements are in setup.py, so whenever setup.py is changed, re-run installation of dependencies.
venv: $(VENV_NAME)/bin/activate
$(VENV_NAME)/bin/activate: setup.py
	test -d $(VENV_NAME) || virtualenv -p python3 $(VENV_NAME)
	${PYTHON} -m pip install -U pip setuptools
	${PYTHON} -m pip install pytest
	${PYTHON} -m pip install pylint
	${PYTHON} -m pip install mypy
	${PYTHON} -m pip install -e .
	touch $(VENV_NAME)/bin/activate


test: venv
	${PYTHON} -m pytest -o junit_family=xunit2 --junitxml=./target/test_report.xml

lint: venv
	${PYTHON} -m pylint ${MODULE_NAME}
	${PYTHON} -m mypy ${MODULE_NAME}

run: venv
	${MODULE_NAME} --version

clean:
	rm -f .coverage
	rm -rf .eggs/
	rm -rf *.egg-info
	rm -rf venv/
	rm -rf build/
	rm -rf dist/
	rm -rf logs/
	rm -rf target/
	find . -type f -name '*.pyc' -delete
	find . -depth -type d -name '__pycache__' -delete




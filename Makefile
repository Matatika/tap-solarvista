.PHONY: install test

install:
	pip install wheel
	python setup.py bdist_wheel
	pip install -e .

test:
	pytest -o junit_family=xunit2 --junitxml=./target/test_report.xml

clean:
	rm -f .coverage
	rm -rf .eggs/
	rm -rf *.egg-info
	rm -rf build/
	rm -rf dist/
	rm -rf logs/
	rm -rf target/
	find . -type f -name '*.pyc' -delete
	find . -depth -type d -name '__pycache__' -delete

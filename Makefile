.PHONY: install test

install:
	pip install -e .

test:
	pytest --junitxml=./target/test_report.xml

clean:
	rm -f .coverage
	rm -rf .eggs/
	rm -rf build/
	rm -rf dist/
	rm -rf logs/
	rm -rf target/
	find . -type f -name '*.pyc' -delete
	find . -depth -type d -name '__pycache__' -delete
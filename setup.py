#!/usr/bin/env python
from setuptools import setup,find_packages

setup(
    name="tap_solarvista",
    version="0.1.0",
    description="Singer.io tap for extracting data",
    author="Matatika",
    url="https://matatika.com",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_solarvista"],
    install_requires=[
        "singer-python>=5.0.12",
        "requests",
    ],
    tests_require=[
        "unittest",
    ],
    entry_points="""
    [console_scripts]
    tap-solarvista=tap_solarvista:main
    """,
    packages = find_packages(),
    package_data = {
        "schemas": ["tap_solarvista/schemas/*.json"]
    },
    include_package_data=True,
)

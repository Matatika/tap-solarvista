#!/usr/bin/env python
from setuptools import setup

setup(
    name="tap-solarvista",
    version="0.1.0",
    description="Singer.io tap for extracting data",
    author="Stitch",
    url="http://singer.io",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_solarvista"],
    install_requires=[
        "singer-python>=5.0.12",
        "requests",
    ],
    entry_points="""
    [console_scripts]
    tap-solarvista=tap_solarvista:main
    """,
    packages=["tap_solarvista"],
    package_data = {
        "schemas": ["tap_solarvista/schemas/*.json"]
    },
    include_package_data=True,
)

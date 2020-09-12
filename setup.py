#!/usr/bin/env python
""" Set up the installation
"""

import os
from setuptools import setup

here = os.path.dirname(os.path.abspath(__file__))

long_description = open(os.path.join(here, "README.md")).read()

setup(
    name="s3-yum-repository",
    version="2.0.0",
    description="Use S3 buckets as yum repositories, authenticating, via named AWS cli profiles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Resisty/s3-yum-repository",
    author="Brian Auron",
    author_email="brianauron@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Packaging",
        "License :: Apache 2.0",
        "Programming Language :: Python :: 2.7",
    ],
    keywords=["s3", "yum", "repository"],
    python_requires=">=2.7,<3",
    install_requires=["boto3", "yum"],
    data_files=[
        ('/etc/yum.repos.d', ['s3.repo']),
        ('/etc/yum/pluginconf.d', ['s3.conf']),
        ('/usr/lib/yum-plugins', ['s3.py']),
    ]
)

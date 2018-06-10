
import setuptools
from distutils.core import setup
import sys
import time

install_requires = open("requirements.txt").readlines()
install_requires = [tmp.strip() for tmp in install_requires]

setup(
	# Application name:
	name="WebRequest",

	# Version number (initial):
	version="0.0.35",

	# Application author details:
	author="Connor Wolf",
	author_email="github@imaginaryindustries.com",

	# Packages
	packages=setuptools.find_packages(),
	package_dir = {'WebRequest': 'WebRequest'},


	# Details
	url="https://github.com/fake-name/WebRequest",

	#
	# license="LICENSE.txt",
	description="Like `requests`, but shittier.",

	long_description              = open("README.md").read(),
	long_description_content_type = "text/markdown",

	# Dependent packages (distributions)
	install_requires=install_requires,
)

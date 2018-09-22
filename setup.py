
import setuptools
import sys
import time

def req_file(filename):
	with open(filename) as f:
		content = f.readlines()
	# you may also want to remove whitespace characters like `\n` at the end of each line
	return [x.strip() for x in content]

setuptools.setup(
	# Application name:
	name="WebRequest",

	# Version number (initial):
	version="0.0.50",

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

	include_package_data=True,

	# Dependent packages (distributions)
	install_requires=req_file("requirements.txt"),
)


import setuptools
from distutils.core import setup
import sys
import time
setup(
	# Application name:
	name="WebRequest",

	# Version number (initial):
	version="0.0.26",

	# Application author details:
	author="Connor Wolf	",
	author_email="github@imaginaryindustries.com",

	# Packages
	packages=setuptools.find_packages(),
	package_dir = {'WebRequest': 'WebRequest'},


	# Details
	url="https://github.com/fake-name/WebRequest",

	#
	# license="LICENSE.txt",
	description="Like `requests`, but shittier.",

	long_description=open("README.md").read(),

	dependency_links=[
		'https://github.com/fake-name/ChromeController/tarball/master#egg=ChromeController-0.1.2',
	],

	# Dependent packages (distributions)
	install_requires=[
		'beautifulsoup4>=4.6.0',
		'selenium>=3.8.1',
		'PySocks>=1.6.8',
		'cchardet>=2.1.1',
		'lxml>=4.1.1',
		"ChromeController>=0.1.2",
	],
)

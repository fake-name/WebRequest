#!/bin/bash


# python3 -m unittest Tests.DbContentTests

# coverage run --source=./dbApi.py -m unittest Tests.DbApiTests

# Coverage doesn't work with cython files.
# Therefore, we don't run the BK Tree tests with it.
# python3 -m unittest Tests.BinaryConverterTests
# python3 -m unittest Tests.BKTreeTests
# python3 -m unittest Tests.Test_BKTree_Concurrency


# Test ALL THE THINGS

set -e

nosetests                      \
	--with-coverage            \
	--exe                      \
	--cover-package=WebRequest \
	tests
	# --stop                     \
	# tests.test_selenium
	# tests.test_simple

# nosetests                      \
# 	--with-coverage            \
# 	--exe                      \
# 	--cover-package=WebRequest \
# 	tests.testing_server

# nosetests                      \
# 	--with-coverage            \
# 	--exe                      \
# 	--cover-package=WebRequest \
# 	tests.test_selenium

# nosetests                      \
# 	--with-coverage            \
# 	--exe                      \
# 	--cover-package=WebRequest \
# 	tests.test_simple

# nosetests                      \
# 	--with-coverage            \
# 	--exe                      \
# 	--cover-package=WebRequest \
# 	--nocapture                \
# 	tests.test_waf_bullshit.TestWafPokeThrough

# nosetests                      \
# 	--with-coverage            \
# 	--exe                      \
# 	--cover-package=WebRequest \
# 	tests.test_chromium.TestChromiumPooled

	# --stop                     \

	# tests
	# --nocapture                \
	# tests.test_waf_bullshit.TestPreemptiveWrapper

	# tests.test_waf_bullshit
	# --with-cprofile \
	# tests.test_simple
	# tests.test_selenium

coverage report --show-missing
coverage erase







#!/usr/bin/python3

import time
import abc
import random
import socket
import urllib.parse
import http.cookiejar
import bs4
import selenium.webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities





class title_not_contains(object):
	""" An expectation for checking that the title *does not* contain a case-sensitive
	substring. title is the fragment of title expected
	returns True when the title matches, False otherwise
	"""
	def __init__(self, title):
		self.title = title


	def __call__(self, driver):
		return self.title not in driver.title

#pylint: disable-msg=E1101, C0325, R0201, W0702, W0703

def wait_for(condition_function):
	start_time = time.time()
	while time.time() < start_time + 3:
		if condition_function():
			return True
		else:
			time.sleep(0.1)
	raise Exception(
		'Timeout waiting for {}'.format(condition_function.__name__)
	)

class load_delay_context_manager(object):

	def __init__(self, browser):
		self.browser = browser

	def __enter__(self):
		self.old_page = self.browser.find_element_by_tag_name('html')

	def page_has_loaded(self):
		new_page = self.browser.find_element_by_tag_name('html')
		return new_page.id != self.old_page.id

	def __exit__(self, *_):
		wait_for(self.page_has_loaded)
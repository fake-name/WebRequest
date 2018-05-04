#!/usr/bin/python3

import time
import logging
import random
import traceback
import urllib.parse
import threading
import contextlib
import multiprocessing
import gc

import bs4

import ChromeController

@contextlib.contextmanager
def _cr_context(cls):
	with ChromeController.ChromeContext(cls._cr_binary) as cr:
		cls._syncIntoChromium(cr)
		yield cr
		cls._syncOutOfChromium(cr)


class WebGetCrMixin(object):
	# creds is a list of 3-tuples that gets inserted into the password manager.
	# it is structured [(top_level_url1, username1, password1), (top_level_url2, username2, password2)]
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cr_binary = "google-chrome"

		self.navigate_timeout_secs = 10
		self.wrapper_step_through_timeout = 20

	def _syncIntoChromium(self, cr):
		cr.clear_cookies()
		# Headers are a list of 2-tuples. We need a dict
		hdict = dict(self.browserHeaders)
		cr.update_headers(hdict)
		for cookie in self.cj:
			# Something, somewhere is setting cookies without a value,
			# and that confuses chromium a LOT. Anways, just don't forward
			# those particular cookies.
			if cookie and cookie.value:
				cr.set_cookie(cookie)

	def _syncOutOfChromium(self, cr):
		for cookie in cr.get_cookies():
			self.cj.set_cookie(cookie)

	def getItemChromium(self, itemUrl):
		self.log.info("Fetching page for URL: '%s' with Chromium" % itemUrl)

		with ChromeController.ChromeContext(binary=self._cr_binary) as cr:

			self._syncIntoChromium(cr)

			response = cr.blocking_navigate_and_get_source(itemUrl, timeout=self.navigate_timeout_secs)

			raw_url = cr.get_current_url()
			fileN = urllib.parse.unquote(urllib.parse.urlparse(raw_url)[2].split("/")[-1])
			fileN = bs4.UnicodeDammit(fileN).unicode_markup

			self._syncOutOfChromium(cr)

		# Probably a bad assumption
		if response['binary']:
			mType = "application/x-binary"
		else:
			mType = "text/html"

		# So, self._cr.page_source appears to be the *compressed* page source as-rendered. Because reasons.
		content = response['content']
		return content, fileN, mType

	def getHeadTitleChromium(self, url, referrer=None):
		self.log.info("Getting HEAD with Chromium")
		if not referrer:
			referrer = url

		with ChromeController.ChromeContext(self._cr_binary) as cr:
			self._syncIntoChromium(cr)

			cr.blocking_navigate(referrer)
			time.sleep(random.uniform(2, 6))
			cr.blocking_navigate(url)

			title, cur_url = cr.get_page_url_title()

			self._syncOutOfChromium(cr)

		self.log.info("Resolved URL for %s -> %s", url, cur_url)

		ret = {
			'url': cur_url,
			'title': title,
		}
		return ret

	def getHeadChromium(self, url, referrer=None):
		self.log.info("Getting HEAD with Chromium")
		if not referrer:
			referrer = url

		with ChromeController.ChromeContext(self._cr_binary) as cr:
			self._syncIntoChromium(cr)


			cr.blocking_navigate(referrer)
			time.sleep(random.uniform(2, 6))
			cr.blocking_navigate(url)

			dummy_title, cur_url = cr.get_page_url_title()

			self._syncOutOfChromium(cr)

		return cur_url


	def chromiumGetRenderedItem(self, url):

		with ChromeController.ChromeContext(self._cr_binary) as cr:
			self._syncIntoChromium(cr)

			# get_rendered_page_source
			cr.blocking_navigate(url)


			content = cr.get_rendered_page_source()
			mType = 'text/html'
			fileN = ''
			self._syncOutOfChromium(cr)


		return content, fileN, mType


	def __del__(self):
		# print("ChromiumMixin destructor")
		sup = super()
		if hasattr(sup, '__del__'):
			sup.__del__()

	def stepThroughJsWaf_bare_chromium(self, url, titleContains='', titleNotContains=''):
		'''
		Use Chromium to access a resource behind WAF protection.

		Params:
			``url`` - The URL to access that is protected by WAF
			``titleContains`` - A string that is in the title of the protected page, and NOT the
				WAF intermediate page. The presence of this string in the page title
				is used to determine whether the WAF protection has been successfully
				penetrated.
			``titleContains`` - A string that is in the title of the WAF intermediate page
				and NOT in the target page. The presence of this string in the page title
				is used to determine whether the WAF protection has been successfully
				penetrated.

		The current WebGetRobust headers are installed into the selenium browser, which
		is then used to access the protected resource.

		Once the protected page has properly loaded, the WAF access cookie is
		then extracted from the selenium browser, and installed back into the WebGetRobust
		instance, so it can continue to use the WAF auth in normal requests.

		'''

		if (not titleContains) and (not titleNotContains):
			raise ValueError("You must pass either a string the title should contain, or a string the title shouldn't contain!")

		if titleContains and titleNotContains:
			raise ValueError("You can only pass a single conditional statement!")

		self.log.info("Attempting to access page through WAF browser verification.")

		current_title = None

		with ChromeController.ChromeContext(self._cr_binary) as cr:
			self._syncIntoChromium(cr)
			cr.blocking_navigate(url)

			for _ in range(self.wrapper_step_through_timeout):
				time.sleep(1)
				current_title, _ = cr.get_page_url_title()
				if titleContains and titleContains in current_title:
					self._syncOutOfChromium(cr)
					return True
				if titleNotContains and current_title and titleNotContains not in current_title:
					self._syncOutOfChromium(cr)
					return True

			self._syncOutOfChromium(cr)

		self.log.error("Failed to step through. Current title: '%s'", current_title)

		return False


	def chromiumContext(self):
		'''
		Return a active chromium context, useable for manual operations directly against
		chromium.

		The WebRequest user agent and other context is synchronized into the chromium
		instance at startup, and changes are flushed back to the webrequest instance
		from chromium at completion.
		'''
		return _cr_context(self)

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
import contextlib

import bs4

import ChromeController

@contextlib.contextmanager
def _cr_context(cls):
	with ChromeController.ChromeContext(cls._cr_binary) as cr:
		cls._syncIntoChromium(cr)
		yield cr
		cls._syncOutOfChromium(cr)

# Share the same chrome instance across multiple threads
class ChromiumBorg(object):
	__shared_state = {}
	# init internal state variables here
	__initialized = False

	def _init_default_register(self, chrome_binary):
		# Current runners are configured to use 10 threads.
		self.__cr = ChromeController.TabPooledChromium(binary=chrome_binary, tab_pool_max_size=10)
		self.__initialized = True

	def __init__(self, chrome_binary):
		self.__dict__ = self.__shared_state
		if not self.__initialized:
			self._init_default_register(chrome_binary)

	def get(self):
		return self.__cr


class WebGetCrMixin(object):
	# creds is a list of 3-tuples that gets inserted into the password manager.
	# it is structured [(top_level_url1, username1, password1), (top_level_url2, username2, password2)]
	def __init__(self, use_global_tab_pool=True, *args, **kwargs):
		if "chromium-binary" in kwargs:
			self._cr_binary = kwargs.pop("chrome-binary")
		else:
			self._cr_binary = "google-chrome"

		super().__init__(*args, **kwargs)

		self.navigate_timeout_secs = 10
		self.wrapper_step_through_timeout = 20

		if use_global_tab_pool:
			self.borg_chrome_pool = True
		else:
			self.borg_chrome_pool = None


	def _chrome_context(self, itemUrl, extra_tid):
		if self.borg_chrome_pool and self.borg_chrome_pool is True:
			self.log.info("Initializing chromium pool on first use!")
			self.borg_chrome_pool = ChromiumBorg(chrome_binary=self._cr_binary)

		if self.borg_chrome_pool:
			assert itemUrl is not None, "You need to pass a URL to the contextmanager, so it can dispatch to the correct tab!"
			return self.borg_chrome_pool.get().tab(url=itemUrl, extra_id=extra_tid)
		else:
			return ChromeController.ChromeContext(binary=self._cr_binary)

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

	def getItemChromium(self, itemUrl, extra_tid=False):
		self.log.info("Fetching page for URL: '%s' with Chromium" % itemUrl)

		if extra_tid is True:
			extra_tid = threading.get_ident()

		with self._chrome_context(itemUrl, extra_tid=extra_tid) as cr:

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

		# Use the new interface that returns the actual type
		if 'mimetype' in response:
			mType = response['mimetype']

		# So, self._cr.page_source appears to be the *compressed* page source as-rendered. Because reasons.
		content = response['content']

		if isinstance(content, bytes):
			self._check_waf(content, itemUrl)
		elif isinstance(content, str):
			self._check_waf(content.encode("UTF-8"), itemUrl)
		else:
			self.log.error("Unknown type of content return: %s" % (type(content), ))

		return content, fileN, mType

	def getHeadTitleChromium(self, url, referrer=None, extra_tid=False):
		self.log.info("Getting HEAD with Chromium")
		if not referrer:
			referrer = url

		if extra_tid is True:
			extra_tid = threading.get_ident()

		with self._chrome_context(url, extra_tid=extra_tid) as cr:
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

	def getHeadChromium(self, url, referrer=None, extra_tid=None):
		self.log.info("Getting HEAD with Chromium")
		if not referrer:
			referrer = url

		if extra_tid is True:
			extra_tid = threading.get_ident()

		with self._chrome_context(url, extra_tid=extra_tid) as cr:
			self._syncIntoChromium(cr)

			cr.blocking_navigate(referrer)
			time.sleep(random.uniform(2, 6))
			cr.blocking_navigate(url)

			dummy_title, cur_url = cr.get_page_url_title()

			self._syncOutOfChromium(cr)

		return cur_url


	def chromiumGetRenderedItem(self, url, extra_tid=None):

		if extra_tid is True:
			extra_tid = threading.get_ident()

		with self._chrome_context(url, extra_tid=extra_tid) as cr:
			self._syncIntoChromium(cr)

			# get_rendered_page_source
			cr.blocking_navigate(url)

			content = cr.get_rendered_page_source()
			mType = 'text/html'
			fileN = ''
			self._syncOutOfChromium(cr)


		self._check_waf(content.encode("UTF-8"), url)

		return content, fileN, mType


	def __del__(self):
		# print("ChromiumMixin destructor")
		sup = super()
		if hasattr(sup, '__del__'):
			sup.__del__()

	def stepThroughJsWaf_bare_chromium(self, url, titleContains='', titleNotContains='', extra_tid=None):
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

		if extra_tid is True:
			extra_tid = threading.get_ident()

		with self._chrome_context(url, extra_tid=extra_tid) as cr:
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


	def chromiumContext(self, url, extra_tid=None):
		'''
		Return a active chromium context, useable for manual operations directly against
		chromium.

		The WebRequest user agent and other context is synchronized into the chromium
		instance at startup, and changes are flushed back to the webrequest instance
		from chromium at completion.
		'''
		assert url is not None, "You need to pass a URL to the contextmanager, so it can dispatch to the correct tab!"


		if extra_tid is True:
			extra_tid = threading.get_ident()

		return self._chrome_context(url, extra_tid=extra_tid)

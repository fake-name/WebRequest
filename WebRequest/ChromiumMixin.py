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

	def close(self):
		if self.__initialized:
			self.__cr.close()
			self.__initialized = False

class ChromiumSingle(object):
	def __init__(self, chrome_binary):
		self.__cr = ChromeController.TabPooledChromium(binary=chrome_binary, tab_pool_max_size=5)
		self.__initialized = True

	def get(self):
		return self.__cr

	def close(self):
		if self.__initialized:
			self.__cr.close()
			self.__initialized = False

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

		self.use_global_tab_pool = use_global_tab_pool

		if use_global_tab_pool:
			self.log.info("Using global chromium tab pool")

		self.chrome_pool = None

	def _chrome_context(self, itemUrl:str, extra_tid):
		if not self.chrome_pool:
			if self.use_global_tab_pool:
				self.log.info("Initializing chromium pool on first use!")
				self.chrome_pool = ChromiumBorg(chrome_binary=self._cr_binary)
			else:
				self.chrome_pool = ChromiumSingle(chrome_binary=self._cr_binary)



		assert itemUrl is not None, "You need to pass a URL to the contextmanager, so it can dispatch to the correct tab!"
		return self.chrome_pool.get().tab(url=itemUrl, extra_id=extra_tid)


	def _syncIntoChromium(self, cr):
		self.log.info("Syncing cookies into chromium")
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
		self.log.info("Syncing cookies out from chromium")
		for cookie in cr.get_cookies():
			self.cj.set_cookie(cookie)

	def comprehensiveGetItemChromium(self, url, referrer=None, extra_tid=False, title_timeout=None, need_rendered=False):

		if title_timeout is None:
			title_timeout = 1
		if extra_tid is True:
			extra_tid = threading.get_ident()

		ret = {}


		with self._chrome_context(url, extra_tid=extra_tid) as cr:
			# print("Starting nav (%s)" % need_rendered)
			self._syncIntoChromium(cr)

			################################################################################################
			# Get the raw content
			response = cr.blocking_navigate_and_get_source(url, timeout=self.navigate_timeout_secs)


			# Probably a bad assumption
			if response['binary']:
				ret['raw_mimetype'] = "application/x-binary"
			else:
				ret['raw_mimetype'] = "text/html"

			# Use the new interface that returns the actual type
			if 'mimetype' in response:
				ret['raw_mimetype'] = response['mimetype']

			# So, self._cr.page_source appears to be the *compressed* page source as-rendered. Because reasons.
			ret['raw_content'] = response['content']

			# Check for a waf before we bother with more stuff.
			if ret['raw_mimetype'] == 'text/html':
				raw_content = ret['raw_content']
				if isinstance(raw_content, str):
					raw_content = raw_content.encode("UTF-8")
				self._check_waf(raw_content, url)

			raw_url = cr.get_current_url()
			fileN = urllib.parse.unquote(urllib.parse.urlparse(raw_url)[2].split("/")[-1])
			fileN = bs4.UnicodeDammit(fileN).unicode_markup
			ret['raw_filename'] = fileN


			################################################################################################
			# Now we wait for the page to render (if the content type appears to be html)
			title, cur_url = cr.get_page_url_title()
			if title_timeout and ret['raw_mimetype'] == 'text/html':
				for _ in range(title_timeout * 20):
					# Wait until the page sets a title. This generally indicates that
					# the page is fully rendered, which for some reason seems to not
					# always be true after blocking_navigate, despite the fact that
					# that call shouldn't return until DOMContentLoaded has fired
					if cur_url not in title:
						break

					time.sleep(1.0 / 20.0)
					title, cur_url = cr.get_page_url_title()

			ret['resolved_title']   = title
			ret['resolved_url']     = cur_url
			if need_rendered:
				ret['resolved_content'] = cr.get_rendered_page_source()

			self._syncOutOfChromium(cr)
			# print("Done")

		self.log.info("Chromium fetch complete.")

		return ret


	def getItemChromium(self, itemUrl:str, referrer:str=None, extra_tid=False, title_timeout:int=None):
		'''

		'''
		self.log.info("Fetching page for URL: '%s' with Chromium", itemUrl)
		ret = self._unwaf_func("comprehensiveGetItemChromium", itemUrl, referrer=referrer, extra_tid=extra_tid, title_timeout=title_timeout)
		return ret['raw_content'], ret['raw_filename'], ret['raw_mimetype']

	def getHeadTitleChromium(self, url:str, referrer:str=None, extra_tid=False, title_timeout:int=None):
		'''

		'''
		self.log.info("Getting HEAD with Chromium")

		ret = self._unwaf_func("comprehensiveGetItemChromium", url, referrer=referrer, extra_tid=extra_tid, title_timeout=title_timeout)

		self.log.info("Resolved URL for %s -> %s (%s)", url, ret['resolved_url'], ret['resolved_title'])

		ret = {
			'url': ret['resolved_url'],
			'title': ret['resolved_title'],
		}
		return ret

	def getHeadChromium(self, url:str, referrer:str=None, extra_tid=None):
		'''

		'''
		self.log.info("Getting HEAD with Chromium")
		ret = self._unwaf_func("comprehensiveGetItemChromium", url, referrer=referrer, extra_tid=extra_tid)
		self.log.info("Resolved URL for %s -> %s", url, ret['resolved_url'])

		return ret['resolved_url']


	def chromiumGetRenderedItem(self, url:str, referrer:str=None, extra_tid=None, title_timeout:int=None):
		'''

		'''
		self.log.info("Getting rendered content with Chromium")

		ret = self._unwaf_func("comprehensiveGetItemChromium", url,
				referrer      = referrer,
				extra_tid     = extra_tid,
				title_timeout = title_timeout,
				need_rendered = True
			)

		return ret['resolved_content'], ret['raw_filename'], ret['raw_mimetype']


	def __del__(self):
		# print("ChromiumMixin destructor")
		sup = super()
		if hasattr(sup, '__del__'):
			sup.__del__()

	def stepThroughJsWaf_bare_chromium(self, url:str, titleContains:str='', titleNotContains:str='', extra_tid=None):
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


	def chromiumContext(self, url:str, extra_tid=None):
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

	def close_chromium(self):
		'''
		If a chromium tab pool is open, close it.
		Note that if you're using a shared tab pool, this will cause accesses to
		other shared instances of the tab pool to potentially fail with exceptions..
		'''
		if self.chrome_pool:
			self.chrome_pool.close()
			self.chrome_pool = None

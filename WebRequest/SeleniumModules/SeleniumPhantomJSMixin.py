#!/usr/bin/python3

import time
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

from . import SeleniumCommon

class WebGetSeleniumPjsMixin(object):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.selenium_pjs_driver = None

	def _initPjsWebDriver(self):
		if self.selenium_pjs_driver:
			self.selenium_pjs_driver.quit()
		dcap = dict(DesiredCapabilities.PHANTOMJS)
		wgSettings = dict(self.browserHeaders)
		# Install the headers from the WebGet class into phantomjs
		dcap["phantomjs.page.settings.userAgent"] = wgSettings.pop('User-Agent')
		for headerName in wgSettings:
			if headerName != 'Accept-Encoding':
				dcap['phantomjs.page.customHeaders.{header}'.format(header=headerName)] = wgSettings[headerName]

		self.selenium_pjs_driver = selenium.webdriver.PhantomJS(desired_capabilities=dcap)
		self.selenium_pjs_driver.set_window_size(1280, 1024)


	def _syncIntoSeleniumPjsWebDriver(self):
		'''
		So selenium is completely retarded, and you can't just set cookes, you have to
		be navigated to the domain for which you want to set cookies.
		This is extra double-plus idiotic, as it means you can't set cookies up
		before navigating.
		Sigh.
		'''
		pass
		# for cookie in self.getCookies():
		# 	print("Cookie: ", cookie)

		# 	cookurl = [
		# 			"http" if cookieDict['httponly'] else "https",   # scheme   0	URL scheme specifier
		# 			cookie.domain,                                   # netloc   1	Network location part
		# 			"/",                                             # path     2	Hierarchical path
		# 			"",                                              # params   3	Parameters for last path element
		# 			"",                                              # query    4	Query component
		# 			"",                                              # fragment 5	Fragment identifier
		# 		]

		# 	cdat = {
		# 				'name'   : cookie.name,
		# 				'value'  : cookie.value,
		# 				'domain' : cookie.domain,
		# 				'path'   :
		# 				'expiry' :
		# 			}
		# 	print("CDat: ", cdat)

		# 	self.selenium_pjs_driver.add_cookie(cdat)


	def _syncOutOfPjsWebDriver(self):
		for cookie in self.selenium_pjs_driver.get_cookies():
			self.addSeleniumCookie(cookie)


	def getItemPhantomJS(self, itemUrl):
		self.log.info("Fetching page for URL: '%s' with PhantomJS" % itemUrl)

		if not self.selenium_pjs_driver:
			self._initPjsWebDriver()
		self._syncIntoSeleniumPjsWebDriver()

		with SeleniumCommon.load_delay_context_manager(self.selenium_pjs_driver):
			self.selenium_pjs_driver.get(itemUrl)
		time.sleep(3)

		fileN = urllib.parse.unquote(urllib.parse.urlparse(self.selenium_pjs_driver.current_url)[2].split("/")[-1])
		fileN = bs4.UnicodeDammit(fileN).unicode_markup

		self._syncOutOfPjsWebDriver()

		# Probably a bad assumption
		mType = "text/html"

		# So, self.selenium_pjs_driver.page_source appears to be the *compressed* page source as-rendered. Because reasons.
		source = self.selenium_pjs_driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")

		assert source != '<head></head><body></body>'

		source = "<html>"+source+"</html>"
		return source, fileN, mType



	def getHeadTitlePhantomJS(self, url, referrer=None):
		self.getHeadPhantomJS(url, referrer)
		ret = {
			'url'   : self.selenium_pjs_driver.current_url,
			'title' : self.selenium_pjs_driver.title,
		}
		return ret

	def getHeadPhantomJS(self, url, referrer=None):
		self.log.info("Getting HEAD with PhantomJS")

		if not self.selenium_pjs_driver:
			self._initPjsWebDriver()
		self._syncIntoSeleniumPjsWebDriver()

		def try_get(loc_url):
			tries = 3
			for x in range(9999):
				try:
					self.selenium_pjs_driver.get(loc_url)
					time.sleep(random.uniform(2, 6))
					return
				except socket.timeout as e:
					if x > tries:
						raise e
		if referrer:
			try_get(referrer)
		try_get(url)

		self._syncOutOfPjsWebDriver()

		return self.selenium_pjs_driver.current_url


	def __del__(self):
		# print("PhantomJS __del__")
		if self.selenium_pjs_driver != None:
			self.selenium_pjs_driver.quit()

		sup = super()
		if hasattr(sup, '__del__'):
			sup.__del__()


	def stepThroughJsWaf_selenium_pjs(self, url, titleContains='', titleNotContains=''):
		'''
		Use Selenium+PhantomJS to access a resource behind cloudflare protection.

		Params:
			``url`` - The URL to access that is protected by cloudflare
			``titleContains`` - A string that is in the title of the protected page, and NOT the
				cloudflare intermediate page. The presence of this string in the page title
				is used to determine whether the cloudflare protection has been successfully
				penetrated.

		The current WebGetRobust headers are installed into the selenium browser, which
		is then used to access the protected resource.

		Once the protected page has properly loaded, the cloudflare access cookie is
		then extracted from the selenium browser, and installed back into the WebGetRobust
		instance, so it can continue to use the cloudflare auth in normal requests.

		'''

		if (not titleContains) and (not titleNotContains):
			raise ValueError("You must pass either a string the title should contain, or a string the title shouldn't contain!")

		if titleContains and titleNotContains:
			raise ValueError("You can only pass a single conditional statement!")

		self.log.info("Attempting to access page through cloudflare browser verification.")

		if not self.selenium_pjs_driver:
			self._initPjsWebDriver()
		self._syncIntoSeleniumPjsWebDriver()


		self.selenium_pjs_driver.get(url)

		if titleContains:
			condition = EC.title_contains(titleContains)
		elif titleNotContains:
			condition = SeleniumCommon.title_not_contains(titleNotContains)
		else:
			raise ValueError("Wat?")


		try:
			WebDriverWait(self.selenium_pjs_driver, 45).until(condition)
			success = True
			self.log.info("Successfully accessed main page!")
		except TimeoutException:
			self.log.error("Could not pass through cloudflare blocking!")
			success = False
		# Add cookies to cookiejar

		self._syncOutOfPjsWebDriver()

		self._syncCookiesFromFile()

		return success



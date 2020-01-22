#!/usr/bin/python3

import time
import traceback
import collections
import sys
import cloudscraper

from .Captcha import SocksProxy
from .Captcha import AntiCaptchaSolver
from .Captcha import TwoCaptchaSolver

from python_anticaptcha import AnticaptchaClient, NoCaptchaTask
from cloudscraper.reCaptcha import reCaptcha



class proxyCaptchaSolver(reCaptcha):

	def __init__(self):
		super(proxyCaptchaSolver, self).__init__('proxyanticaptcha')

	def getCaptchaAnswer(self, site_url, site_key, reCaptchaParams):
		if not reCaptchaParams.get('api_key'):
			raise ValueError("reCaptcha provider 'anticaptcha' was not provided an 'api_key' parameter.")

		client = AnticaptchaClient(reCaptchaParams.get('api_key'))

		task = NoCaptchaTask(
					website_url    = site_url,
					website_key    = site_key,
					user_agent     = reCaptchaParams['user_agent'],

					proxy_type     = "socks5",
					proxy_address  = reCaptchaParams['proxy_address'],
					proxy_port     = reCaptchaParams['proxy_port'],
					proxy_login    = None,
					proxy_password = None,
			)

		if not hasattr(client, 'createTaskSmee'):
			sys.tracebacklimit = 0
			raise RuntimeError("Please upgrade 'python_anticaptcha' via pip or download it from https://github.com/ad-m/python-anticaptcha")

		job = client.createTaskSmee(task)
		return job.get_solution_response()


proxyCaptchaSolver()

class WebGetCloudscraperMixin(object):

	def __init__(self,
			twocaptcha_api_key          : str             = None,
			anticaptcha_api_key         : str             = None,
			*args,
			**kwargs
			):

		super().__init__(*args, **kwargs)

		if twocaptcha_api_key:
			self.log.info("Have API key for 2Captcha.com: %s", twocaptcha_api_key)

		if anticaptcha_api_key:
			self.log.info("Have API key for Anti-Captcha.com: %s", anticaptcha_api_key)



		self.twocaptcha_api_key  = twocaptcha_api_key
		self.anticaptcha_api_key = anticaptcha_api_key

	def set_twocaptcha_api_key(self, api_key):
		self.log.info("Setting API key for 2Captcha.com: %s", api_key)
		self.twocaptcha_api_key  = api_key

	def set_anticaptcha_api_key(self, api_key):
		self.log.info("Setting API key for Anti-Captcha.com: %s", api_key)
		self.anticaptcha_api_key  = api_key


	def extract_cloudscrape_resp_cookies(self, scraper, resp):
		for cookie in scraper.cookies:
			self.addCookie(cookie)

	def _no_recaptcha_fetch(self, url):
		normal_scraper = cloudscraper.create_scraper()

		# Sync our headers.
		normal_scraper.headers = collections.OrderedDict(self.browserHeaders)

		try:
			resp = normal_scraper.get(url)
			self.extract_cloudscrape_resp_cookies(normal_scraper, resp)
			resp.raise_for_status()
			return True

		except Exception as e:
			if 'Cloudflare reCaptcha detected' in str(e):
				return "Cloudflare reCaptcha detected"

			self.log.error('"{}" returned an error. Could not collect tokens.'.format(url))
			self.log.error('Returned exception: {}.'.format(str(e)))
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			return False

		return False


	def handle_cloudflare_cloudscraper(self, url):
		self.log.info("Using cloudscraper to attempt to circumvent cloudflare.")

		ret = self._no_recaptcha_fetch(url)

		if ret != "Cloudflare reCaptcha detected":
			self.log.info("Cloudflare dealt with.")
			return ret


		if self.twocaptcha_api_key:
			self.log.info("handle_cloudflare_cloudscraper() -> Have API key for 2Captcha.com")
		if self.anticaptcha_api_key:
			self.log.info("handle_cloudflare_cloudscraper() -> Have API key for Anti-Captcha.com")


		recaptcha_params = {}
		if self.anticaptcha_api_key:
			proxy = SocksProxy.ProxyLauncher(AntiCaptchaSolver.ANTICAPTCHA_IPS)
			recaptcha_params = {
					'provider': 'proxyanticaptcha',
					'api_key': self.anticaptcha_api_key,

					"user_agent"     : dict(self.browserHeaders).get('User-Agent'),
					"proxy_type"     : "socks5",
					"proxy_address"  : proxy.get_wan_ip(),
					"proxy_port"     : proxy.get_wan_port(),
				}
		elif self.twocaptcha_api_key:
			proxy = SocksProxy.ProxyLauncher([TwoCaptchaSolver.TWOCAPTCHA_IP])
			recaptcha_params = {
					'provider': 'anticaptcha',
					'api_key': self.twocaptcha_api_key,

					'proxy'       : proxy.get_wan_address(),
					'proxytype'   : "SOCKS5",
				}
		else:
			self.log.error("Cloudflare captcha and no captcha handlers!")
			self.log.error("twocaptcha_api_key value: %s", self.twocaptcha_api_key)
			self.log.error("anticaptcha_api_key value: %s", self.anticaptcha_api_key)
			return None


		try:
			self.log.info("Connection params: %s:%s", proxy.get_wan_ip(), proxy.get_wan_port())

			if proxy.is_forwarded():
				# Wait for the port to be open and stuff. No idea why this seemed to be needed
				self.log.info("Letting port forward stabilize.")
				time.sleep(5)

			self.log.info("Attempting to access site using CloudScraper with Captcha Handling.")
			normal_scraper = cloudscraper.create_scraper(recaptcha=recaptcha_params)

			# Sync our headers.
			normal_scraper.headers = collections.OrderedDict(self.browserHeaders)
			resp = normal_scraper.get(url)
			self.extract_cloudscrape_resp_cookies(normal_scraper, resp)
			resp.raise_for_status()
			return True

		except Exception as e:

			self.log.error('"{}" returned an error. Could not collect tokens.'.format(url))
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			return False



		finally:
			proxy.stop()

		return False
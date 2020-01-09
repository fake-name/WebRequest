#!/usr/bin/python3

import time
import traceback
import collections
import cloudscraper

from .Captcha import SocksProxy
from .Captcha import AntiCaptchaSolver
from .Captcha import TwoCaptchaSolver

class WebGetCloudscraperMixin(object):

	def __init__(self,
			twocaptcha_api_key          : str             = None,
			anticaptcha_api_key         : str             = None,
			*args,
			**kwargs
			):

		super().__init__(*args, **kwargs)

		self.twocaptcha_api_key  = twocaptcha_api_key
		self.anticaptcha_api_key = anticaptcha_api_key


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

		recaptcha_params = {}
		if self.anticaptcha_api_key:
			proxy = SocksProxy.ProxyLauncher(AntiCaptchaSolver.ANTICAPTCHA_IPS)
			recaptcha_params = {
					'provider': 'anticaptcha',
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
			return None

		try:
			self.log.info("Connection params: %s:%s", proxy.get_wan_ip(), proxy.get_wan_port())

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
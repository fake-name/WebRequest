#!/usr/bin/python3

import traceback
import collections
import cloudscraper


class WebGetCloudscraperMixin(object):

	def extract_cloudscrape_resp_cookies(self, scraper, resp):
		for cookie in scraper.cookies:
			self.addCookie(cookie)

	def handle_cloudflare_cloudscraper(self, url):
		self.log.info("Using cloudscraper to attempt to circumvent cloudflare.")
		scraper = cloudscraper.create_scraper()

		# Sync our headers.
		scraper.headers = collections.OrderedDict(self.browserHeaders)

		try:
			resp = scraper.get(url)
			self.extract_cloudscrape_resp_cookies(scraper, resp)
			resp.raise_for_status()
			return True

		except Exception:
			self.log.error('"{}" returned an error. Could not collect tokens.'.format(url))
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			return False


		return False


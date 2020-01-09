



import logging
import json
import urllib.parse
import os.path
import io
import time

import requests
import python_anticaptcha

from .. import Exceptions as exc
from . import SocksProxy
from . import CaptchaSolverBase

# This is hardcoded. Huh.
# So UPnP /supports/ remote address filtering, despite most of the documentation
# I've found saying it does not. Arrrgh.
ANTICAPTCHA_IPS = [
		"*",
		"69.65.41.21",
		"78.46.86.231",
		"209.212.146.168",
	]
# Maybe use http://api.anti-captcha.com/getProxygateAddress for deriving these addresses in the future?


class AntiCaptchaSolver(CaptchaSolverBase.CaptchaSolverBase):

	captcha_service_name = "AntiCaptcha"


	def getbalance(self):
		"""
		Get you account balance.

		Returns value: balance (float), or raises an exception.
		"""

		return float(self.client.getBalance())


	def solve_simple_captcha(self, pathfile=None, filedata=None, filename=None):
		"""
		Upload a image (from disk or a bytearray), and then
		block until the captcha has been solved.
		Return value is the captcha result.

		either pathfile OR filedata should be specified. Filename is ignored (and is
		only kept for compatibility with the 2captcha solver interface)

		Failure will result in a subclass of WebRequest.CaptchaSolverFailure being
		thrown.
		"""

		if pathfile and os.path.exists(pathfile):
			fp = open(pathfile, 'rb')
		elif filedata:
			fp = io.BytesIO(filedata)
		else:
			raise ValueError("You must pass either a valid file path, or a bytes array containing the captcha image!")

		try:
			task = python_anticaptcha.ImageToTextTask(fp)
			job = self.client.createTask(task)

			job.join(maximum_time = self.waittime)

			return job.get_captcha_text()

		except python_anticaptcha.AnticaptchaException as e:
			raise exc.CaptchaSolverFailure("Failure solving captcha: %s, %s, %s" % (
					e.error_id,
					e.error_code,
					e.error_description,
				))


	def solve_recaptcha(self, google_key, page_url, timeout = 15 * 60):
		'''
		Solve a recaptcha on page `page_url` with the input value `google_key`.
		Timeout is `timeout` seconds, defaulting to 60 seconds.

		Return value is either the `g-recaptcha-response` value, or an exceptionj is raised
		(generally `CaptchaSolverFailure`)
		'''

		proxy = SocksProxy.ProxyLauncher(ANTICAPTCHA_IPS)
		self.log.info("Connection params: %s:%s", proxy.get_wan_ip(), proxy.get_wan_port())

		# Wait for the port to be open and stuff. No idea why this seemed to be needed
		self.log.info("Letting port forward stabilize.")
		time.sleep(5)

		try:
			task = python_anticaptcha.NoCaptchaTask(
					website_url    = page_url,
					website_key    = google_key,
					user_agent     = dict(self.wg.browserHeaders).get('User-Agent'),

					proxy_type     = "socks5",
					proxy_address  = proxy.get_wan_ip(),
					proxy_port     = proxy.get_wan_port(),
					proxy_login    = None,
					proxy_password = None,

				)

			job = self.client.createTask(task)
			job.join(maximum_time = timeout)

			return job.get_solution_response()
		except python_anticaptcha.AnticaptchaException as e:
			raise exc.CaptchaSolverFailure("Failure solving captcha: %s, %s, %s" % (
					e.error_id,
					e.error_code,
					e.error_description,
				))

		finally:
			proxy.stop()


def recaptcha_test():
	import test_settings
	logging.basicConfig(level=logging.DEBUG)

	import WebRequest

	wg = WebRequest.WebGetRobust()

	test_url = "https://patrickhlauke.github.io/recaptcha/"

	soup = wg.getSoup(test_url)

	recaptcha_div = soup.find("div", class_='g-recaptcha')

	print(recaptcha_div)
	print(recaptcha_div['data-sitekey'])

	solver = AntiCaptchaSolver(api_key=test_settings.ANTICAPTCHA_API_KEY, wg=wg)

	result = solver.solve_recaptcha(recaptcha_div['data-sitekey'], test_url)

	print("Solve result: ", result)


def test():
	import test_settings
	logging.basicConfig(level=logging.DEBUG)

	import WebRequest

	wg = WebRequest.WebGetRobust()

	solver = AntiCaptchaSolver(api_key=test_settings.ANTICAPTCHA_API_KEY, wg=wg)

	print(solver)

	# print("Credits: ", solver.getbalance())

	# res = solver.solve_simple_captcha(pathfile='/media/Storage/Scripts/xaDownloader/img.jpg')

	# print(res)




if __name__ == '__main__':
	recaptcha_test()
	# test()



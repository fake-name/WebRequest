



import logging
import json
import urllib.parse
import os.path
import io
import time

import requests

from .. import Exceptions as exc

from . import SocksProxy

# This is hardcoded. Huh.
TWOCAPTCHA_IP = '138.201.188.166'

class TwoCaptchaSolver(object):
	def __init__(self, api_key, wg):
		self.log      = logging.getLogger("Main.WebRequest.Captcha.2Captcha")

		self.api_key  = api_key
		self.wg       = wg

		# Default timeout is 5 minutes.
		self.waittime = 60 * 5

	def getUrlFor(self, mode, query_dict):

		# query params for input mode
		# Normal captcha solving
		#     key         String               Yes your API key
		#     language    Integer Default: 0   No  0 - not specified 1 - Cyrillic (Russian) captcha 2 - Latin captcha
		#     lang        String               No  Language code. See the list of supported languages.
		#     textcaptcha String
		#                   Max 140 characters
		#                   Endcoding: UTF-8   No  Text will be shown to worker to help him to solve the captcha correctly.
		#                                             For example: type red symbols only.
		#     header_acao Integer Default: 0   No  0 - disabled 1 - enabled. If enabled in.php will include Access-Control-Allow-Origin:* header in the response.
		#                                             Used for cross-domain AJAX requests in web applications.
		#     pingback    String               No  URL for pingback (callback) response that will be sent when captcha is solved.
		#                                             URL should be registered on the server. More info here.
		#     json        Integer Default: 0   No  0 - server will send the response as plain text 1 - tells the server to send the response as JSON
		#     soft_id     Integer              No  ID of software developer. Developers who integrated their software with 2captcha get reward: 10% of spendings of their software users.
		#
		# For solving recaptcha
		#     key           String              Yes  your API key
		#     method        String              Yes  userrecaptcha - defines that you're sending a ReCaptcha V2 with new method
		#     googlekey     String              Yes  Value of k or data-sitekey parameter you found on page
		#     pageurl       String              Yes  Full URL of the page where you see the ReCaptcha
		#     invisible     Integer Default: 0  No   1 - means that ReCaptcha is invisible. 0 - normal ReCaptcha.
		#     header_acao   Integer Default: 0  No   0 - disabled 1 - enabled.
		#                                               If enabled in.php will include Access-Control-Allow-Origin:* header in the response.
		#                                               Used for cross-domain AJAX requests in web applications. Also supported by res.php.
		#     pingback      String              No   URL for pingback (callback) response that will be sent when captcha is solved.
		#                                               URL should be registered on the server. More info here.
		#     json          Integer Default: 0  No   0 - server will send the response as plain text 1 - tells the server to send the response as JSON
		#     soft_id       Integer             No   ID of software developer. Developers who integrated their software with 2captcha get reward: 10% of spendings of their software users.
		#     proxy         String              No   Format: login:password@123.123.123.123:3128
		#                                            You can find more info about proxies here.
		#     proxytype     String              No   Type of your proxy: HTTP, HTTPS, SOCKS4, SOCKS5.
		#
		# Query params for result mode
		# Normal captcha results
		#     key         String              Yes your API key
		#     action      String              Yes get - get the asnwer for your captcha
		#     id          Integer             Yes ID of captcha returned by in.php.
		#     json        Integer Default: 0  No  0 - server will send the response as plain text 1 - tells the server to send the response as JSON
		#     header_acao Integer Default: 0  No  0 - disabled 1 - enabled. If enabled res.php will include Access-Control-Allow-Origin:* header
		#                                             in the response. Used for cross-domain AJAX requests in web applications.
		# Recaptcha results
		#     key         String              Yes your API key
		#     action      String              Yes get - get the asnwer for your captcha
		#     id          Integer             Yes ID of captcha returned by in.php.
		#     json        Integer Default: 0  No  0 - server will send the response as plain text 1 - tells the server to send the response as JSON

		if mode == 'input':
			path = '/in.php'
		elif mode == 'result':
			path = '/res.php'
		else:
			raise RuntimeError("Unknown mode (%s). Valid modes are 'input' and 'result'." % mode)

		query = urllib.parse.urlencode(query_dict)
		new_url = urllib.parse.urlunsplit(
				(
					'https',          # scheme
					'2captcha.com',   # netloc
					path,             # path
					query,           # query
					''                # fragment
				)
			)

		return new_url

	def _process_response(self, resp_json):

		if 'status' and 'request' in resp_json:
			if resp_json['status'] == 1:
				return resp_json['request']
			elif resp_json['request'] == 'CAPCHA_NOT_READY':
				raise exc.CaptchaNotReady("Captcha not ready yet.")
			else:
				self.log.error("[TwoCaptchaSolver] Error response: %s", resp_json['request'])
				raise exc.CaptchaSolverFailure("API call returned failure response: %s" % resp_json['request'])


		raise exc.CaptchaSolverFailure("Failure doing get request")


	def doGet(self, mode, query_dict):
		query_dict['json'] = True

		url = self.getUrlFor(mode, query_dict)

		res = self.wg.getJson(url)

		return self._process_response(res)

	def getbalance(self):
		"""
		Get you account balance.

		Returns value: balance (float), or raises an exception.
		"""

		balance = self.doGet('result', {
				'action' : 'getbalance',
				'key'    : self.api_key,
				'json'   : True,
			})

		return balance


	def _getresult(self, captcha_id, timeout=None):
		"""
		Poll until a captcha `captcha_id` has been solved, or
		the poll times out. The timeout is the default 60 seconds,
		unless overridden by `timeout` (which is in seconds).

		Polling is done every 8 seconds.
		"""
		timeout = timeout

		if not timeout:
			timeout = self.waittime

		poll_interval = 8

		start = time.time()

		for x in range(int(timeout / poll_interval)+1):
			self.log.info("Sleeping %s seconds (poll %s of %s, elapsed %0.2fs of %0.2f).",
					poll_interval,
					x,
					int(timeout / poll_interval)+1,
					(time.time() - start),
					timeout,
				)
			time.sleep(poll_interval)

			try:
				resp = self.doGet('result', {
						'action' : 'get',
						'key'    : self.api_key,
						'json'   : True,
						'id'     : captcha_id,
					}
				)

				self.log.info("Call returned success!")
				return resp

			except exc.CaptchaNotReady:
				self.log.info("Captcha not ready. Waiting longer.")

		raise exc.CaptchaSolverFailure("Solving captcha timed out after %s seconds!" % (time.time() - start, ))

	def _submit(self, pathfile, filedata, filename):
		'''
		Submit either a file from disk, or a in-memory file to the solver service, and
		return the request ID associated with the new captcha task.
		'''
		if pathfile and os.path.exists(pathfile):
			files = {'file': open(pathfile, 'rb')}
		elif filedata:
			assert filename
			files = {'file' : (filename, io.BytesIO(filedata))}
		else:
			raise ValueError("You must pass either a valid file path, or a bytes array containing the captcha image!")

		payload = {
			'key'    : self.api_key,
			'method' : 'post',
			'json'   : True,
			}

		self.log.info("Uploading to 2Captcha.com.")

		url = self.getUrlFor('input', {})

		request = requests.post(url, files=files, data=payload)

		if not request.ok:
			raise exc.CaptchaSolverFailure("Posting captcha to solve failed!")

		resp_json = json.loads(request.text)
		return self._process_response(resp_json)


	def solve_simple_captcha(self, pathfile=None, filedata=None, filename=None):
		"""
		Upload a image (from disk or a bytearray), and then
		block until the captcha has been solved.
		Return value is the captcha result.

		either pathfile OR filedata AND filename should be specified.

		Failure will result in a subclass of WebRequest.CaptchaSolverFailure being
		thrown.
		"""

		captcha_id = self._submit(pathfile, filedata, filename)
		return self._getresult(captcha_id=captcha_id)

	def solve_recaptcha(self, google_key, page_url, timeout = 15 * 60):
		'''
		Solve a recaptcha on page `page_url` with the input value `google_key`.
		Timeout is `timeout` seconds, defaulting to 60 seconds.

		Return value is either the `g-recaptcha-response` value, or an exceptionj is raised
		(generally `CaptchaSolverFailure`)
		'''

		proxy = SocksProxy.ProxyLauncher(TWOCAPTCHA_IP)

		try:
			captcha_id = self.doGet('input', {
						'key'         : self.api_key,
						'method'      : "userrecaptcha",
						'googlekey'   : google_key,
						'pageurl'     : page_url,

						'proxy'       : proxy.get_wan_address(),
						'proxytype'   : "SOCKS5",

						'json'        : True,
					}
				)

			# Allow 15 minutes for the solution
			# I've been seeing times up to 160+ seconds in testing.
			return self._getresult(captcha_id=captcha_id, timeout=timeout)
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

	solver = TwoCaptchaSolver(api_key=test_settings.TWOCAPTCHA_API_KEY, wg=wg)

	result = solver.solve_recaptcha(recaptcha_div['data-sitekey'], test_url)

	print("Solve result: ", result)


def test():
	import test_settings
	logging.basicConfig(level=logging.DEBUG)

	import WebRequest

	wg = WebRequest.WebGetRobust()

	solver = TwoCaptchaSolver(api_key=test_settings.TWOCAPTCHA_API_KEY, wg=wg)

	print(solver)

	# print("Credits: ", solver.getbalance())

	# res = solver.solve_simple_captcha(pathfile='/media/Storage/Scripts/xaDownloader/img.jpg')

	# print(res)




if __name__ == '__main__':
	recaptcha_test()
	# test()


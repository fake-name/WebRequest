



import logging
import abc


class CaptchaSolverBase(metaclass=abc.ABCMeta):
	# Abstract class (must be subclassed)
	__metaclass__ = abc.ABCMeta


	@abc.abstractmethod
	def captcha_service_name(self):
		return None


	def __init__(self, api_key, wg):
		self.log      = logging.getLogger("Main.WebRequest.Captcha.{}".format(self.captcha_service_name))

		self.api_key  = api_key
		self.wg       = wg

		# Default timeout is 5 minutes.
		self.waittime = 60 * 5


	@abc.abstractmethod
	def getbalance(self):
		assert False, "This shouldn't be hit!"


	@abc.abstractmethod
	def solve_simple_captcha(self, pathfile=None, filedata=None, filename=None):
		assert False, "This shouldn't be hit!"

	@abc.abstractmethod
	def solve_recaptcha(self, google_key, page_url, timeout = 15 * 60):
		assert False, "This shouldn't be hit!"

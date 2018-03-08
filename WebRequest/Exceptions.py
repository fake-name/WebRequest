


class WebGetException(Exception):
	def __init__(self, message, url):
		super().__init__(self, message)
		self.url         = url

	def __repr__(self):
		return '<WebGetException for url %s>' % (self.url, )

class ContentTypeError(WebGetException):
	pass

class ArgumentError(WebGetException):
	pass

class FetchFailureError(WebGetException):
	def __init__(self, message, url, err_content=None, err_reason=None, err_code=None):
		super().__init__(message, url=url)

		self.err_content = err_content
		self.err_reason  = err_reason
		self.err_code    = err_code

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return '<FetchFailureError %s -> %r for url: %s (%s)>' % (
				self.err_code,
				self.err_reason,
				self.url,
				"{%s}" % self.err_content
			)

# Specialized exceptions for garbage site
# "protection" bullshit
class GarbageSiteWrapper(WebGetException):
	pass
class CloudFlareWrapper(GarbageSiteWrapper):
	pass
class SucuriWrapper(GarbageSiteWrapper):
	pass


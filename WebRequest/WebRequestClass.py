#!/usr/bin/python3
import urllib.request
import urllib.parse
import urllib.error


import os.path

import time
import http.cookiejar

import traceback

import logging
import zlib
import codecs
import re
import sys
import gzip
import io
import socket
import json

from threading import Lock

import bs4
try:
	import socks
	from sockshandler import SocksiPyHandler
	HAVE_SOCKS = True
except ImportError:
	HAVE_SOCKS = False


cchardet = False

try:
	import cchardet
except ImportError:    # pragma: no cover
	pass


from . import HeaderParseMonkeyPatch

from . import ChromiumMixin
from . import Handlers
from . import iri2uri
from . import UA_Constants
from . import Domain_Constants
from . import Exceptions
from . import utility

from .SeleniumModules import SeleniumPhantomJSMixin
from .SeleniumModules import SeleniumChromiumMixin

#pylint: disable-msg=E1101, C0325, R0201, W0702, W0703

COOKIEWRITELOCK = Lock()

GLOBAL_COOKIE_FILE = None


# A urllib2 wrapper that provides error handling and logging, as well as cookie management. It's a bit crude, but it works.
# Also supports transport compresion.
# OOOOLLLLLLDDDDD, has lots of creaky internals. Needs some cleanup desperately, but lots of crap depends on almost everything.
# Arrrgh.

class WebGetRobust(
		ChromiumMixin.WebGetCrMixin,
		SeleniumPhantomJSMixin.WebGetSeleniumPjsMixin,
		SeleniumChromiumMixin.WebGetSeleniumChromiumMixin,

		):

	COOKIEFILE = 'cookies.lwp'				# the path and filename to save your cookies in
	cj = None
	cookielib = None
	opener = None

	errorOutCount = 1
	# retryDelay = 0.1
	retryDelay = 0.01

	data = None

	# creds is a list of 3-tuples that gets inserted into the password manager.
	# it is structured [(top_level_url1, username1, password1), (top_level_url2, username2, password2)]
	def __init__(self,
			creds         = None,
			logPath       = "Main.WebRequest",
			cookie_lock   = None,
			cloudflare    = True,
			auto_waf      = True,
			use_socks     = False,
			alt_cookiejar = None,
			custom_ua     = None,
			):

		super().__init__()

		self.rules = {}
		self.rules['auto_waf'] = cloudflare or auto_waf
		if cookie_lock:
			self.cookie_lock = cookie_lock
		elif alt_cookiejar:
			self.log.info("External cookie-jar specified. Not forcing cookiejar serialization.")
			self.cookie_lock = None
		else:
			self.cookie_lock = COOKIEWRITELOCK

		self.use_socks = use_socks
		# Override the global default socket timeout, so hung connections will actually time out properly.
		socket.setdefaulttimeout(5)

		self.log = logging.getLogger(logPath)
		# print("Webget init! Logpath = ", logPath)

		if custom_ua:
			self.log.info("User agent overridden!")
			self.browserHeaders = custom_ua
		else:
			# Due to general internet people douchebaggyness, I've basically said to hell with it and decided to spoof a whole assortment of browsers
			# It should keep people from blocking this scraper *too* easily
			self.browserHeaders = UA_Constants.getUserAgent()

		self.data = urllib.parse.urlencode(self.browserHeaders)

		if creds:
			print("Have credentials, installing password manager into urllib handler.")
			passManager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
			for url, username, password in creds:
				passManager.add_password(None, url, username, password)
			self.credHandler = Handlers.PreemptiveBasicAuthHandler(passManager)
		else:
			self.credHandler = None

		self.alt_cookiejar = alt_cookiejar
		self.__loadCookies()



	def getpage(self, requestedUrl, *args, **kwargs):
		try:
			return self.__getpage(requestedUrl, *args, **kwargs)

		except Exceptions.CloudFlareWrapper:
			if self.rules['auto_waf']:
				self.log.warning("Cloudflare failure! Doing automatic step-through.")
				if not self.stepThroughCloudFlareWaf(requestedUrl):
					raise Exceptions.FetchFailureError("Could not step through cloudflare!", requestedUrl)
				# Cloudflare cookie set, retrieve again
				return self.__getpage(requestedUrl, *args, **kwargs)

			else:
				self.log.info("Cloudflare without step-through setting!")
				raise

		except Exceptions.SucuriWrapper:
			# print("Sucuri!")
			if self.rules['auto_waf']:
				self.log.warning("Sucuri failure! Doing automatic step-through.")
				if not self.stepThroughSucuriWaf(requestedUrl):
					raise Exceptions.FetchFailureError("Could not step through Sucuri WAF bullshit!", requestedUrl)
				return self.__getpage(requestedUrl, *args, **kwargs)
			else:
				self.log.info("Sucuri without step-through setting!")
				raise



	def chunkReport(self, bytesSoFar, totalSize):
		if totalSize:
			percent = float(bytesSoFar) / totalSize
			percent = round(percent * 100, 2)
			self.log.info("Downloaded %d of %d bytes (%0.2f%%)" % (bytesSoFar, totalSize, percent))
		else:
			self.log.info("Downloaded %d bytes" % (bytesSoFar))

	def __chunkRead(self, response, chunkSize=2 ** 18, reportHook=None):
		contentLengthHeader = response.info().getheader('Content-Length')
		if contentLengthHeader:
			totalSize = contentLengthHeader.strip()
			totalSize = int(totalSize)
		else:
			totalSize = None
		bytesSoFar = 0
		pgContent = ""
		while 1:
			chunk = response.read(chunkSize)
			pgContent += chunk
			bytesSoFar += len(chunk)

			if not chunk:
				break

			if reportHook:
				reportHook(bytesSoFar, chunkSize, totalSize)

		return pgContent

	def getSoup(self, requestedUrl, *args, **kwargs):
		if 'returnMultiple' in kwargs and kwargs['returnMultiple']:
			raise Exceptions.ArgumentError("getSoup cannot be called with 'returnMultiple' being true", requestedUrl)

		if 'soup' in kwargs and kwargs['soup']:
			raise Exceptions.ArgumentError("getSoup contradicts the 'soup' directive!", requestedUrl)

		page = self.getpage(requestedUrl, *args, **kwargs)
		if isinstance(page, bytes):
			raise Exceptions.ContentTypeError("Received content not decoded! Cannot parse!", requestedUrl)

		soup = utility.as_soup(page)
		return soup

	def getJson(self, requestedUrl, *args, **kwargs):
		if 'returnMultiple' in kwargs and kwargs['returnMultiple']:
			raise Exceptions.ArgumentError("getSoup cannot be called with 'returnMultiple' being true", requestedUrl)

		attempts = 0
		while 1:
			try:
				page = self.getpage(requestedUrl, *args, **kwargs)
				if isinstance(page, bytes):
					page = page.decode(utility.determine_json_encoding(page))
					# raise ValueError("Received content not decoded! Cannot parse!")

				page = page.strip()
				ret = json.loads(page)
				return ret
			except ValueError:
				if attempts < 1:
					attempts += 1
					self.log.error("JSON Parsing issue retrieving content from page!")
					for line in traceback.format_exc().split("\n"):
						self.log.error("%s", line.rstrip())
					self.log.error("Retrying!")

					# Scramble our current UA
					self.browserHeaders = UA_Constants.getUserAgent()
					if self.alt_cookiejar:
						self.cj.init_agent(new_headers=self.browserHeaders)

					time.sleep(self.retryDelay)
				else:
					self.log.error("JSON Parsing issue, and retries exhausted!")
					# self.log.error("Page content:")
					# self.log.error(page)
					# with open("Error-ctnt-{}.json".format(time.time()), "w") as tmp_err_fp:
					# 	tmp_err_fp.write(page)
					raise



	def getSoupNoRedirects(self, *args, **kwargs):
		if 'returnMultiple' in kwargs:
			raise Exceptions.ArgumentError("getSoup cannot be called with 'returnMultiple'")

		if 'soup' in kwargs and kwargs['soup']:
			raise Exceptions.ArgumentError("getSoup contradicts the 'soup' directive!")

		kwargs['returnMultiple'] = True

		tgt_url = kwargs.get('requestedUrl', None)
		if not tgt_url:
			tgt_url = args[0]


		page, handle = self.getpage(*args, **kwargs)

		redirurl = handle.geturl()
		if redirurl != tgt_url:
			self.log.error("Requested %s, redirected to %s. Raising error", tgt_url, redirurl)

			raise Exceptions.RedirectedError("Requested %s, redirected to %s" % (
				tgt_url, redirurl))

		soup = as_soup(page)
		return soup


	def getFileAndName(self, *args, **kwargs):
		'''
		Give a requested page (note: the arguments for this call are forwarded to getpage()),
		return the content at the target URL and the filename for the target content as a
		2-tuple (pgctnt, hName) for the content at the target URL.

		The filename specified in the content-disposition header is used, if present. Otherwise,
		the last section of the url path segment is treated as the filename.
		'''

		pgctnt, hName, mime = self.getFileNameMime(*args, **kwargs)
		return pgctnt, hName

	def getFileNameMime(self, requestedUrl, *args, **kwargs):
		'''
		Give a requested page (note: the arguments for this call are forwarded to getpage()),
		return the content at the target URL, the filename for the target content, and
		the mimetype for the content at the target URL, as a 3-tuple (pgctnt, hName, mime).

		The filename specified in the content-disposition header is used, if present. Otherwise,
		the last section of the url path segment is treated as the filename.
		'''



		if 'returnMultiple' in kwargs:
			raise Exceptions.ArgumentError("getFileAndName cannot be called with 'returnMultiple'", requestedUrl)

		if 'soup' in kwargs and kwargs['soup']:
			raise Exceptions.ArgumentError("getFileAndName contradicts the 'soup' directive!", requestedUrl)

		kwargs["returnMultiple"] = True

		pgctnt, pghandle = self.getpage(requestedUrl, *args, **kwargs)

		info = pghandle.info()
		if not 'Content-Disposition' in info:
			hName = ''
		elif not 'filename=' in info['Content-Disposition']:
			hName = ''
		else:
			hName = info['Content-Disposition'].split('filename=')[1]
			# Unquote filename if it's quoted.
			if ((hName.startswith("'") and hName.endswith("'")) or hName.startswith('"') and hName.endswith('"')) and len(hName) >= 2:
				hName = hName[1:-1]

		mime = info.get_content_type()

		if not hName.strip():
			requestedUrl = pghandle.geturl()
			hName = urllib.parse.urlsplit(requestedUrl).path.split("/")[-1].strip()

		if "/" in hName:
			hName = hName.split("/")[-1]

		return pgctnt, hName, mime



	def getItem(self, itemUrl):
		content, handle = self.getpage(itemUrl, returnMultiple=True)

		if not content or not handle:
			raise urllib.error.URLError("Failed to retreive file from page '%s'!" % itemUrl)

		handle_info = handle.info()

		if handle_info['Content-Disposition'] and 'filename=' in handle_info['Content-Disposition'].lower():
			fileN = handle_info['Content-Disposition'].split("=", 1)[-1]
		else:
			fileN = urllib.parse.unquote(urllib.parse.urlparse(handle.geturl())[2].split("/")[-1])
			fileN = bs4.UnicodeDammit(fileN).unicode_markup
		mType = handle_info['Content-Type']

		# If there is an encoding in the content-type (or any other info), strip it out.
		# We don't care about the encoding, since WebFunctions will already have handled that,
		# and returned a decoded unicode object.
		if mType and ";" in mType:
			mType = mType.split(";")[0].strip()

		# *sigh*. So minus.com is fucking up their http headers, and apparently urlencoding the
		# mime type, because apparently they're shit at things.
		# Anyways, fix that.
		if mType and '%2F' in  mType:
			mType = mType.replace('%2F', '/')

		self.log.info("Retreived file of type '%s', name of '%s' with a size of %0.3f K", mType, fileN, len(content)/1000.0)
		return content, fileN, mType

	def getHead(self, url, addlHeaders=None):
		for x in range(9999):
			try:
				self.log.info("Doing HTTP HEAD request for '%s'", url)
				pgreq = self.__buildRequest(url, None, addlHeaders, None, req_class=Handlers.HeadRequest)
				pghandle = self.opener.open(pgreq, timeout=30)
				returl = pghandle.geturl()
				if returl != url:
					self.log.info("HEAD request returned a different URL '%s'", returl)

				return returl
			except socket.timeout as e:
				self.log.info("Timeout, retrying....")
				if x >= 3:
					self.log.error("Failure fetching: %s", url)
					raise Exceptions.FetchFailureError("Timout when fetching content", url)
			except urllib.error.URLError as e:
				# Continue even in the face of cloudflare crapping it's pants
				if e.code == 500 and e.geturl():
					return e.geturl()
				self.log.info("URLError, retrying....")
				if x >= 3:
					self.log.error("Failure fetching: %s", url)
					raise Exceptions.FetchFailureError("URLError when fetching content", e.geturl(), err_code=e.code)

	######################################################################################################################################################
	######################################################################################################################################################


	def __check_suc_cookie(self, components):
		'''
		This is only called if we're on a known sucuri-"protected" site.
		As such, if we do *not* have a sucuri cloudproxy cookie, we can assume we need to
		do the normal WAF step-through.
		'''
		netloc = components.netloc.lower()

		for cookie in self.cj:
			if cookie.domain_specified and (cookie.domain.lower().endswith(netloc)
				or (cookie.domain.lower().endswith("127.0.0.1") and (
				components.path == "/sucuri_shit_3" or components.path == "/sucuri_shit_2" ))):   # Allow testing
				if "sucuri_cloudproxy_uuid_" in cookie.name:
					return
		self.log.info("Missing cloudproxy cookie for known sucuri wrapped site. Doing a pre-emptive chromium fetch.")
		raise Exceptions.SucuriWrapper("WAF Shit", str(components))

	def __check_cf_cookie(self, components):
		netloc = components.netloc.lower()

		# TODO: Implement me?

		# for cookie in self.cj:
		# 	if cookie.domain_specified and (cookie.domain.lower().endswith(netloc)
		# 		or (cookie.domain.lower().endswith("127.0.0.1") and components.path == "/sucuri_shit_2")):   # Allow testing

		# 		if "sucuri_cloudproxy_uuid_" in cookie.name:
		# 			return
		# 		print("Target cookie!")
		# 		print("K -> V: %s -> %s" % (cookie.name, cookie.value))

		# 	print(cookie)
		# 	print(type(cookie))
		# 	print(cookie.domain)
		# raise RuntimeError
		pass

	def __pre_check(self, requestedUrl):
		'''
		Allow the pre-emptive fetching of sites with a full browser if they're known
		to be dick hosters.
		'''
		components = urllib.parse.urlsplit(requestedUrl)

		netloc_l = components.netloc.lower()
		if netloc_l in Domain_Constants.SUCURI_GARBAGE_SITE_NETLOCS:
			self.__check_suc_cookie(components)
		elif netloc_l in Domain_Constants.CF_GARBAGE_SITE_NETLOCS:
			self.__check_cf_cookie(components)
		elif components.path == '/sucuri_shit_2':
			self.__check_suc_cookie(components)
		elif components.path == '/sucuri_shit_3':
			self.__check_suc_cookie(components)
		elif components.path == '/cloudflare_under_attack_shit_2':
			self.__check_cf_cookie(components)
		elif components.path == '/cloudflare_under_attack_shit_3':
			self.__check_cf_cookie(components)


	def __getpage(self, requestedUrl, **kwargs):
		self.__pre_check(requestedUrl)

		self.log.info("Fetching content at URL: %s", requestedUrl)

		# strip trailing and leading spaces.
		requestedUrl = requestedUrl.strip()

		# If we have 'soup' as a param, just pop it, and call `getSoup()`.
		if 'soup' in kwargs and kwargs['soup']:
			self.log.warning("'soup' kwarg is depreciated. Please use the `getSoup()` call instead.")
			kwargs.pop('soup')
			return self.getSoup(requestedUrl, **kwargs)

		# Decode the kwargs values
		addlHeaders    = kwargs.setdefault("addlHeaders",     None)
		returnMultiple = kwargs.setdefault("returnMultiple",  False)
		callBack       = kwargs.setdefault("callBack",        None)
		postData       = kwargs.setdefault("postData",        None)
		retryQuantity  = kwargs.setdefault("retryQuantity",   None)
		nativeError    = kwargs.setdefault("nativeError",     False)
		binaryForm     = kwargs.setdefault("binaryForm",      False)

		# Conditionally encode the referrer if needed, because otherwise
		# urllib will barf on unicode referrer values.
		if addlHeaders and 'Referer' in addlHeaders:
			addlHeaders['Referer'] = iri2uri.iri2uri(addlHeaders['Referer'])


		retryCount = 0
		err_content = None
		err_reason = None
		err_code = None

		while 1:

			pgctnt = None
			pghandle = None

			pgreq = self.__buildRequest(requestedUrl, postData, addlHeaders, binaryForm)

			errored = False
			lastErr = ""

			retryCount = retryCount + 1

			if (retryQuantity and retryCount > retryQuantity) or (not retryQuantity and retryCount > self.errorOutCount):
				self.log.error("Failed to retrieve Website : %s at %s All Attempts Exhausted", pgreq.get_full_url(), time.ctime(time.time()))
				pgctnt = None
				try:
					self.log.critical("Critical Failure to retrieve page! %s at %s, attempt %s", pgreq.get_full_url(), time.ctime(time.time()), retryCount)
					self.log.critical("Error: %s", lastErr)
					self.log.critical("Exiting")
				except:
					self.log.critical("And the URL could not be printed due to an encoding error")
				break

			#print "execution", retryCount
			try:
				# print("Getpage!", requestedUrl, kwargs)
				pghandle = self.opener.open(pgreq, timeout=30)					# Get Webpage
				# print("Gotpage")

			except Exceptions.GarbageSiteWrapper as err:
				# print("garbage site:")
				raise err

			except urllib.error.HTTPError as err:								# Lotta logging
				self.log.warning("Error opening page: %s at %s On Attempt %s.", pgreq.get_full_url(), time.ctime(time.time()), retryCount)
				self.log.warning("Error Code: %s", err)

				if err.fp:
					err_content = err.fp.read()
					encoded = err.hdrs.get('Content-Encoding', None)
					if encoded:
						_, err_content = self.__decompressContent(encoded, err_content)

				err_reason = err.reason
				err_code   = err.code
				lastErr    = err
				try:

					self.log.warning("Original URL: %s", requestedUrl)
					errored = True
				except:
					self.log.warning("And the URL could not be printed due to an encoding error")

				if err.code == 404:
					#print "Unrecoverable - Page not found. Breaking"
					self.log.critical("Unrecoverable - Page not found. Breaking")
					break

				time.sleep(self.retryDelay)
				if err.code == 503:
					if err_content:
						self._check_waf(err_content, requestedUrl)

				# So I've been seeing this causing CF to bounce too.
				# As such, poke through those via chromium too.
				if err.code == 502:
					if err_content:
						self._check_waf(err_content, requestedUrl)

			except UnicodeEncodeError:
				self.log.critical("Unrecoverable Unicode issue retrieving page - %s", requestedUrl)
				for line in traceback.format_exc().split("\n"):
					self.log.critical("%s", line.rstrip())
				self.log.critical("Parameters:")
				self.log.critical("	requestedUrl: '%s'", requestedUrl)
				self.log.critical("	postData:     '%s'", postData)
				self.log.critical("	addlHeaders:  '%s'", addlHeaders)
				self.log.critical("	binaryForm:   '%s'", binaryForm)

				err_reason = "Unicode Decode Error"
				err_code   = -1
				err_content = traceback.format_exc()

				break

			except Exception as e:
				errored = True
				#traceback.print_exc()
				lastErr = sys.exc_info()
				self.log.warning("Retreival failed. Traceback:")
				self.log.warning(str(lastErr))
				self.log.warning(traceback.format_exc())

				self.log.warning("Error Retrieving Page! - Trying again - Waiting %s seconds", self.retryDelay)

				try:
					self.log.critical("Error on page - %s", requestedUrl)
				except:
					self.log.critical("And the URL could not be printed due to an encoding error")

				time.sleep(self.retryDelay)

				err_reason = "Unhandled general exception"
				err_code   = -1
				err_content = traceback.format_exc()

				continue

			if pghandle != None:
				self.log.info("Request for URL: %s succeeded at %s On Attempt %s. Recieving...", pgreq.get_full_url(), time.ctime(time.time()), retryCount)
				pgctnt = self.__retreiveContent(pgreq, pghandle, callBack)

				# if __retreiveContent did not return false, it managed to fetch valid results, so break
				if pgctnt != False:
					break

		if errored and pghandle != None:
			print(("Later attempt succeeded %s" % pgreq.get_full_url()))
		elif (errored or not pgctnt) and pghandle is None:

			if lastErr and nativeError:
				raise lastErr
			raise Exceptions.FetchFailureError("Failed to retreive page", requestedUrl,
				err_content=err_content, err_code=err_code, err_reason=err_reason)

		if returnMultiple:

			return pgctnt, pghandle
		else:
			return pgctnt

	######################################################################################################################################################
	######################################################################################################################################################

	def __decode_text_content(self, pageContent, cType):

		# this *should* probably be done using a parser.
		# However, it seems to be grossly overkill to shove the whole page (which can be quite large) through a parser just to pull out a tag that
		# should be right near the page beginning anyways.
		# As such, it's a regular expression for the moment

		# Regex is of bytes type, since we can't convert a string to unicode until we know the encoding the
		# bytes string is using, and we need the regex to get that encoding
		coding = re.search(b"charset=[\'\"]?([a-zA-Z0-9\-]*)[\'\"]?", pageContent, flags=re.IGNORECASE)

		cType = b""
		charset = None
		try:
			if coding:
				cType = coding.group(1)
				codecs.lookup(cType.decode("ascii"))
				charset = cType.decode("ascii")

		except LookupError:

			# I'm actually not sure what I was thinking when I wrote this if statement. I don't think it'll ever trigger.
			if (b";" in cType) and (b"=" in cType): 		# the server is reporting an encoding. Now we use it to decode the

				dummy_docType, charset = cType.split(b";")
				charset = charset.split(b"=")[-1]

		if cchardet:
			inferred = cchardet.detect(pageContent)
			if inferred and inferred['confidence'] is None:
				# If we couldn't infer a charset, just short circuit and return the content.
				# It's probably binary.
				return pageContent

			elif inferred and inferred['confidence'] is not None and inferred['confidence'] > 0.8:
				charset = inferred['encoding']
				self.log.info("Cchardet inferred encoding: %s", charset)

		else:
			self.log.warning("Missing cchardet!")

		if not charset:
			self.log.warning("Could not find encoding information on page - Using default charset. Shit may break!")
			charset = "utf-8"

		try:
			pageContent = str(pageContent, charset)

		except UnicodeDecodeError:
			self.log.error("Encoding Error! Stripping invalid chars.")
			pageContent = pageContent.decode('utf-8', errors='ignore')

		return pageContent

	def __buildRequest(self, pgreq, postData, addlHeaders, binaryForm, req_class = None):
		if req_class is None:
			req_class = urllib.request.Request

		pgreq = iri2uri.iri2uri(pgreq)

		try:
			params = {}
			headers = {}
			if postData != None:
				self.log.info("Making a post-request! Params: '%s'", postData)
				if isinstance(postData, str):
					params['data'] = postData.encode("utf-8")
				elif isinstance(postData, dict):
					for key, parameter in postData.items():
						self.log.info("	Item: '%s' -> '%s'", key, parameter)
					params['data'] = urllib.parse.urlencode(postData).encode("utf-8")
			if addlHeaders != None:
				self.log.info("Have additional GET parameters!")
				for key, parameter in addlHeaders.items():
					self.log.info("	Item: '%s' -> '%s'", key, parameter)
				headers = addlHeaders
			if binaryForm:
				self.log.info("Binary form submission!")
				if 'data' in params:
					raise Exceptions.ArgumentError("You cannot make a binary form post and a plain post request at the same time!", pgreq)

				params['data']            = binaryForm.make_result()
				headers['Content-type']   =  binaryForm.get_content_type()
				headers['Content-length'] =  len(params['data'])

			return req_class(pgreq, headers=headers, **params)

		except:
			self.log.critical("Invalid header or url")
			raise

	def __decompressContent(self, coding, pgctnt):
		"""
		This is really obnoxious
		"""
		#preLen = len(pgctnt)
		if coding == 'deflate':
			compType = "deflate"
			bits_opts = [
				-zlib.MAX_WBITS,       # deflate
				 zlib.MAX_WBITS,       # zlib
				 zlib.MAX_WBITS | 16,  # gzip
				 zlib.MAX_WBITS | 32,  # "automatic header detection"

				 0,  # Try to guess from header

				 # Try all the raw window options.
				 -8, -9, -10, -11, -12, -13, -14, -15,

				 # Stream with zlib headers
				  8,  9,  10,  11,  12,  13,  14,  15,

				 # With gzip header+trailer
				  8+16,  9+16,  10+16,  11+16,  12+16,  13+16,  14+16,  15+16,
				 # Automatic detection
				  8+32,  9+32,  10+32,  11+32,  12+32,  13+32,  14+32,  15+32,

			]

			err = None

			for wbits_val in bits_opts:
				try:
					pgctnt = zlib.decompress(pgctnt, wbits_val)
					return compType, pgctnt
				except zlib.error as e:
					err = e

			# We can't get here without err having thrown.
			raise err

		elif coding == 'gzip':
			compType = "gzip"

			buf = io.BytesIO(pgctnt)
			f = gzip.GzipFile(fileobj=buf)
			pgctnt = f.read()

		elif coding == "sdch":
			raise Exceptions.ContentTypeError("Wait, someone other then google actually supports SDCH compression (%s)?" % pgreq)

		else:
			compType = "none"

		return compType, pgctnt

	def __decodeTextContent(self, pgctnt, cType):

		if cType:
			if (";" in cType) and ("=" in cType):
				# the server is reporting an encoding. Now we use it to decode the content
				# Some wierdos put two charsets in their headers:
				# `text/html;Charset=UTF-8;charset=UTF-8`
				# Split, and take the first two entries.
				docType, charset = cType.split(";")[:2]
				charset = charset.split("=")[-1]

				# Only decode content marked as text (yeah, google is serving zip files
				# with the content-disposition charset header specifying "UTF-8") or
				# specifically allowed other content types I know are really text.
				decode = ['application/atom+xml', 'application/xml', "application/json", 'text']
				if any([item in docType for item in decode]):
					try:
						pgctnt = str(pgctnt, charset)
					except UnicodeDecodeError:
						self.log.error("Encoding Error! Stripping invalid chars.")
						pgctnt = pgctnt.decode('utf-8', errors='ignore')

			else:
				# The server is not reporting an encoding in the headers.
				# Use content-aware mechanisms for determing the content encoding.


				if "text/html" in cType or             \
					'text/javascript' in cType or      \
					'text/css' in cType or             \
					'application/json' in cType or     \
					'application/xml' in cType or      \
					'application/atom+xml' in cType or \
					cType.startswith("text/"):				# If this is a html/text page, we want to decode it using the local encoding
					pgctnt = self.__decode_text_content(pgctnt, cType)

				elif "text" in cType:
					self.log.critical("Unknown content type!")
					self.log.critical(cType)

		else:
			self.log.critical("No content disposition header!")
			self.log.critical("Cannot guess content type!")

		return pgctnt

	def __retreiveContent(self, pgreq, pghandle, callBack):
		try:
			# If we have a progress callback, call it for chunked read.
			# Otherwise, just read in the entire content.
			if callBack:
				pgctnt = self.__chunkRead(pghandle, 2 ** 17, reportHook=callBack)
			else:
				pgctnt = pghandle.read()


			if pgctnt is None:
				return False

			self.log.info("URL fully retrieved.")

			preDecompSize = len(pgctnt)/1000.0

			encoded = pghandle.headers.get('Content-Encoding')
			compType, pgctnt = self.__decompressContent(encoded, pgctnt)


			decompSize = len(pgctnt)/1000.0
			# self.log.info("Page content type = %s", type(pgctnt))
			cType = pghandle.headers.get("Content-Type")
			if compType == 'none':
				self.log.info("Compression type = %s. Content Size = %0.3fK. File type: %s.", compType, decompSize, cType)
			else:
				self.log.info("Compression type = %s. Content Size compressed = %0.3fK. Decompressed = %0.3fK. File type: %s.", compType, preDecompSize, decompSize, cType)

			self._check_waf(pgctnt, pgreq.get_full_url())

			pgctnt = self.__decodeTextContent(pgctnt, cType)

			return pgctnt


		except Exceptions.GarbageSiteWrapper as err:
			raise err
		except Exception:

			self.log.error("Exception!")
			self.log.error(str(sys.exc_info()))
			traceback.print_exc()
			self.log.error("Error Retrieving Page! - Transfer failed. Waiting %s seconds before retrying", self.retryDelay)

			try:
				self.log.critical("Critical Failure to retrieve page! %s at %s", pgreq.get_full_url(), time.ctime(time.time()))
				self.log.critical("Exiting")
			except:
				self.log.critical("And the URL could not be printed due to an encoding error")
			self.log.error(pghandle)
			time.sleep(self.retryDelay)

		return False


		# HUGE GOD-FUNCTION.
		# OH GOD FIXME.

		# postData expects a dict
		# addlHeaders also expects a dict

	def _check_waf(self, pageContent, pageUrl):
		assert isinstance(pageContent, bytes), "Item pageContent must be of type bytes, received %s" % (type(pageContent), )
		assert isinstance(pageUrl, str), "Item pageUrl must be of type str, received %s" % (type(pageUrl), )

		if b"sucuri_cloudproxy_js=" in pageContent:
			raise Exceptions.SucuriWrapper("WAF Shit", pageUrl)

		if b'This process is automatic. Your browser will redirect to your requested content shortly.' in pageContent:
			raise Exceptions.CloudFlareWrapper("WAF Shit", pageUrl)

		if b'is currently offline. However, because the site uses Cloudflare\'s Always Online' in pageContent:
			raise Exceptions.CloudFlareWrapper("WAF Shit", pageUrl)

	######################################################################################################################################################
	######################################################################################################################################################

	def __loadCookies(self):

		if self.alt_cookiejar is not None:
			self.alt_cookiejar.init_agent(new_headers=self.browserHeaders)
			self.cj = self.alt_cookiejar
		else:
			self.cj = http.cookiejar.LWPCookieJar()		# This is a subclass of FileCookieJar
												# that has useful load and save methods
		if self.cj is not None:
			if os.path.isfile(self.COOKIEFILE):
				try:
					self.__updateCookiesFromFile()
					# self.log.info("Loading CookieJar")
				except:
					self.log.critical("Cookie file is corrupt/damaged?")
					try:
						os.remove(self.COOKIEFILE)
					except FileNotFoundError:
						pass
			if http.cookiejar is not None:
				# self.log.info("Installing CookieJar")
				self.log.debug(self.cj)
				cookieHandler = urllib.request.HTTPCookieProcessor(self.cj)
				args = (cookieHandler, Handlers.HTTPRedirectHandler)
				if self.credHandler:
					print("Have cred handler. Building opener using it")
					args += (self.credHandler, )
				if self.use_socks:
					print("Using Socks handler")
					if not HAVE_SOCKS:
						raise RuntimeError("SOCKS Use specified, and no socks installed!")
					args = (SocksiPyHandler(socks.SOCKS5, "127.0.0.1", 9050), ) + args

				self.opener = urllib.request.build_opener(*args)
				#self.opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)')]
				self.opener.addheaders = self.browserHeaders
				#urllib2.install_opener(self.opener)

		for cookie in self.cj:
			self.log.debug(cookie)
			#print cookie

	def _syncCookiesFromFile(self):
		# self.log.info("Synchronizing cookies with cookieFile.")
		if os.path.isfile(self.COOKIEFILE):
			self.cj.save("cookietemp.lwp")
			self.cj.load(self.COOKIEFILE)
			self.cj.load("cookietemp.lwp")
		# First, load any changed cookies so we don't overwrite them
		# However, we want to persist any cookies that we have that are more recent then the saved cookies, so we temporarily save
		# the cookies in memory to a temp-file, then load the cookiefile, and finally overwrite the loaded cookies with the ones from the
		# temp file

	def __updateCookiesFromFile(self):
		if os.path.exists(self.COOKIEFILE):
			# self.log.info("Synchronizing cookies with cookieFile.")
			self.cj.load(self.COOKIEFILE)
		# Update cookies from cookiefile

	def addCookie(self, inCookie):
		self.log.info("Updating cookie!")
		self.cj.set_cookie(inCookie)


	def addSeleniumCookie(self, cookieDict):
		'''
		Install a cookie exported from a selenium webdriver into
		the active opener
		'''
		# print cookieDict
		cookie = http.cookiejar.Cookie(
				version            = 0,
				name               = cookieDict['name'],
				value              = cookieDict['value'],
				port               = None,
				port_specified     = False,
				domain             = cookieDict['domain'],
				domain_specified   = True,
				domain_initial_dot = False,
				path               = cookieDict['path'],
				path_specified     = False,
				secure             = cookieDict['secure'],
				expires            = cookieDict['expiry'] if 'expiry' in cookieDict else None,
				discard            = False,
				comment            = None,
				comment_url        = None,
				rest               = {"httponly":"%s" % cookieDict['httponly'] if 'httponly' in cookieDict else False},
				rfc2109            = False
			)

		self.addCookie(cookie)

	def saveCookies(self, halting=False):

		if self.cookie_lock:
			locked = self.cookie_lock.acquire(timeout=5)
			if not locked:
				self.log.error("Failed to acquire cookie-lock!")
				return

		# print("Have %d cookies before saving cookiejar" % len(self.cj))
		try:
			# self.log.info("Trying to save cookies!")
			if self.cj is not None:							# If cookies were used

				self._syncCookiesFromFile()

				# self.log.info("Have cookies to save")
				for cookie in self.cj:
					# print(cookie)
					# print(cookie.expires)

					if isinstance(cookie.expires, int) and cookie.expires > 30000000000:		# Clamp cookies that expire stupidly far in the future because people are assholes
						cookie.expires = 30000000000

				# self.log.info("Calling save function")
				self.cj.save(self.COOKIEFILE)					# save the cookies again


				# self.log.info("Cookies Saved")
			else:
				self.log.info("No cookies to save?")
		except Exception as e:
			pass
			# The destructor call order is too incoherent, and shit fails
			# during the teardown with null-references. The error printout is
			# not informative, so just silence it.
			# print("Possible error on exit (or just the destructor): '%s'." % e)
		finally:
			if self.cookie_lock:
				self.cookie_lock.release()

		# print("Have %d cookies after saving cookiejar" % len(self.cj))
		if not halting:
			self._syncCookiesFromFile()
		# print "Have %d cookies after reloading cookiejar" % len(self.cj)

	def clearCookies(self):

		if self.cookie_lock:
			locked = self.cookie_lock.acquire(timeout=5)
			if not locked:
				self.log.error("Failed to acquire cookie-lock!")
				return
		try:
			self.cj.clear()
			self.cj.save(self.COOKIEFILE)					# save the cookies again
			self.cj.save("cookietemp.lwp")
			self._syncCookiesFromFile()
		finally:
			if self.cookie_lock:
				self.cookie_lock.release()

	def getCookies(self):

		if self.cookie_lock:
			locked = self.cookie_lock.acquire(timeout=5)
			if not locked:
				raise RuntimeError("Could not acquire lock on cookiejar")

		try:
			# self.log.info("Trying to save cookies!")
			if self.cj is not None:							# If cookies were used
				self._syncCookiesFromFile()
		finally:
			if self.cookie_lock:
				self.cookie_lock.release()

		return self.cj

	######################################################################################################################################################
	######################################################################################################################################################

	def __del__(self):
		# print "WGH Destructor called!"
		# print("WebRequest __del__")
		self.saveCookies(halting=True)

		sup = super()
		if hasattr(sup, '__del__'):
			sup.__del__()





	def stepThroughCloudFlareWaf(self, url):
		return self.stepThroughJsWaf(url, titleNotContains='Just a moment...')
	def stepThroughSucuriWaf(self, url):
		return self.stepThroughJsWaf(url, titleNotContains="You are being redirected...")

	def stepThroughJsWaf(self, *args, **kwargs):
		# Shim to the underlying web browser of choice
		return self.stepThroughJsWaf_bare_chromium(*args, **kwargs)


	# Compat for old code.
	def stepThroughCloudFlare(self, *args, **kwargs):
		return self.stepThroughJsWaf(*args, **kwargs)

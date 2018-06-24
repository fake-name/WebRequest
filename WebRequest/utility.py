
import bs4
from . import Exceptions

def as_soup(in_str):

	# I already pre-decode the content, and lxml barfs horribly when fed
	# content with a charset specified as iso-8859-1.
	# See https://bugs.launchpad.net/beautifulsoup/+bug/972466 and
	# https://bugs.launchpad.net/lxml/+bug/963936
	if 'charset=iso-8859-1' in in_str:
		in_str = in_str.replace("charset=iso-8859-1", "charset=UTF-8")
	if 'charset=ISO-8859-1' in in_str:
		in_str = in_str.replace("charset=ISO-8859-1", "charset=UTF-8")

	return bs4.BeautifulSoup(in_str, "lxml")


def determine_json_encoding(json_bytes):
	'''
	Given the fact that the first 2 characters in json are guaranteed to be ASCII, we can use
	these to determine the encoding.
	See: http://tools.ietf.org/html/rfc4627#section-3

	Copied here:
	   Since the first two characters of a JSON text will always be ASCII
	   characters [RFC0020], it is possible to determine whether an octet
	   stream is UTF-8, UTF-16 (BE or LE), or UTF-32 (BE or LE) by looking
	   at the pattern of nulls in the first four octets.

			   00 00 00 xx  UTF-32BE
			   00 xx 00 xx  UTF-16BE
			   xx 00 00 00  UTF-32LE
			   xx 00 xx 00  UTF-16LE
			   xx xx xx xx  UTF-8
	'''

	assert isinstance(json_bytes, bytes), "`determine_json_encoding()` can only operate on bytestring inputs"

	if len(json_bytes) > 4:
		b1, b2, b3, b4 = json_bytes[0], json_bytes[1], json_bytes[2], json_bytes[3]
		if   b1 == 0 and b2 == 0 and b3 == 0 and b4 != 0:
			return "UTF-32BE"
		elif b1 == 0 and b2 != 0 and b3 == 0 and b4 != 0:
			return "UTF-16BE"
		elif b1 != 0 and b2 == 0 and b3 == 0 and b4 == 0:
			return "UTF-32LE"
		elif b1 != 0 and b2 == 0 and b3 != 0 and b4 == 0:
			return "UTF-16LE"
		elif b1 != 0 and b2 != 0 and b3 != 0 and b4 != 0:
			return "UTF-8"
		else:
			raise Exceptions.ContentTypeError("Unknown encoding!")

	elif len(json_bytes) > 2:
		b1, b2 = json_bytes[0], json_bytes[1]
		if   b1 == 0 and b2 == 0:
			return "UTF-32BE"
		elif b1 == 0 and b2 != 0:
			return "UTF-16BE"
		elif b1 != 0 and b2 == 0:
			raise Exceptions.ContentTypeError("Json string too short to definitively infer encoding.")
		elif b1 != 0 and b2 != 0:
			return "UTF-8"
		else:
			raise Exceptions.ContentTypeError("Unknown encoding!")

	raise Exceptions.ContentTypeError("Input string too short to guess encoding!")


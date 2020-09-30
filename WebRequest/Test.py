

# A urllib2 wrapper that provides error handling and logging, as
# well as cookie management. It's a bit crude, but it works.
# Also supports transport compresion.
# OOOOLLLLLLDDDDD, has lots of creaky internals. Needs some cleanup
# desperately, but lots of crap depends on almost everything.
# Arrrgh.
#
# This code is terrible, and probably shouldn't be used by anyone ever.

import logging
from . import WebGetRobust

def test():
	print("Test!")
	logging.basicConfig(level=logging.DEBUG)
	cs = WebGetRobust()
	cs.handle_cloudflare_cloudscraper("https://www.cloudflare.com/")



if __name__ == '__main__':
	test()


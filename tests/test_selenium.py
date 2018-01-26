import unittest
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import WebRequest

from . import testing_server


class CommonTests():

	def test_fetch_wg(self):
		page = self.wg.getpage("http://localhost:{}".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_fetch_2(self):
		page_1, fname_1, mtype_1 = self.get_item_callable("http://localhost:{}".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(page_1, '<html><head></head><body>Root OK?</body></html>')

	def test_fetch_3(self):
		# Because PJS is retarded, it ALWAYS wraps content in html shit unless you specify the content is "text/html". If you do that, it then proceds to only
		# add /some/ of the html tag garbage
		page_2, fname_2, mtype_2 = self.get_item_callable("http://localhost:{}/raw-txt".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(
						page_2,
						'<html><head></head><body><pre style="word-wrap: break-word; white-space: pre-wrap;">Root OK?</pre></body></html>'
		)
	def test_fetch_4(self):
		page_1, fname_1, mtype_1 = self.get_item_callable("http://localhost:{}/content/have-title".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(page_1, '<html><head><title>I can haz title?</title></head><body>This page has a title!</body></html>')

	def test_fetch_5(self):
		# Because PJS is retarded, it ALWAYS wraps content in html shit unless you specify the content is "text/html". If you do that, it then proceds to only
		# add /some/ of the html tag garbage
		page_2, fname_2, mtype_2 = self.get_item_callable("http://localhost:{}/content/no-title".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(page_2, '<html><head></head><body>This page has no title. Sadface.jpg</body></html>')

	def test_head_1(self):
		url_1 = "http://localhost:{}/raw-txt".format(self.mock_server_port)
		purl_1 = self.get_head_callable(url_1)
		self.assertEqual(purl_1, url_1)

		url_2 = "http://localhost:{}/redirect/to-1".format(self.mock_server_port)
		purl_2 = self.get_head_callable("http://localhost:{}/redirect/from-1".format(self.mock_server_port))
		self.assertEqual(purl_2, url_2)

	def test_head_title_1(self):
		url_1 = "http://localhost:{}/content/have-title".format(self.mock_server_port)
		ret_1 = self.get_head_title_callable(url_1)
		self.assertEqual(ret_1['url'], url_1)
		self.assertEqual(ret_1['title'], 'I can haz title?')

		url_2 = "http://localhost:{}/content/no-title".format(self.mock_server_port)
		ret_2 = self.get_head_title_callable(url_2)
		self.assertEqual(ret_2['url'], url_2)
		self.assertEqual(ret_2['title'], '')


class TestPhantomJS(unittest.TestCase, CommonTests):
	def setUp(self):
		self.wg = WebRequest.WebGetRobust()

		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_annoying_pjs=True)

		self.get_item_callable = self.wg.getItemPhantomJS
		self.get_head_callable = self.wg.getHeadPhantomJS
		self.get_head_title_callable = self.wg.getHeadTitlePhantomJS

	def tearDown(self):
		self.mock_server.shutdown()


	# We expect to get the same value as passed, since pjs will not resolve out
	# the bad redirects.
	# Note we have to restart phantomjs for these tests, because otherwise it remembers state (this is why they're separate tests).
	def test_head_pjs_2(self):
		url_3 = "http://localhost:{}/redirect/bad-1".format(self.mock_server_port)
		purl_3 = self.wg.getHeadPhantomJS("http://localhost:{}/redirect/bad-1".format(self.mock_server_port))
		self.assertEqual(purl_3, url_3)

	def test_head_pjs_3(self):
		# Somehow, this turns into 'about:blank'. NFI how
		url_4 = "about:blank"
		purl_4 = self.wg.getHeadPhantomJS("http://localhost:{}/redirect/bad-2".format(self.mock_server_port))
		self.assertEqual(purl_4, url_4)

	def test_head_pjs_4(self):
		# Somehow, this turns into 'about:blank'. NFI how
		url_5 = "about:blank"
		purl_5 = self.wg.getHeadPhantomJS("http://localhost:{}/redirect/bad-3".format(self.mock_server_port))
		self.assertEqual(purl_5, url_5)



class TestSeleniumChromium(unittest.TestCase, CommonTests):
	def setUp(self):
		self.wg = WebRequest.WebGetRobust()

		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_selenium_garbage_chromium=True)

		self.get_item_callable = self.wg.getItemSeleniumChromium
		self.get_head_callable = self.wg.getHeadSeleniumChromium
		self.get_head_title_callable = self.wg.getHeadTitleSeleniumChromium

	def tearDown(self):
		self.mock_server.shutdown()

	# We expect to get the same value as passed, since scromium will not resolve out
	# the bad redirects.
	# Note we have to restart phantomjs for these tests, because otherwise it remembers state (this is why they're separate tests).
	def test_head_scromium_2(self):
		url_3 = "http://localhost:{}/redirect/bad-1".format(self.mock_server_port)
		purl_3 = self.wg.getHeadSeleniumChromium("http://localhost:{}/redirect/bad-1".format(self.mock_server_port))
		self.assertEqual(purl_3, url_3)

	def test_head_scromium_3(self):
		# Somehow, this turns into 'about:blank'. NFI how
		url_4 = "http://localhost:{}/redirect/bad-2".format(self.mock_server_port)
		purl_4 = self.wg.getHeadSeleniumChromium(url_4)
		self.assertEqual(purl_4, url_4)

	def test_head_scromium_4(self):
		# Somehow, this turns into 'about:blank'. NFI how
		in_url_5 = "http://localhost:{}/redirect/bad-3".format(self.mock_server_port)
		url_5 = "data:,"
		purl_5 = self.wg.getHeadSeleniumChromium(in_url_5)
		self.assertEqual(purl_5, url_5)

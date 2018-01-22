import unittest
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import WebRequest

def capture_expected_headers(expected_headers, test_context, is_chromium=False):

	# print("Capturing expected headers:")
	# print(expected_headers)

	class MockServerRequestHandler(BaseHTTPRequestHandler):
		def do_GET(self):
			# Process an HTTP GET request and return a response with an HTTP 200 status.
			# print("Path: ", self.path)
			# print("Headers: ", self.headers)

			for key, value in expected_headers:
				if key == 'Accept-Encoding':
					# So PhantomJS monkeys with accept-encoding headers
					# Just ignore that particular header, I guess.
					pass

				# Selenium is fucking retarded, and I can't override the user-agent
				# and other assorted parameters via their API at all.
				elif is_chromium and key == 'Accept-Language':
					pass
				elif is_chromium and key == 'Accept':
					pass
				else:
					v1 = value.replace(" ", "")
					v2 = self.headers[key]
					if v2 is None:
						v2 = ""
					v2 = v2.replace(" ", "")
					test_context.assertEqual(v1, v2, msg="Mismatch in header parameter {} : {} -> {}".format(key, value, self.headers[key]))

			if self.path == "/":
				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"Root OK?")

			elif self.path == "/raw-txt":
				self.send_response(200)
				self.send_header('Content-type', "text/plain")
				self.end_headers()
				self.wfile.write(b"Root OK?")

			elif self.path == "/redirect/bad-1":
				self.send_response(302)
				self.end_headers()

			elif self.path == "/redirect/bad-2":
				self.send_response(302)
				self.send_header('location', "bad-2")
				self.end_headers()

			elif self.path == "/redirect/bad-3":
				self.send_response(302)
				self.send_header('location', "gopher://www.google.com")
				self.end_headers()

			elif self.path == "/redirect/from-1":
				self.send_response(302)
				self.send_header('location', "to-1")
				self.end_headers()

			if self.path == "/redirect/to-1":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"Redirect-To-1")

			elif self.path == "/redirect/from-2":
				self.send_response(302)
				self.send_header('uri', "to-2")
				self.end_headers()

			if self.path == "/redirect/to-2":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"Redirect-To-2")

			elif self.path == "/redirect/from-3":
				self.send_response(302)
				newurl = "http://{}:{}".format(self.server.server_address[0], self.server.server_address[1])
				self.send_header('uri', newurl)
				self.end_headers()

			elif self.path == "/content/have-title":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"<html><head><title>I can haz title?</title></head><body>This page has a title!</body></html>")

			elif self.path == "/content/no-title":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"<html><head></head><body>This page has no title. Sadface.jpg</body></html>")
	return MockServerRequestHandler

def get_free_port():
	s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
	s.bind(('localhost', 0))
	address, port = s.getsockname()
	s.close()
	return port


class CommonTests():

	def test_fetch_1(self):
		page = self.wg.getpage("http://localhost:{}".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_fetch_2(self):
		page_1, fname_1, mtype_1 = self.get_item_callable("http://localhost:{}".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(page_1, '<html><head></head><body>Root OK?</body></html>')

		# Because PJS is retarded, it ALWAYS wraps content in html shit unless you specify the content is "text/html". If you do that, it then proceds to only
		# add /some/ of the html tag garbage
		page_2, fname_2, mtype_2 = self.get_item_callable("http://localhost:{}/raw-txt".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(
						page_2,
						'<html><head></head><body><pre style="word-wrap: break-word; white-space: pre-wrap;">Root OK?</pre></body></html>'
		)
	def test_fetch_3(self):
		page_1, fname_1, mtype_1 = self.get_item_callable("http://localhost:{}/content/have-title".format(self.mock_server_port))
		# I think all this garbage is phantomjs/selenium deciding they know what I want the content to look like for me.
		# Note that the content isn't specified to be HTML ANYWHERE.
		self.assertEqual(page_1, '<html><head><title>I can haz title?</title></head><body>This page has a title!</body></html>')

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
		self.mock_server_port = get_free_port()
		self.mock_server = HTTPServer(('localhost', self.mock_server_port), capture_expected_headers(self.wg.browserHeaders, self))

		# Start running mock server in a separate thread.
		# Daemon threads automatically shut down when the main process exits.
		self.mock_server_thread = Thread(target=self.mock_server.serve_forever)
		self.mock_server_thread.setDaemon(True)
		self.mock_server_thread.start()

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
		self.mock_server_port = get_free_port()
		self.mock_server = HTTPServer(('localhost', self.mock_server_port), capture_expected_headers(self.wg.browserHeaders, self, is_chromium=True))

		# Start running mock server in a separate thread.
		# Daemon threads automatically shut down when the main process exits.
		self.mock_server_thread = Thread(target=self.mock_server.serve_forever)
		self.mock_server_thread.setDaemon(True)
		self.mock_server_thread.start()

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

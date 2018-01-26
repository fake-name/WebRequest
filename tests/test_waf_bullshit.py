import unittest
import socket
import json
import base64
import zlib
import gzip
import bs4
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import WebRequest
from . import testing_server



class TestWafPokeThrough(unittest.TestCase):
	def setUp(self):

		self.wg = WebRequest.WebGetRobust()
		self.wg.clearCookies()
		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_annoying_pjs=True)

	def tearDown(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

	def test_cloudflare_auto(self):
		page = self.wg.getpage("http://127.0.0.1:{}/cloudflare_under_attack_shit".format(self.mock_server_port))
		self.assertEqual(page, '<html><body>CF Redirected OK?</body></html>')

	def test_sucuri_auto(self):
		page = self.wg.getpage("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port))
		self.assertEqual(page, '<html><body>Sucuri Redirected OK?</body></html>')
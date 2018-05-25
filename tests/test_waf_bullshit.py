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


class TestPreemptiveWrapper(unittest.TestCase):
	def setUp(self):

		self.wg = WebRequest.WebGetRobust()
		self.wg.clearCookies()
		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_annoying_pjs=True)

		# Google sets some test cookies we can look at
		self.wg.getpage("https://www.google.com")

	def tearDown(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

	def test_preemptive_unwaf(self):
		page = self.wg.getpage("http://127.0.0.1:{}/sucuri_shit_3".format(self.mock_server_port))
		self.assertEqual(page, '<html><head><title>At target preemptive Sucuri page!</title></head><body>Preemptive waf circumvented OK (p3)?</body></html>')


	def test_preemptive_unwaf_skip(self):
		page = self.wg.getpage("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port))

		page = self.wg.getpage("http://127.0.0.1:{}/sucuri_shit_2".format(self.mock_server_port))
		self.assertEqual(page, '<html><head><title>At target preemptive Sucuri page!</title></head><body>Preemptive waf circumvented OK (p2)?</body></html>')


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
		self.assertEqual(page, '<html><head><title>At target CF page!</title></head><body>CF Redirected OK?</body></html>')

	def test_sucuri_auto(self):
		page = self.wg.getpage("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port))
		self.assertEqual(page, '<html><head><title>At target Sucuri page!</title></head><body>Sucuri Redirected OK?</body></html>')


	def test_cloudflare_selenium_pjs(self):
		stepped_through = self.wg.stepThroughJsWaf_selenium_pjs("http://127.0.0.1:{}/cloudflare_under_attack_shit".format(self.mock_server_port), titleNotContains='Just a moment...')
		self.assertEqual(stepped_through, True)

	def test_sucuri_selenium_pjs(self):
		stepped_through = self.wg.stepThroughJsWaf_selenium_pjs("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port), titleNotContains="You are being redirected...")
		self.assertEqual(stepped_through, True)


class TestSeleniumGarbageWafPokeThrough(unittest.TestCase):
	def setUp(self):

		self.wg = WebRequest.WebGetRobust()
		self.wg.clearCookies()
		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_selenium_garbage_chromium=True)

	def tearDown(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

	def test_cloudflare_selenium_chromium(self):
		stepped_through = self.wg.stepThroughJsWaf_selenium_chromium("http://127.0.0.1:{}/cloudflare_under_attack_shit".format(self.mock_server_port), titleNotContains='Just a moment...')
		self.assertEqual(stepped_through, True)

	def test_sucuri_selenium_chromium(self):
		stepped_through = self.wg.stepThroughJsWaf_selenium_chromium("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port), titleNotContains="You are being redirected...")
		self.assertEqual(stepped_through, True)


class TestChromiumPokeThrough(unittest.TestCase):
	def setUp(self):

		self.wg = WebRequest.WebGetRobust()
		self.wg.clearCookies()
		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_annoying_pjs=True)

	def tearDown(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

	def test_cloudflare_raw_chromium_1(self):
		stepped_through = self.wg.stepThroughJsWaf_bare_chromium("http://127.0.0.1:{}/cloudflare_under_attack_shit".format(self.mock_server_port), titleNotContains='Just a moment...')
		self.assertEqual(stepped_through, True)

	def test_cloudflare_raw_chromium_2(self):
		stepped_through = self.wg.stepThroughJsWaf_bare_chromium("http://127.0.0.1:{}/cloudflare_under_attack_shit".format(self.mock_server_port), titleContains='At target CF page!')
		self.assertEqual(stepped_through, True)

	def test_sucuri_raw_chromium_1(self):
		stepped_through = self.wg.stepThroughJsWaf_bare_chromium("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port), titleNotContains="You are being redirected...")
		self.assertEqual(stepped_through, True)

	def test_sucuri_raw_chromium_2(self):
		stepped_through = self.wg.stepThroughJsWaf_bare_chromium("http://127.0.0.1:{}/sucuri_shit".format(self.mock_server_port), titleContains="At target Sucuri page!")
		self.assertEqual(stepped_through, True)

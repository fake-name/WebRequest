import unittest
import socket
import json
import base64
import zlib
import gzip
import bs4
import ChromeController
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import WebRequest
from . import testing_server


class TestChromium(unittest.TestCase):
	def setUp(self):
		self.wg = WebRequest.WebGetRobust()

		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_chromium=True)

	def tearDown(self):
		self.mock_server.shutdown()

		# Hacky force-close of the chromium interface
		# self.wg.close_chromium()
		del self.wg

	def test_fetch_1(self):
		page = self.wg.getpage("http://localhost:{}".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_fetch_chromium_1(self):
		page, fname, mtype = self.wg.getItemChromium("http://localhost:{}".format(self.mock_server_port))

		self.assertEqual(fname, '')
		self.assertEqual(mtype, 'text/html')
		self.assertEqual(page, 'Root OK?')

	def test_fetch_chromium_2(self):
		page, fname, mtype = self.wg.getItemChromium("http://localhost:{}/raw-txt".format(self.mock_server_port))
		self.assertEqual(fname, 'raw-txt')
		self.assertEqual(mtype, 'text/plain')
		self.assertEqual(page, 'Root OK?')

	def test_fetch_chromium_3(self):
		page, fname, mtype = self.wg.getItemChromium("http://localhost:{}/binary_ctnt".format(self.mock_server_port))
		self.assertEqual(fname, 'binary_ctnt')
		self.assertEqual(mtype, 'image/jpeg')
		self.assertEqual(page, b"Binary!\x00\x01\x02\x03")

	def test_head_chromium_1(self):
		url_1 = "http://localhost:{}/raw-txt".format(self.mock_server_port)
		purl_1 = self.wg.getHeadChromium(url_1)
		self.assertEqual(purl_1, url_1)

	def test_head_chromium_2(self):
		url_2 = "http://localhost:{}/redirect/to-1".format(self.mock_server_port)
		purl_2 = self.wg.getHeadChromium("http://localhost:{}/redirect/from-1".format(self.mock_server_port))
		self.assertEqual(purl_2, url_2)

	def test_head_chromium_3(self):
		url_3 = "http://localhost:{}/redirect/bad-1".format(self.mock_server_port)
		purl_3 = self.wg.getHeadChromium("http://localhost:{}/redirect/bad-1".format(self.mock_server_port))
		self.assertEqual(purl_3, url_3)

	def test_head_title_chromium_1(self):
		pg_url = "http://localhost:{}/content/have-title".format(self.mock_server_port)
		retreived = self.wg.getHeadTitleChromium(pg_url)

		expect = {
						'url': pg_url,
						'title': 'I can haz title?',
		}
		self.assertEqual(retreived, expect)

	def test_head_title_chromium_2(self):
		pg_url = "http://localhost:{}/".format(self.mock_server_port)
		retreived = self.wg.getHeadTitleChromium(pg_url)

		expect = {
						# If no title is specified, chromium returns the server URL
						'url': pg_url,
						'title': 'localhost:{}'.format(self.mock_server_port),
		}
		self.assertEqual(retreived, expect)

	def test_head_title_chromium_3(self):
		pg_url = "http://localhost:{}/binary_ctnt".format(self.mock_server_port)
		retreived = self.wg.getHeadTitleChromium(pg_url)

		expect = {
						# If no title is specified, chromium returns the server URL
						'url': pg_url,
						'title': 'localhost:{}/binary_ctnt'.format(self.mock_server_port),
		}
		self.assertEqual(retreived, expect)

	def test_head_title_chromium_4(self):
		pg_url = "http://localhost:{}/content/no-title".format(self.mock_server_port)
		retreived = self.wg.getHeadTitleChromium(pg_url)

		expect = {
						'url': pg_url,
						'title': "localhost:{}/content/no-title".format(self.mock_server_port),
		}
		self.assertEqual(retreived, expect)


class TestChromiumPooled(unittest.TestCase):
	def setUp(self):
		self.wg = WebRequest.WebGetRobust()

		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg, is_chromium=True)

	def tearDown(self):
		self.mock_server.shutdown()

		# Hacky force-close of the chromium interface
		# self.wg.close_chromium()
		del self.wg

	def test_fetch_1(self):
		page = self.wg.getpage("http://localhost:{}/".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_tab_repeatability_1(self):
		tgturl = "http://localhost:{}/".format(self.mock_server_port)
		page, fname, mtype = self.wg.getItemChromium(tgturl)

		self.assertEqual(fname, '')
		self.assertEqual(mtype, 'text/html')
		self.assertEqual(page, 'Root OK?')


		print("Creating tab again!")
		with self.wg.chromiumContext(url=tgturl) as cr:
			at_url = cr.get_current_url()

			self.assertEqual(at_url, tgturl)

		print("3rd tab context!")
		with self.wg.chromiumContext(url=tgturl) as cr:
			title, cur_url = cr.get_page_url_title()
			print("title, cur_url", title, cur_url)
			self.assertEqual(cur_url, tgturl)


	def test_tab_flushing_1(self):
		tgturl = "http://localhost:{}/".format(self.mock_server_port)
		page, fname, mtype = self.wg.getItemChromium(tgturl)

		self.assertEqual(fname, '')
		self.assertEqual(mtype, 'text/html')
		self.assertEqual(page, 'Root OK?')

		for x in range(20):
			print("Creating tab again!")
			with self.wg.chromiumContext(url=tgturl, extra_tid=x) as cr:
				title, cur_url = cr.get_page_url_title()
				print("title, cur_url", title, cur_url)


		print("3rd tab context!")
		with self.wg.chromiumContext(url=tgturl) as cr:
			title, cur_url = cr.get_page_url_title()
			print("title, cur_url", title, cur_url)
			self.assertNotEqual(cur_url, tgturl)



	# def test_fetch_chromium_2(self):
	# 	page, fname, mtype = self.wg.getItemChromium("http://localhost:{}/raw-txt".format(self.mock_server_port))
	# 	self.assertEqual(fname, 'raw-txt')
	# 	self.assertEqual(mtype, 'text/html')  # I'm not properly retrieving the mimetype from chromium
	# 	self.assertEqual(page, 'Root OK?')

	# def test_fetch_chromium_3(self):
	# 	page, fname, mtype = self.wg.getItemChromium("http://localhost:{}/binary_ctnt".format(self.mock_server_port))
	# 	self.assertEqual(fname, 'binary_ctnt')
	# 	self.assertEqual(mtype, 'application/x-binary')
	# 	self.assertEqual(page, b"Binary!\x00\x01\x02\x03")

	# def test_head_chromium_1(self):
	# 	url_1 = "http://localhost:{}/raw-txt".format(self.mock_server_port)
	# 	purl_1 = self.wg.getHeadChromium(url_1)
	# 	self.assertEqual(purl_1, url_1)

	# def test_head_chromium_2(self):
	# 	url_2 = "http://localhost:{}/redirect/to-1".format(self.mock_server_port)
	# 	purl_2 = self.wg.getHeadChromium("http://localhost:{}/redirect/from-1".format(self.mock_server_port))
	# 	self.assertEqual(purl_2, url_2)

	# def test_head_chromium_3(self):
	# 	url_3 = "http://localhost:{}/redirect/bad-1".format(self.mock_server_port)
	# 	purl_3 = self.wg.getHeadChromium("http://localhost:{}/redirect/bad-1".format(self.mock_server_port))
	# 	self.assertEqual(purl_3, url_3)

	# def test_head_title_chromium_1(self):
	# 	pg_url = "http://localhost:{}/content/have-title".format(self.mock_server_port)
	# 	retreived = self.wg.getHeadTitleChromium(pg_url)
	# 	expect = {
	# 					'url': pg_url,
	# 					'title': 'I can haz title?',
	# 	}
	# 	self.assertEqual(retreived, expect)

	# def test_head_title_chromium_2(self):
	# 	pg_url = "http://localhost:{}/".format(self.mock_server_port)
	# 	retreived = self.wg.getHeadTitleChromium(pg_url)
	# 	expect = {
	# 					# If no title is specified, chromium returns the server URL
	# 					'url': pg_url,
	# 					'title': 'localhost:{}'.format(self.mock_server_port),
	# 	}
	# 	self.assertEqual(retreived, expect)

	# def test_head_title_chromium_3(self):
	# 	pg_url = "http://localhost:{}/binary_ctnt".format(self.mock_server_port)
	# 	retreived = self.wg.getHeadTitleChromium(pg_url)
	# 	expect = {
	# 					# If no title is specified, chromium returns the server URL
	# 					'url': pg_url,
	# 					'title': 'localhost:{}/binary_ctnt'.format(self.mock_server_port),
	# 	}
	# 	self.assertEqual(retreived, expect)

	# def test_head_title_chromium_4(self):
	# 	pg_url = "http://localhost:{}/content/no-title".format(self.mock_server_port)
	# 	retreived = self.wg.getHeadTitleChromium(pg_url)

	# 	expect = {
	# 					'url': pg_url,
	# 					'title': "localhost:{}/content/no-title".format(self.mock_server_port),
	# 	}
	# 	self.assertEqual(retreived, expect)

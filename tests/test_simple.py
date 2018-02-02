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


class TestPlainCreation(unittest.TestCase):
	def test_plain_instantiation_1(self):
		wg = WebRequest.WebGetRobust()
		self.assertTrue(wg is not None)

	def test_plain_instantiation_2(self):
		wg = WebRequest.WebGetRobust(cloudflare=True)
		self.assertTrue(wg is not None)

	def test_plain_instantiation_3(self):
		wg = WebRequest.WebGetRobust(use_socks=True)
		self.assertTrue(wg is not None)



class TestSimpleFetch(unittest.TestCase):
	def setUp(self):

		self.wg = WebRequest.WebGetRobust()

		# Configure mock server.
		self.mock_server_port, self.mock_server, self.mock_server_thread = testing_server.start_server(self, self.wg)

	def tearDown(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

	def test_fetch_1(self):
		page = self.wg.getpage("http://localhost:{}".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_fetch_decode_1(self):
		# text/html content should be decoded automatically.
		page = self.wg.getpage("http://localhost:{}/html-decode".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_fetch_soup_1(self):
		# text/html content should be decoded automatically.
		page = self.wg.getSoup("http://localhost:{}/html/real".format(self.mock_server_port))
		self.assertEqual(page, bs4.BeautifulSoup('<html><body>Root OK?</body></html>', 'lxml'))

	def test_fetch_soup_2(self):
		page = self.wg.getSoup("http://localhost:{}/html-decode".format(self.mock_server_port))
		self.assertEqual(page, bs4.BeautifulSoup('<html><body><p>Root OK?</p></body></html>', 'lxml'))

	def test_fetch_soup_3(self):
		# getSoup fails to fetch content that's not of content-type text/html
		with self.assertRaises(WebRequest.ContentTypeError):
			self.wg.getSoup("http://localhost:{}/binary_ctnt".format(self.mock_server_port))

	def test_fetch_decode_json(self):
		# text/html content should be decoded automatically.
		page = self.wg.getJson("http://localhost:{}/json/valid".format(self.mock_server_port))
		self.assertEqual(page, {'oh': 'hai'})

		page = self.wg.getJson("http://localhost:{}/json/no-coding".format(self.mock_server_port))
		self.assertEqual(page, {'oh': 'hai'})

		with self.assertRaises(json.decoder.JSONDecodeError):
			page = self.wg.getJson("http://localhost:{}/json/invalid".format(self.mock_server_port))

	def test_fetch_compressed(self):

		page = self.wg.getpage("http://localhost:{}/compressed/gzip".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

		page = self.wg.getpage("http://localhost:{}/compressed/deflate".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')

	def test_file_and_name_1(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename/path-only.txt".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'path-only.txt')

	def test_file_and_name_2(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename/content-disposition".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'lolercoaster.txt')

	def test_file_and_name_3(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename_mime/content-disposition-quotes-1".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'lolercoaster.html')

	def test_file_and_name_4(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename_mime/content-disposition-quotes-2".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'lolercoaster.html')

	def test_file_and_name_5(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename_mime/content-disposition-quotes-spaces-1".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'loler coaster.html')

	def test_file_and_name_6(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename_mime/content-disposition-quotes-spaces-2".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'loler coaster.html')

	def test_file_and_name_7(self):
		page, fn = self.wg.getFileAndName(requestedUrl="http://localhost:{}/filename_mime/content-disposition-quotes-spaces-2".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'loler coaster.html')
	def test_file_and_name_8(self):
		page, fn = self.wg.getFileAndName(requestedUrl="http://localhost:{}/filename_mime/content-disposition-quotes-spaces-2".format(self.mock_server_port), addlHeaders={"Referer" : 'http://www.example.org'})
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'loler coaster.html')
	def test_file_and_name_9(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename_mime/content-disposition-quotes-spaces-2".format(self.mock_server_port), addlHeaders={"Referer" : 'http://www.example.org'})
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'loler coaster.html')
	def test_file_and_name_10(self):
		page, fn = self.wg.getFileAndName("http://localhost:{}/filename/path-only-trailing-slash/".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, '')

	def test_file_name_mime_1(self):
		page, fn, mimet = self.wg.getFileNameMime(
						"http://localhost:{}/filename_mime/path-only.txt".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'path-only.txt')
		self.assertEqual(mimet, 'text/plain')

	def test_file_name_mime_2(self):
		page, fn, mimet = self.wg.getFileNameMime(
						"http://localhost:{}/filename_mime/content-disposition".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'lolercoaster.txt')
		self.assertEqual(mimet, 'text/plain')

	def test_file_name_mime_3(self):
		page, fn, mimet = self.wg.getFileNameMime(
						"http://localhost:{}/filename_mime/content-disposition-html-suffix".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, 'lolercoaster.html')
		self.assertEqual(mimet, 'text/plain')

	def test_file_name_mime_5(self):
		page, fn, mimet = self.wg.getFileNameMime(
						"http://localhost:{}/filename/path-only-trailing-slash/".format(self.mock_server_port))
		self.assertEqual(page, b'LOLWAT?')
		self.assertEqual(fn, '')
		self.assertEqual(mimet, 'text/plain')

	def test_file_name_mime_4(self):
		page, fn, mimet = self.wg.getFileNameMime(
						"http://localhost:{}/filename_mime/explicit-html-mime".format(self.mock_server_port))
		self.assertEqual(page, 'LOLWAT?')
		self.assertEqual(fn, 'lolercoaster.html')
		self.assertEqual(mimet, 'text/html')

	def test_get_head_1(self):
		inurl_1 = "http://localhost:{}".format(self.mock_server_port)
		nurl_1 = self.wg.getHead(inurl_1)
		self.assertEqual(inurl_1, nurl_1)

	def test_get_head_2(self):
		inurl_2 = "http://localhost:{}/filename_mime/content-disposition".format(self.mock_server_port)
		nurl_2 = self.wg.getHead(inurl_2)
		self.assertEqual(inurl_2, nurl_2)


	def test_redirect_handling_1(self):

		inurl_1 = "http://localhost:{}/redirect/from-1".format(self.mock_server_port)
		ctnt_1 = self.wg.getpage(inurl_1)
		self.assertEqual(ctnt_1, b"Redirect-To-1")

	def test_redirect_handling_2(self):
		inurl_2 = "http://localhost:{}/redirect/from-2".format(self.mock_server_port)
		ctnt_2 = self.wg.getpage(inurl_2)
		self.assertEqual(ctnt_2, b"Redirect-To-2")

	def test_redirect_handling_3(self):
		inurl_3 = "http://localhost:{}/redirect/from-1".format(self.mock_server_port)
		outurl_3 = "http://localhost:{}/redirect/to-1".format(self.mock_server_port)
		nurl_3 = self.wg.getHead(inurl_3)
		self.assertEqual(outurl_3, nurl_3)

	def test_redirect_handling_4(self):
		inurl_4 = "http://localhost:{}/redirect/from-2".format(self.mock_server_port)
		outurl_4 = "http://localhost:{}/redirect/to-2".format(self.mock_server_port)
		nurl_4 = self.wg.getHead(inurl_4)
		self.assertEqual(outurl_4, nurl_4)

	def test_redirect_handling_5(self):
		# This is a redirect without the actual redirect
		with self.assertRaises(WebRequest.FetchFailureError):
			inurl_5 = "http://localhost:{}/redirect/bad-1".format(self.mock_server_port)
			self.wg.getHead(inurl_5)

	def test_redirect_handling_6(self):
		# This is a infinitely recursive redirect.
		with self.assertRaises(WebRequest.FetchFailureError):
			inurl_6 = "http://localhost:{}/redirect/bad-2".format(self.mock_server_port)
			self.wg.getHead(inurl_6)

	def test_redirect_handling_7(self):
		# This is a infinitely recursive redirect.
		with self.assertRaises(WebRequest.FetchFailureError):
			inurl_6 = "http://localhost:{}/redirect/bad-3".format(self.mock_server_port)
			self.wg.getHead(inurl_6)

	def test_redirect_handling_8(self):
		inurl_7 = "http://localhost:{}/redirect/from-3".format(self.mock_server_port)
		# Assumes localhost seems to resolve to the listening address (here it's 0.0.0.0). Is this ever not true? IPv6?
		outurl_7 = "http://0.0.0.0:{}/".format(self.mock_server_port)
		nurl_7 = self.wg.getHead(inurl_7)
		self.assertEqual(outurl_7, nurl_7)


	# For the auth tests, we have to restart the test-server with the wg that's configured for password management
	def test_http_auth_1(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

		new_port_1 = testing_server.get_free_port()
		wg_1 = WebRequest.WebGetRobust(creds=[("localhost:{}".format(new_port_1), "lol", "wat")])
		# Configure mock server.
		new_port_1, self.mock_server, self.mock_server_thread = testing_server.start_server(self, wg_1, port_override=new_port_1)

		page = wg_1.getpage("http://localhost:{}/password/expect".format(new_port_1))
		self.assertEqual(page, b'Password Ok?')

	def test_http_auth_2(self):
		self.mock_server.shutdown()
		self.mock_server_thread.join()
		self.wg = None

		new_port_2 = testing_server.get_free_port()

		wg_2 = WebRequest.WebGetRobust(creds=[("localhost:{}".format(new_port_2), "lol", "nope")])
		# Configure mock server.
		new_port_2, self.mock_server, self.mock_server_thread = testing_server.start_server(self, wg_2, port_override=new_port_2)


		page = wg_2.getpage("http://localhost:{}/password/expect".format(new_port_2))
		self.assertEqual(page, b'Password Bad!')


	def test_get_item_1(self):
		inurl_1 = "http://localhost:{}".format(self.mock_server_port)
		content_1, fileN_1, mType_1 = self.wg.getItem(inurl_1)
		self.assertEqual(content_1, 'Root OK?')
		self.assertEqual(fileN_1, '')
		self.assertEqual(mType_1, "text/html")


	def test_get_item_2(self):
		inurl_2 = "http://localhost:{}/filename_mime/content-disposition".format(self.mock_server_port)
		content_2, fileN_2, mType_2 = self.wg.getItem(inurl_2)

		# Lack of an explicit mimetype makes this not get decoded
		self.assertEqual(content_2, b'LOLWAT?')
		self.assertEqual(fileN_2, 'lolercoaster.txt')
		self.assertEqual(mType_2, None)


	def test_get_item_3(self):
		inurl_3 = "http://localhost:{}/filename/path-only.txt".format(self.mock_server_port)
		content_3, fileN_3, mType_3 = self.wg.getItem(inurl_3)

		self.assertEqual(content_3, b'LOLWAT?')
		self.assertEqual(fileN_3, 'path-only.txt')
		self.assertEqual(mType_3, None)

	def test_get_cookies_1(self):
		inurl_1 = "http://localhost:{}/cookie_test".format(self.mock_server_port)
		inurl_2 = "http://localhost:{}/cookie_require".format(self.mock_server_port)

		self.wg.clearCookies()
		cookies = self.wg.getCookies()
		self.assertEqual(list(cookies), [])

		page_resp_nocook = self.wg.getpage(inurl_2)
		self.assertEqual(page_resp_nocook, '<html><body>Cookie is missing</body></html>')


		_ = self.wg.getpage(inurl_1)
		cookies = self.wg.getCookies()
		print(cookies)

		page_resp_cook = self.wg.getpage(inurl_2)
		self.assertEqual(page_resp_cook, '<html><body>Cookie forwarded properly!</body></html>')




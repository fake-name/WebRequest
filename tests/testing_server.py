import unittest
import socket
import json
import base64
import zlib
import gzip
import bs4
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
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
				self.end_headers()
				self.wfile.write(b"Root OK?")

			elif self.path == "/raw-txt":
				self.send_response(200)
				self.send_header('Content-type', "text/plain")
				self.end_headers()
				self.wfile.write(b"Root OK?")

			elif self.path == "/html-decode":
				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"Root OK?")

			elif self.path == "/html/real":
				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"<html><body>Root OK?</body></html>")

			elif self.path == "/compressed/deflate":
				self.send_response(200)
				self.send_header('Content-Encoding', 'deflate')
				self.send_header('Content-type', "text/html")
				self.end_headers()

				inb = b"Root OK?"
				cobj = zlib.compressobj(wbits=-zlib.MAX_WBITS)
				t1 = cobj.compress(inb) + cobj.flush()
				self.wfile.write(t1)

			elif self.path == "/compressed/gzip":
				self.send_response(200)
				self.send_header('Content-Encoding', 'gzip')
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(gzip.compress(b"Root OK?"))

			elif self.path == "/json/invalid":
				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"LOLWAT")

			elif self.path == "/json/valid":
				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b'{"oh" : "hai"}')

			elif self.path == "/json/no-coding":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b'{"oh" : "hai"}')

			elif self.path == "/filename/path-only.txt":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"LOLWAT?")
			elif self.path == "/filename/content-disposition":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename=lolercoaster.txt")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/path-only.txt":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/content-disposition":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename=lolercoaster.txt")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/content-disposition-html-suffix":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename=lolercoaster.html")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/explicit-html-mime":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename=lolercoaster.html")
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

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

			elif self.path == "/password/expect":

				self.send_response(200)
				self.end_headers()

				val = self.headers['Authorization']
				passval = val.split(" ")[-1]
				passstr = base64.b64decode(passval)

				if passstr == b'lol:wat':
					self.wfile.write(b"Password Ok?")
				else:
					self.wfile.write(b"Password Bad!")

			elif self.path == "/content/have-title":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"<html><head><title>I can haz title?</title></head><body>This page has a title!</body></html>")

			elif self.path == "/content/no-title":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"<html><head></head><body>This page has no title. Sadface.jpg</body></html>")

			elif self.path == "/binary_ctnt":
				self.send_response(200)
				self.send_header('Content-type', "image/jpeg")
				self.end_headers()
				self.wfile.write(b"Binary!\x00\x01\x02\x03")



	return MockServerRequestHandler

def get_free_port():
	s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
	s.bind(('localhost', 0))
	address, port = s.getsockname()
	s.close()
	return port


def start_server(assertion_class, from_wg):

	# Configure mock server.
	mock_server_port = get_free_port()
	mock_server = HTTPServer(('localhost', mock_server_port), capture_expected_headers(from_wg.browserHeaders, assertion_class, is_chromium=True))

	# Start running mock server in a separate thread.
	# Daemon threads automatically shut down when the main process exits.
	mock_server_thread = Thread(target=mock_server.serve_forever)
	mock_server_thread.setDaemon(True)
	mock_server_thread.start()

	return mock_server_port, mock_server, mock_server_thread



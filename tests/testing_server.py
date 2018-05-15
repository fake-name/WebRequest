
import traceback
import uuid
import socket
import logging
import os
import base64
import zlib
import gzip
import time
import datetime
from http import cookies
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from threading import Thread

import WebRequest


def capture_expected_headers(expected_headers, test_context, is_chromium=False, is_selenium_garbage_chromium=False, is_annoying_pjs=False, skip_header_checks=False):

	# print("Capturing expected headers:")
	# print(expected_headers)

	cookie_key = uuid.uuid4().hex
	log = logging.getLogger("Main.TestServer")
	class MockServerRequestHandler(BaseHTTPRequestHandler):

		def log_message(self, format, *args):
			return

		def validate_headers(self):
			for key, value in expected_headers:
				if (is_annoying_pjs or is_selenium_garbage_chromium or skip_header_checks) and key == 'Accept-Encoding':
					# So PhantomJS monkeys with accept-encoding headers
					# Just ignore that particular header, I guess.
					pass

				# Selenium is fucking retarded, and I can't override the user-agent
				# and other assorted parameters via their API at all.
				elif (is_selenium_garbage_chromium or skip_header_checks) and key == 'Accept-Language':
					pass
				elif (is_chromium or is_selenium_garbage_chromium or skip_header_checks) and key == 'Accept':
					pass
				elif not skip_header_checks:
					v1 = value.replace(" ", "")
					v2 = self.headers[key]
					if v2 is None:
						v2 = ""
					v2 = v2.replace(" ", "")
					test_context.assertEqual(v1, v2, msg="Mismatch in header parameter '{}' : '{}' -> '{}'".format(key, value, self.headers[key]))


		def _get_handler(self):

			self.validate_headers()

			if self.path == "/":
				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"Root OK?")


			elif self.path == "/favicon.ico":
				self.send_response(404)
				self.end_headers()

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

			elif self.path == "/filename/path-only-trailing-slash/":
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

			elif self.path == "/filename_mime/content-disposition-quotes-1":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename='lolercoaster.html'")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/content-disposition-quotes-2":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename=\'lolercoaster.html\'")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/content-disposition-quotes-spaces-1":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename='loler coaster.html'")
				self.end_headers()
				self.wfile.write(b"LOLWAT?")

			elif self.path == "/filename_mime/content-disposition-quotes-spaces-2":
				self.send_response(200)
				self.send_header('Content-Disposition', "filename=\"loler coaster.html\"")
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

			elif self.path == "/redirect/to-1":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"Redirect-To-1")

			elif self.path == "/redirect/from-2":
				self.send_response(302)
				self.send_header('uri', "to-2")
				self.end_headers()

			elif self.path == "/redirect/to-2":
				self.send_response(200)
				self.end_headers()
				self.wfile.write(b"Redirect-To-2")

			elif self.path == "/redirect/from-3":
				self.send_response(302)
				newurl = "http://{}:{}".format(self.server.server_address[0], self.server.server_address[1])
				self.send_header('uri', newurl)
				self.end_headers()

			elif self.path == "/password/expect":
				# print("Password")
				# print(self.headers)

				self.send_response(200)
				self.end_headers()

				if not 'Authorization' in self.headers:
					self.wfile.write(b"Password not sent!!")
					return

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

			elif self.path == "/binary_ctnt":
				self.send_response(200)
				self.send_header('Content-type', "image/jpeg")
				self.end_headers()
				self.wfile.write(b"Binary!\x00\x01\x02\x03")

			##################################################################################################################################
			# Cookie stuff
			##################################################################################################################################

			elif self.path == '/cookie_test':
				cook = cookies.SimpleCookie()
				cook['cookie_test_key'] = cookie_key
				cook['cookie_test_key']['path'] = "/"
				cook['cookie_test_key']['domain'] = ""
				expiration = datetime.datetime.now() + datetime.timedelta(days=30)
				cook['cookie_test_key']["expires"] = expiration.strftime("%a, %d-%b-%Y %H:%M:%S PST")
				self.send_response(200)
				self.send_header('Content-type', "text/html")

				self.send_header('Set-Cookie', cook['cookie_test_key'].OutputString())
				self.end_headers()
				self.wfile.write(b"<html><body>CF Cookie Test</body></html>")

			elif self.path == '/cookie_require':
				if self.headers.get_all('Cookie', failobj=[]):
					cook = self.headers.get_all('Cookie', failobj=[])[0]
					cook_key, cook_value = cook.split("=", 1)
					if cook_key == 'cookie_test_key' and cook_value == cookie_key:
						self.send_response(200)
						self.send_header('Content-type', "text/html")
						self.end_headers()
						self.wfile.write(b"<html><body>Cookie forwarded properly!</body></html>")
						return

				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(b"<html><body>Cookie is missing</body></html>")



			##################################################################################################################################
			# Sucuri validation
			##################################################################################################################################

			elif self.path == '/sucuri_shit':
				# print("Fetch for ", self.path)
				# print("Cookies:", self.headers.get_all('Cookie', failobj=[]))

				if self.headers.get_all('Cookie', failobj=[]):
					cook = self.headers.get_all('Cookie', failobj=[])[0]

					cook_key, cook_value = cook.split("=", 1)

					if cook_key == 'sucuri_cloudproxy_uuid_6293e0004' and cook_value == '04cbb56494ebedbcd19a61b2d728c478':
						# if cook['']
						self.send_response(200)
						self.send_header('Content-type', "text/html")
						self.end_headers()
						self.wfile.write(b"<html><head><title>At target Sucuri page!</title></head><body>Sucuri Redirected OK?</body></html>")

						return


				container_dir = os.path.dirname(__file__)
				fpath = os.path.join(container_dir, "waf_garbage", 'sucuri_garbage.html')
				with open(fpath, "rb") as fp:
					plain_contents = fp.read()

				self.send_response(200)
				self.send_header('Content-type', "text/html")
				self.end_headers()
				self.wfile.write(plain_contents)

			##################################################################################################################################
			# Cloudflare validation
			##################################################################################################################################

			elif self.path == '/cloudflare_under_attack_shit':
				if self.headers.get_all('Cookie', failobj=[]):
					cook = self.headers.get_all('Cookie', failobj=[])[0]

					cook_key, cook_value = cook.split("=", 1)

					if cook_key == 'cloudflare_validate_key' and cook_value == cookie_key:
						# if cook['']
						self.send_response(200)
						self.send_header('Content-type', "text/html")
						self.end_headers()
						self.wfile.write(b"<html><head><title>At target CF page!</title></head><body>CF Redirected OK?</body></html>")

						return

				container_dir = os.path.dirname(__file__)
				fpath = os.path.join(container_dir, "waf_garbage", 'cloudflare_bullshit.html')
				with open(fpath, "rb") as fp:
					plain_contents = fp.read()

				self.send_response(503)
				self.send_header('Content-type','text/html')
				self.end_headers()
				self.wfile.write(plain_contents)

			elif (self.path == '/cdn-cgi/l/chk_jschl?jschl_vc=b10392d4929902df66c5d69ff703fde7&pass=1516685611.828-z5pqL%2FrL34&jschl_answer=3161' or
				  self.path == '/cdn-cgi/l/chk_jschl?jschl_vc=b10392d4929902df66c5d69ff703fde7&pass=1516685611.828-z5pqL%2FrL34&jschl_answer=3160'):

				cook = cookies.SimpleCookie()
				cook['cloudflare_validate_key'] = cookie_key
				cook['cloudflare_validate_key']['path'] = "/"
				cook['cloudflare_validate_key']['domain'] = ""
				expiration = datetime.datetime.now() + datetime.timedelta(days=30)
				cook['cloudflare_validate_key']["expires"] = expiration.strftime("%a, %d-%b-%Y %H:%M:%S PST")
				self.send_response(200)
				self.send_header('Content-type', "text/html")

				self.send_header('Set-Cookie', cook['cloudflare_validate_key'].OutputString())
				self.end_headers()

				body = "<html><body>Setting cookies.<script>window.location.href='/cloudflare_under_attack_shit'</script></body></html>"
				self.wfile.write(body.encode("utf-8"))




			##################################################################################################################################
			# Handle requests for an unknown path
			##################################################################################################################################

			else:
				test_context.assertEqual(self.path, "This shouldn't happen!")



		def do_GET(self):
			# Process an HTTP GET request and return a response with an HTTP 200 status.
			log.info("Request for URL path: '%s'", self.path)
			# print("Headers: ", self.headers)
			# print("Cookie(s): ", self.headers.get_all('Cookie', failobj=[]))

			try:
				return self._get_handler()
			except Exception as e:
				log.error("Exception in handler!")
				for line in traceback.format_exc().split("\n"):
					log.error(line)
				raise e

	return MockServerRequestHandler

def get_free_port():
	s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
	s.bind(('localhost', 0))
	address, port = s.getsockname()
	s.close()
	return port


def start_server(assertion_class,
			from_wg,
			port_override                = None,
			is_chromium                  = None,
			is_selenium_garbage_chromium = False,
			is_annoying_pjs              = False,
			skip_header_checks           = False
		):

	# Configure mock server.
	if port_override:
		mock_server_port = port_override
	else:
		mock_server_port = get_free_port()

	captured_server = capture_expected_headers(from_wg.browserHeaders, assertion_class,
			is_chromium                  = is_chromium,
			is_selenium_garbage_chromium = is_selenium_garbage_chromium,
			is_annoying_pjs              = is_annoying_pjs,
			skip_header_checks           = skip_header_checks
		)
	mock_server = HTTPServer(('0.0.0.0', mock_server_port), captured_server)

	# Start running mock server in a separate thread.
	# Daemon threads automatically shut down when the main process exits.
	mock_server_thread = Thread(target=mock_server.serve_forever)
	mock_server_thread.setDaemon(True)
	mock_server_thread.start()

	return mock_server_port, mock_server, mock_server_thread



if __name__ == '__main__':

	wg = WebRequest.WebGetRobust()
	srv = start_server(None, wg, skip_header_checks=True)

	print("running server on port: ", srv)
	while 1:
		time.sleep(1)

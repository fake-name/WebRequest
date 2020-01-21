

import random
import logging
import threading

import time
import asyncio
import functools

from . import socks5
# import pproxy
# from . import pysoxy
# import pproxy.verbose

from . import PunchPort
from .. import Exceptions as exc


class ProxyLauncher(object):

	def __init__(self, remote_ips):
		self.log = logging.getLogger("Main.WebRequest.Captcha.ProxyLauncher")

		# Chose a random local port between 5000 and 60000
		# We avoid the absolute extents as a precaution
		self.listen_port = random.randint(5000, 60000)
		# self.listen_port = 12345
		assert isinstance(remote_ips, list), "Remote IPs must be a list (of IPs). Passed %s (%s)" % (type(remote_ips), remote_ips)
		self.remote_ips = remote_ips

		self._open_local_port(self.listen_port, self.remote_ips)

		self.prox = socks5.Socks5Server(
				port = self.listen_port
			)

		self.log.info("Launching Socks5 proxy listening on local port %s", self.listen_port)
		self.prox.run_in_thread()



		########################################################################
		## Pproxy 1.5.2
		# try:
		# 	self.loop = asyncio.get_event_loop()
		# except RuntimeError:
		# 	self.loop = asyncio.new_event_loop()
		# 	asyncio.set_event_loop(self.loop)


		# listen = pproxy.uri_compile('http+socks://*:{port}/'.format(port=port))

		# args = {
		# 		'httpget' : {},
		# 		'v'       : False,
		# 		'alive'   : 0,
		# 		'listen'  : listen,
		# 		'block'   : None,
		# 		'pac'     : None,
		# 		'sslfile' : None,
		# 		'gets'    : [],
		# 		'rserver' : []
		# 	}

		# servers = []
		# handler = functools.partial(functools.partial(pproxy.proxy_handler, **args), **vars(listen))

		# server = listen.server(handler)

		# eventLoop = self.loop.run_until_complete(server)
		# servers.append(eventLoop)


		# if servers:
		# 	try:
		# 		self.loop.run_forever()
		# 	except KeyboardInterrupt:
		# 		pass

		# for task in asyncio.Task.all_tasks():
		# 	task.cancel()
		# for server in servers:
		# 	server.close()
		# for server in servers:
		# 	self.loop.run_until_complete(server.wait_closed())
		# self.loop.close()

		########################################################################
		## Pproxy 2.2.0
		# server = pproxy.Server('http+socks5://0.0.0.0:{port}/'.format(port=port))
		# remotes = []
		# for ip in self.remote_ips:
		# 	remotes.append(pproxy.Connection('http+socks5://{ip}:{port}/'.format(ip=ip, port=port)))
		# args = dict( rserver = remotes,
		#              verbose = print )

		# handler = self.loop.run_until_complete(server.start_server(args))
		# try:
		# 	self.loop.run_forever()
		# except KeyboardInterrupt:
		# 	print('exit!')

		# handler.close()
		# self.loop.run_until_complete(handler.wait_closed())
		# self.loop.run_until_complete(self.loop.shutdown_asyncgens())
		# self.loop.close()


	def _open_local_port(self, port, listen_from_ips):
		self.log.info("Opening port on NAT device to forward port %s from remote IP %s.", port, listen_from_ips)
		self.hole_puncher = PunchPort.UpnpHolePunch()
		self.hole_puncher.open_port(listen_from_ips, port, port)


	def _close_local_port(self, port, listen_from_ips):
		self.log.info("Closing port on NAT device to forward port %s from remote IP %s.", port, listen_from_ips)
		self.hole_puncher.close_port(listen_from_ips, port)


	def stop(self):
		self.log.info("Telling proxy server to exit")
		self.prox.stop_server_thread()
		# self.log.info("Telling async event-loop to exit")
		# self.loop.call_soon_threadsafe(self.loop.stop)
		# self.log.info("Joining asyncio loop thread.")
		# self.proxy_process.join()

		# Close the port
		self._close_local_port(self.listen_port, self.remote_ips)

	def is_forwarded(self):
		'''
		If we're forwarded, we're not public
		'''
		return not self.hole_puncher.is_public()

	def get_wan_address(self):
		return "{}:{}".format(self.hole_puncher.get_wan_ip(), self.listen_port)

	def get_wan_ip(self):
		return "{}".format(self.hole_puncher.get_wan_ip())

	def get_wan_port(self):
		return "{}".format(self.listen_port)


def test():
	twocaptcha_ip = ['*']
	logging.basicConfig(level=logging.INFO)
	pl = ProxyLauncher(twocaptcha_ip)

	print("Pl:", pl)
	print("Wan IP:", pl.get_wan_address())
	try:
		for x in range(2000):
			print("Loop ", x)
			time.sleep(1)
	except KeyboardInterrupt:
		pass
	finally:


		pl.stop()

	pass

if __name__ == '__main__':
	test()






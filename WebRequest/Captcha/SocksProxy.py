

import random
import logging
import threading

import time
import asyncio
import functools


import pproxy
import pproxy.verbose



from . import PunchPort
from .. import Exceptions as exc


class ProxyLauncher(object):

	def __init__(self, remote_ip):
		self.log = logging.getLogger("Main.WebRequest.Captcha.ProxyLauncher")

		# Chose a random local port between 5000 and 60000
		# We avoid the absolute extents as a precaution
		self.listen_port = random.randint(5000, 60000)

		self.remote_ip = remote_ip

		self._open_local_port(self.listen_port, self.remote_ip)

		self.proxy_process = threading.Thread(target=self._launch_proxy, args=(self.listen_port, ))
		self.proxy_process.start()

	def _launch_proxy(self, port):
		self.log.info("Launching Socks5 proxy listening on local port %s", port)
		listen = pproxy.uri_compile('http+socks://:{port}/'.format(port=port))


		self.loop = asyncio.new_event_loop()
		# Make the current loop available to the libraries
		asyncio.set_event_loop(self.loop)

		args = {
				'httpget' : {},
				'v'       : False,
				'alive'   : 0,
				'listen'  : listen,
				'block'   : None,
				'pac'     : None,
				'sslfile' : None,
				'gets'    : [],
				'rserver' : []
			}

		servers = []
		handler = functools.partial(functools.partial(pproxy.proxy_handler, **args), **vars(listen))

		server = listen.server(handler)

		eventLoop = self.loop.run_until_complete(server)
		servers.append(eventLoop)


		if servers:
			try:
				self.loop.run_forever()
			except KeyboardInterrupt:
				pass

		for task in asyncio.Task.all_tasks():
			task.cancel()
		for server in servers:
			server.close()
		for server in servers:
			self.loop.run_until_complete(server.wait_closed())
		self.loop.close()

	def _open_local_port(self, port, listen_from_ip):
		self.log.info("Opening port on NAT device to forward port %s from remote IP %s.", port, listen_from_ip)
		self.hole_puncher = PunchPort.UpnpHolePunch()
		self.hole_puncher.open_port(listen_from_ip, port, port)


	def _close_local_port(self, port, listen_from_ip):
		self.log.info("Closing port on NAT device to forward port %s from remote IP %s.", port, listen_from_ip)
		self.hole_puncher.close_port(listen_from_ip, port)


	def stop(self):
		self.log.info("Telling async event-loop to exit")
		self.loop.call_soon_threadsafe(self.loop.stop)
		self.log.info("Joining asyncio loop thread.")
		self.proxy_process.join()

		# Close the port
		self._close_local_port(self.listen_port, self.remote_ip)

	def get_wan_address(self):
		return "{}:{}".format(self.hole_puncher.get_wan_ip(), self.listen_port)


def test():
	twocaptcha_ip = '138.201.188.166'
	logging.basicConfig(level=logging.INFO)
	pl = ProxyLauncher(twocaptcha_ip)

	print("Pl:", pl)
	print("Wan IP:", pl.get_wan_address())
	for x in range(20):
		print("Loop ", x)
		time.sleep(1)


	pl.stop()

	pass

if __name__ == '__main__':
	test()






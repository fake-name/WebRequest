
import logging
import struct
import socket
import upnpclient

import WebRequest.Exceptions as exc

def _is_private_ip(ip):
	"""
	Taken from https://stackoverflow.com/a/39656628/268006

	Check if the IP belongs to private network blocks.
	@param ip: IP address to verify.
	@return: boolean representing whether the IP belongs or not to
			 a private network block.
	"""
	networks = [
		"0.0.0.0/8",
		"10.0.0.0/8",
		"100.64.0.0/10",
		"127.0.0.0/8",
		"169.254.0.0/16",
		"172.16.0.0/12",
		"192.0.0.0/24",
		"192.0.2.0/24",
		"192.88.99.0/24",
		"192.168.0.0/16",
		"198.18.0.0/15",
		"198.51.100.0/24",
		"203.0.113.0/24",
		"240.0.0.0/4",
		"255.255.255.255/32",
		"224.0.0.0/4",
	]

	for network in networks:
		try:
			ipaddr = struct.unpack(">I", socket.inet_aton(ip))[0]

			netaddr, bits = network.split("/")

			network_low = struct.unpack(">I", socket.inet_aton(netaddr))[0]
			network_high = network_low | 1 << (32 - int(bits)) - 1

			if ipaddr <= network_high and ipaddr >= network_low:
				return True
		except Exception:
			continue

	return False


class UpnpHolePunch(object):
	def __init__(self):
		self.log = logging.getLogger("Main.WebRequest.Captcha.UPnP-Manager")

		self.gateway_device = None

		self.local_ip = self._get_local_ip()

		if not self.local_ip:
			raise exc.CouldNotDetermineLocalIp("Could not determine the local IP. Are you connected to the internet?")

		self.is_public = not _is_private_ip(self.local_ip)

		if self.is_public:
			self.log.info("You seem to have a public IP address. No need to forward a port via UPnP")
		else:
			self.log.info("Your local IP is %s, which appears to be private. Looking for a UPnP Gateway.", self.local_ip)

			self._init_upnp()

	def _init_upnp(self):
		devices = upnpclient.discover()
		self.log.info("Found %s UPnP devices on LAN", len(devices))

		for device in devices:
			try:
				_ = device.WANIPConn1
				self.gateway_device = device
				self.log.info("Found gateway device: %s", device)
			except Exception:
				pass

		if not self.gateway_device:
			raise exc.CouldNotFindUpnpGateway("No UPnP Gateway found. Found %s UPnP devices on LAN" % len(devices))


		self.log.info("Resolved WAN address: %s", self.get_wan_ip())

	def _get_local_ip(self):
		local_ip = None

		dummy_hostname, dummy_aliaslist, ipaddrlist = socket.gethostbyname_ex(socket.gethostname())
		for ip in ipaddrlist:
			if not ip.startswith("127."):
				local_ip = ip

		if not local_ip:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("8.8.8.8", 53))
			local_ip, dummy_port = s.getsockname()
			s.close()

		return local_ip

	def get_wan_ip(self):
		ret = self.gateway_device.WANIPConn1.GetExternalIPAddress()
		if not "NewExternalIPAddress" in ret:
			raise exc.CouldNotDetermineWanIp("No wan IP address found on gateway. What?")
		return ret["NewExternalIPAddress"]

	def open_port(self, remote_address, remote_port, local_port, duration=None):
		# Idiot check
		if not self.gateway_device:
			raise exc.CouldNotFindUpnpGateway("No UPnP Gateway found.")

		if duration is None:
			duration = 60 * 15

		self.gateway_device.WANIPConn1.AddPortMapping(
					NewRemoteHost             = remote_address,
					NewExternalPort           = remote_port,
					NewProtocol               = 'TCP',
					NewInternalPort           = local_port,
					NewInternalClient         = self.local_ip,
					NewEnabled                = '1',
					NewPortMappingDescription = 'WebRequest CaptchaSolver Hole Punching.',
					NewLeaseDuration          = duration
					)
		self.log.info("Forwarding from remote %s:%s to local %s:%s. Lease will expire in %s seconds.",
			remote_address, remote_port, self.local_ip, local_port, duration)



	def close_port(self, remote_address, remote_port):
		# Idiot check
		if not self.gateway_device:
			raise exc.CouldNotFindUpnpGateway("No UPnP Gateway found.")

		self.log.info("Closing forwarded port from remote %s:%s.",
			remote_address, remote_port)

		self.gateway_device.WANIPConn1.DeletePortMapping(
						NewRemoteHost             = remote_address,
						NewExternalPort           = remote_port,
						NewProtocol               = 'TCP',
					)


def test():
	logging.basicConfig(level=logging.INFO)
	puncher = UpnpHolePunch()
	print("Puncher:", puncher)
	print("Wan IP:", puncher.get_wan_ip())

if __name__ == '__main__':
	test()
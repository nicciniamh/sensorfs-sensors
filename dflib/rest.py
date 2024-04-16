import os
import sys
import requests
import subprocess
import pprint

def _ping(host='8.8.8.8'):
   try:
      subprocess.check_output(["ping", "-c", "1", host])
      return True
   except subprocess.CalledProcessError:
      return False

stats = {
	'sent': 0,
	'errors': 0
}

class RestClient(object):
	'''
	This is the improved RESTapi interface as an class.
	'''
	def __init__(self,**kwargs):
		'''
		'''
		self.server = None
		self.host = None
		self.sensor = None

		for k in ['server','host','sensor']:
			if not k in kwargs:
				m=f'{k} argument is missing. server, host and sensor must be supplied'
				raise ValueError (m)

		self.setup(**kwargs)

		if not self.server or not self.sensor or not self.host:
			raise ValueError('neither sever nor host specified')

	def setup(self,**kwargs):
		'''
		set new options in kwargs for server, host and sensor. Any or all
		may be specified.
		'''
		for k in ['server','host','sensor']:
			if k in kwargs:
				setattr(self,k,kwargs[k])

	def _detailedError(self,exception,url,response):
		"""
		build an error message and reutrn it. The exception and url are printed
		and the response object is pretty printed from the dict representation of the
		response object.
		"""
		error = ""
		error = error + f"There was an exception: {exception}\n"
		error = error + f"The URL attempted was: {url}\n"
		error = error + f"{pprint.pformat(response.__dict__)}\n"
		return error

	def _sendCommand(self,command):
		"""
		Send a formatted command to the server, return the response, or
		return None on error. detailedError is called on exceptions.
		command contains the url encoded command and parameters. These are sent
		to server on port 4242.
		"""
		if not _ping(self.server):
			stats['errors'] += 1
			return {'error': 'host unreachable'}
		headers = {'Accept': 'application/json'}
		url = f'http://{self.server}:4242/{command}'
		try:
			r = requests.get(url=url, headers=headers,timeout=10)
			stats['sent'] += 1
			js = r.json()
			if 'error' in js:
				stats['errors'] += 1
				return js
		except Exception as e:
			stats['errors'] += 1
			return {'error': e}
		return r.json()


	def read(self):
		"""
		get sensor data from host as json object
		"""
		return self._sendCommand(f'read?host={self.host}&sensor={self.sensor}')

	def write(self,data):
		"""
		write sensor data to host as json object
		"""
		return self._sendCommand(f'write?host={self.host}&sensor={self.sensor}&data={str(data)}')

	def list(self):
		"""
		get list of sensors on host
		"""
		return self._sendCommand(f'list?host={self.host}')

	def hosts(self):
		"""
		get a list of hosts the server knows about
		"""
		return self._sendCommand('hosts')

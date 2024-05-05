'''
Module to edit sensor definitons
'''
import os
import json
from dflib.debug import debug, set_debug
from dflib import rest

#set_debug(True)

class Sensor:
	def __init__(self,server,host,sensor):
		self.client = rest.RestClient(server=server, host=host, sensor=sensor)
		self.modinfo = ''
		self.description = ''
		self._name = sensor
		self.read()

	def read(self):
		data = self.client.read()
		if not 'error' in data:
			self.data  = data
			if 'modinfo' in data:
				self.modinfo = data['modinfo']
			if 'description' in data:
				self.description = data['description']
			return self.data
		return None

	def __call__(self):
		return self.read()

class SensorHost:
	def __init__(self,server,host):
		self.server = server
		self.host = host
		self.sensors = {}
		debug(self.server,self.host)
		sens = rest.RestClient(server=self.server, host=self.host,sensor=None).list()
		for sen in sens:
			debug(self.server,self.host,sen)
			self.sensors[sen] = Sensor(self.server,self.host,sen)
			
	def list(self):
		return self.sensors.keys()

class SensorInfo:
	'''
	retrieve sensor information in a nice little dict
	'''
	def __init__(self,server):
		'''
		server = SensorFS RestAPI server to retrieve data from
		'''
		self.server = server
		self.sensors = {}
		r = rest.RestClient(server=self.server,host='none',sensor='none')
		hlist = r.hosts()
		for host in hlist:
			self.sensors[host] = SensorHost(self.server,host)

	def sensor_hosts(self):
		'''
		return a list of hosts on which sensors reside
		'''
		return list(self.sensors.keys())
	
	def sensors_on_host(self,host):
		'''
		return a list of sensors for a host
		'''
		return list(self.sensors[host].list())

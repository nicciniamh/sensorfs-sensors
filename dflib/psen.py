import os
import sys
import json
import time


stats = {
	'reads': 0
}

class PsuedoSensor:
	'''
	Since the data collection is done by a daemon process, this class provides 
	the rquired sensor interface to read sensor data from a ramdisk. 
	'''
	def __init__(self,**kwargs):
		self.sensor = None
		self.host = None
		self.base_path = None
		for k,v in kwargs.items():
			setattr(self,k,v)

	def read(self):
		'''
		read data, allowing for race conditions on sensor files
		'''
		stats['reads'] += 1
		tries = 0
		dpath = os.path.join(self.base_path,f'{self.host}/{self.sensor}/{self.sensor}.json')
		data = None
		while not data:
			try:
				with open(dpath) as f:
					data = json.load(f)
			except json.decoder.JSONDecodeError:
				tries += 1
				data = None
				time.sleep(.3)
				if tries > 5:
					return None
		return data
			

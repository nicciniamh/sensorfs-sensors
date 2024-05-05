class SensorCapabilities:
	def __init__(self,sensor_name):
		self._dsym = '\xb0'
		self._cpu_info = {
			'readable':True,
			'writable': False,
			'units': {
				'usage': {'text': '%', 'digits': 1},
				'core0': {'text': '%', 'digits': 1},
				'core1': {'text': '%', 'digits': 1},
				'core2': {'text': '%', 'digits': 1},
				'core3': {'text': '%', 'digits': 1},
				'vmem': {'text': '%', 'digits': 1},
				'loadavg': {'text': '', 'digits': 2},
				'cputemp': {'text': f'\xB0 C', 'digits': 2},
				'boot_time': {'text': '', 'digits': 0}
			},
			'ranges': {
				'usage': (0,100),
				'core0': (0,100),
				'core1': (0,100),
				'core2': (0,100),
				'core3': (0,100),
				'vmem': (0,100),
				'loadavg': (0,5),
				'cputemp': (25,100),
				'boot_time': (0,1048576),
			}
		}
		self._temp_sensors = {
			'readable':True,
			'writable': False,
			'units': {
				'humidity': {'text': '%', 'digits': 1},
				'tempc': {'text': f'\xB0C', 'digits': 2},
				'temp': {'text': f'\xB0F', 'digits': 2},
			},
			"ranges": {
				'temp': (50,95),
				'tempc': (10,35),
				'humidity': (0,100)
			}
		}
		self._aggregate_sensors = {
			'readable':True,
			'writable': False,
			'units': {
				'humidity': {'text': '%', 'digits': 1},
				'tempc': {'text': f'\xB0C', 'digits': 2},
				'temp': {'text': f'\xB0F', 'digits': 2},
				'pressure': {'text': 'mbars'}
			},
			"ranges": {
				'temp': (50,95),
				'tempc': (10,35),
				'humidity': (0,100),
				'pressure': (950,1035)
			}
		}
		self._barometer_sensors = {
			'readable':True,
			'writable': False,
			'units': {
				'tempc': {'text': f'\xB0C', 	'digits': 2},
				'temp': {'text': f'\xB0F', 		'digits': 2},
				'pressure': {'text': 'mbars',	'digits': 2}
			},
			"ranges": {
				'temp': (50,95),
				'tempc': (10,35),
				'pressure': (950,1035)
			}
		}
		self._sen_caps = {
			'si7020': self._temp_sensors,
			'si7021': self._temp_sensors,
			'aht10': self._temp_sensors,
			'dht22': self._temp_sensors,
			'bmp280': self._barometer_sensors,
			'cpu_info': self._cpu_info,
			'cpu_usage': self._cpu_info,
			'aggregate': self._aggregate_sensors
		}
		if not sensor_name in self._sen_caps:
			raise AttributeError(f'{sensor_name} is not in capacilities')
		self.sensor_name = sensor_name
		self.cap = self._sen_caps[sensor_name]

	def get_cap(self):
		return self.cap

	def get_cap_name(self,name):
		if name in self.cap:
			return self.cap[name]
		else:
			raise AttributeError(f'{name} is not in capacilities')

	def get_cap_units(self, name):
		if not name in self.cap['units']:
			raise AttributeError(f'{name} is not in capacilities')
		return self.cap['units'][name]
	
	def get_sensor_keys(self):
		return list(self.cap['units'].keys())


if __name__ == "__main__":
	from pprint import pp
	c = SensorCapabilities('bmp280')
	d = c.get_cap()
	pp(d)

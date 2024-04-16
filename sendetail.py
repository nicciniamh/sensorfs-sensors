'''
This module is for the SenDetail windows opened when the detial window is opened. 
'''
import os
import sys
import time
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

sys.path.append(os.path.expanduser('~/lib'))
prog_dir = os.path.dirname(os.path.realpath(sys.argv[0])) 
sys.path.append(prog_dir)

from dflib import widgets, rest
from dflib.debug import debug

''' Colors for dark mode '''
dark_mode_colors = {
	'humdity': 		'cyan',
	'time': 		'yellow',
	'name':		 	'#AD00AD',
	'type': 		'goldenrod',
	'modinfo': 		'#ebba7a',
	'description': 	'#9aeb7a',
	'location': 	'#b8870b',
	'temp_green': 	'#00ff00',
	'temp_red': 	'#ff0000',
	'temp_blue': 	'#0000ff'
}
''' Colors for light mode  '''
light_mode_colors = {
	'humdity': 		'#008000',
	'time': 		'brown',
	'name': 		'darkblue',
	'type': 		'darkorange',
	'modinfo': 		'#800080',
	'description': 	'#034f91',
	'location': 	'#002000',
	'temp_green': 	'#004000',
	'temp_red': 	'#400000',
	'temp_blue': 	'#000040'
}

class PsuedoSensor:
	'''
	Since the data collection is done by a daemon process, this class provides 
	the rquired sensor interface to read sensor data from a ramdisk. 
	'''
	def __init__(self,**kwargs):
		self.sensor = None
		self.host = None
		self.base_path = '/Volumes/RamDisk/sensordata'
		for k,v in kwargs.items():
			setattr(self,k,v)

	def read(self):
		'''
		read data, allowing for race conditions on sensor files
		'''
		tries = 0
		dpath = os.path.join(self.base_path,f'{self.host}-{self.sensor}.json')
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
			
class SenDetail(Gtk.Window):
	'''
	This class implements the sensor detail window. 
	The specified sensor is read every config['poll_interval'] seconds.
	When the window is created it is positioned based on the position 
	parameter. Window movement is tracked and reported to the caller. 
	The keyword arguments for this class are:
		config = global configuration dict
		host - sensor host (for rest client)
		sensor_name - sensor name (for rest client)
		title - Window title
		position - initial window position
		callback - to be called when the window is closed 
		move_callback - to be called when the window is moved (for saving position)
	'''
	def __init__(self,*args,**kwargs):
		self.config = None
		self.host = None
		self.sensor_name = None
		self.title = None
		self.callback = None
		self.position = None
		self._macos = False
		self.move_callback = None
		self._initial_position_set = False
		self.iconified = False
		self._data_thread = None
		self._data_q = None
		self._command_q = None
		for k,v in kwargs.items():
			if k in ['config','host','sensor_name','title','callback','position','move_callback']:
				setattr(self,k,v)
			else:
				raise ValueError(f'Invalid keyword argument {k}')

		for p in ['config','host','sensor_name','title','callback','position']:
			if not getattr(self,p):
				raise AttributeError(p)

		if 'Darwin' in os.uname()[0]:
			self._macos = True

		if not 'poll_interval' in self.config:
			self.config['poll_interval'] = 300

		debug(self.sensor_name,'interval', self.config['poll_interval'])
		self.server = self.config['server']
		#self.sensor = rest.RestClient(server=self.server,sensor=self.sensor_name,host=self.host)
		self.sensor = PsuedoSensor(server=self.server,sensor=self.sensor_name,host=self.host)
		Gtk.Window.__init__(self, title=self.title)
		self.connect("delete-event", self.stopit)
		self.keepgoing = True
		self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.label = Gtk.Label()
		self.label.set_selectable(False)
		self.label.set_hexpand(True)
		self.vbox.pack_start(self.label,True,True,0)
		self.add(self.vbox)
		window_icon = GdkPixbuf.Pixbuf.new_from_file('icons/humidity.png')
		self.set_icon(window_icon)
		self.show_all()
		self.update()

	def change_sensor(self, title, host, sensor):
		'''
		Change title,host and sensor used.
		'''
		self.title = title
		self.set_title(title)
		self.host = host
		self.sensor_name = sensor
		self.server = self.config['server']
		self.sensor = rest.RestClient(server=self.server,sensor=self.sensor_name,host=self.host)
		debug(self.server,title, host, sensor)

	def do_iconify(self,*args):
		'''
		Hide a window if not hidden
		'''
		debug(f'is_iconified',self.iconified)
		if not self.iconified:
			self.iconified = True
			self.hide()

	def do_deiconify(self,*args):
		'''
		unhide a hidden window
		'''
		debug(f'is_iconified',self.iconified)
		if self.iconified:
			self.iconified = False
			self.show_all()

	def set_window_position(self):
		'''
		position the window on init
		'''
		debug(self.title,self.position)
		if self.position:
			self.move(*self.position)
		self.connect('configure-event',self.on_window_config)
		self._initial_position_set = True

	def _xyfixup(self,x,y):
		'''
		Window management on macos is a little weird. This fixes it
		'''
		if x + y != 0:
			yoffset = 28 if self._macos else 0
			y+=yoffset
			if x < 0:
				x=0
		return (x,y)

	def move(self,x,y):
		'''
		move the window
		'''
		return super().move(*self._xyfixup(x,y))

	def on_window_config(self,*args):
		'''
		when the window is moved this evet is called, in turn we callback to the
		caller for the caller to save
		'''
		if self.keepgoing:
			pos = tuple(self.get_position())
			if callable(self.move_callback):
				self.move_callback(self.title,pos)

	def stopit(self,*args):
		'''
		call this when terminating. If callback is defined call it with title
		'''
		debug(f'stopit; {self.title}')
		self.keepgoing = False
		if callable(self.callback):
			self.callback(self.title)
		self.destroy()

	def read_sensor(self):
		''' reas the sensor and return data unless there's an error in the data
		'''
		we = f'{self.sensor.host}::{self.sensor.sensor}'
		detail = self.sensor.read()
		if type(detail) is dict:
			if 'error' in detail:
				return None
		else:
			debug(we,"returned data is not dict",detail)
			return None
		return detail


	def update(self):
		'''
		This is out main worker.
		First we check for dark_mode and set css accordingly. 
		We read the sensor and if data is returned format it 
		based on keys and colors. Once complete set a new timeout 
		to do this all over again.
		'''
		if 'dark_mode' not in self.config:
			self.dark_mode = False
		self.dark_mode = self.config['dark_mode']
		if self.dark_mode:
			self.key_color = '#7f7f7f'
			self.keycolors = dark_mode_colors
			bgc = 'black'
		else:
			self.key_color = '#3f3f3f'
			self.keycolors = light_mode_colors
			bgc = 'white'

		css_data = '.sdetail {font-family: Ariel; font-size: 22px;  background-color: @bgc; padding: 15px; }'.replace('@bgc',bgc)

		widgets._widget_set_css(self.label, 'sdetail', css_data)
		key_color = self.key_color
		dark_mode = self.dark_mode
		detail = self.read_sensor()
		if detail and not 'error' in detail:
			detail['name'] = self.sensor_name
			s = ''
			for k,v in detail.items():
				if k == 'description' or k == 'modinfo':
					v = f'<i>{v}</i>'

				if k == 'time':
					v = time.strftime('%D %T',time.localtime(v))
				if k == 'boot_time':
					v = int(time.time()) - int(v)
					v = time.strftime('%D %T',time.localtime(v))
					v = ':'.join(v.split(':')[:-1])

				if k in self.keycolors:
					color = self.keycolors[k]
				else:
					color = key_color
				if k == 'loadavg':
					la = []
					for i in range(0,3):
						la.append('{:.2f}'.format(v[i]))
					v = ', '.join(la)

				if type(v) is float:
					if k  in ['high', 'low','temp','tempc']:
						if v < 60:
							color = self.keycolors['temp_blue']
						elif v >= 80:
							color = self.keycolors['temp_red']
						else:
							color = self.keycolors['temp_green']

					v = '{:.2f}'.format(v)
				s = s + f'<span foreground="{key_color}">{k}</span>: '
				s = s + f'<span foreground="{color}">{v}</span>\n'
			try:
				self.label.set_markup(s)
			except:
				debug(f'Markup error: {s}')
				self.keepgoing = False
				return

		if not self._initial_position_set:
			self.set_window_position()

		if self.keepgoing:
			interval = self.config['poll_interval']
			GLib.timeout_add(interval, self.update)

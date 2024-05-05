import argparse
import sys
import os
import json
import psutil
import gi
import time
import matplotlib.colors as mpcolors
import pprint

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

prog_dir = os.path.expanduser('~/sensors-gui')
sys.path.append(os.path.expanduser('~/lib'))
sys.path.append(prog_dir)
os.chdir(prog_dir)

import defaults
import chartconf
import boundlist
import sencaps
from dflib import widgets, rest, psen
from dflib.LiveChart import LiveChart
from dflib.theme import change_theme
from dflib.debug import debug, set_debug, dpprint
from sendetail import SenDetail
from about import AboutDialog
from config import SensorsConfig
from iconbox import IconWindow

def format_number(number, width, precision,fill=' '):
	width += (precision+1)
	s = f'{number:0.{precision}f}'
	return s
	#return s.rjust(width,fill)

def get_units_information(sen, key):
	debug(sen,key)
	try:
		sencap = sencaps.SensorCapabilities(sen)
		if sencap:
			cap =  sencap.get_cap_name('units')
			return cap,'sencap'
	except Exception as e:
		debug(f'Exception getting cap for {sen}:{key}: {e}')
		pass
	return {key: {'text': '',
		 	'digits': 4}},'generated'

class ChartWindow(Gtk.Window):
	def __init__(self, config, **kwargs):
		# your initialization code remains the same
		self.keepging = True
		self.reconfig_timer = False
		self.active = True
		self.iconified = False
		self._initialized = False
		self.interval = 1000
		self.config = config
		self.key = kwargs.get('key')
		self.name = kwargs.get('name')
		self.line_width = kwargs.get('line_width',2)
		self.background_color = kwargs.get('background_color','black')
		self.legend_color = kwargs.get('legend_color','white')
		self.line_color = kwargs.get('line_color','blue')
		self.data_path = kwargs.get('data_path')
		self.on_close = kwargs.get('on_close')
		self.window_icon = kwargs.get('window_icon',None)
		self.config_callback = kwargs.get('config_callback')
		self.chartdef_backup = None
		self.color_buttons = {}
		self.size = (0,0)
		self.update_timeout = None
		self.config_window = None
		self.units = None
		self.min_value = -1
		self.max_value = -1
		if not self.name:
			raise AttributeError('name must be supplied')

		if not self.key:
			raise AttributeError('key must be specified')

		if not self.name in self.config['sensors']:
			raise AttributeError('name must be a valid sensor entry')

		self.host = self.config['sensors'][self.name]['host']
		self.sen = self.config['sensors'][self.name]['sensor']
		if 'chart' in self.config['sensors'][self.name]:
			self.chart_obj = self.config['sensors'][self.name]['chart']
		else:
			self.chart_obj = defaults.chart

		self.sensor = psen.PsuedoSensor(
			base_path = self.data_path,
			server='Some Server',
			host=self.host,
			sensor=self.sen)

		self.sencap = sencaps.SensorCapabilities(self.sen).get_cap()
		self.kavail = list(self.sencap['units'].keys())

		Gtk.Window.__init__(self,title=self.name,icon=self.window_icon)
		self.connect('destroy',self.stopit)
		self.data = boundlist.BoundList(30)
		self.background_color = '#000000'
		self.legend_color = '#ffffff'
		self.line_color = '#0000ff'
		self.paused = False

		for k,v in self.chart_obj.items():
			setattr(self,k,v)

		if self.units:
			if not self.key in self.units:
				self.units = None
		if not self.units:
			self.chart_obj['units'] = self.sencap['units']
		self.units = self.chart_obj['units']

		if 'min_value' in self.chart_obj:
			self.min_value = self.chart_obj['min_value']
		else:
			self.min_value = self.sencap['ranges'][self.key][0]

		if 'max_value' in self.chart_obj:
			self.max_value = self.chart_obj['max_value']
		else:
			self.max_value = self.sencap['ranges'][self.key][1]

		self.chart_obj['min_value'] = self.min_value
		self.chart_obj['max_value'] = self.max_value

		self.chart = LiveChart(
			500,300,
			background_color=self.background_color,
			legend_color=self.legend_color,
			line_color=self.line_color,
			line_width=self.line_width,
			min_value=self.min_value,
			max_value=self.max_value,
			relative_scale=False)


		self.data = boundlist.BoundList(50)
		grid = Gtk.Grid()
		self.add(grid)

		style = '''.current { font-family: "Arial"; font-size: 16px; padding: 10px} '''

		# Create an expander with settings box
		tbitems = {
			"Clear chart Data": {"icon": 'edit-delete',				"callback": self.on_clear},
			"Pause chart":		{"icon": 'media-playback-pause',		"callback": self.on_pause},
			"Chart settings":	{"icon": 'emblem-system',			"callback": self.open_config},
		}
		self.toolbar = widgets.Toolbar(tbitems,icon_size=Gtk.IconSize.MENU)
		grid.attach(self.toolbar,0,0,1,1)
		debug('Set the controls for the heart of the sun')
		dpprint(self.units)
		# Create a box for the labels
		label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		self.vcap = Gtk.Label()
		self.vcap.set_markup(f'<span size="large">{self.key}, last reading</span>')
		self.vlabel = Gtk.Label(label="<span background='black' color='#00ff00'></span>", use_markup=True)
		self.vlabel.set_width_chars(10)
		self.vlabel.set_alignment(1.0, 0.5) 
		self.vcap.set_alignment(0.0,0.5)
		widgets._widget_set_css(self.vcap,'current',style)
		widgets._widget_set_css(self.vlabel,'current',style)

		self.rate = Gtk.Label()
		self.rate.set_markup(f'<span size="large">Read once per {int(self.interval/1000)} second(s)</span>')
		widgets._widget_set_css(self.rate,'current',style)
		label_box.pack_start(self.vcap, False, False, 0)
		label_box.pack_start(self.vlabel, False, False, 0)
		self.vunits = Gtk.Label(label=self.units[self.key]['text'])
		label_box.pack_start(self.vunits, False, False, 0)
		label_box.pack_start(self.rate, False, False, 0)
		grid.attach(label_box, 0, 1, 1, 1)

		# Attach the chart to the grid
		grid.attach(self.chart, 0, 2, 1, 2)

		# Set chart data and other configurations
		if 'chart' in self.config['sensors'][self.name]:
			cobj = self.config['sensors'][self.name]['chart']
			if 'pos' in cobj:
				self.pos = cobj['pos']
				debug(f"setting pos: {cobj['pos']}")
				self.move(*cobj['pos'])

		if self.interval <= 100:
			self.interval = 100;
		self.data.append(self.sensor.read()[self.key])
		self.chart.set_data(self.data)
		self.set_title_status()
		self.update()
		self.show_all()
		self._trigger()
		self.connect('destroy', self.stopit)
		self.connect('configure-event', self.on_configure)
		self.set_resizable(False)
		GLib.timeout_add(100, self._set_initialized)
		self.reconfig(self.key,self.chart_obj	)
		self.reset_timer()

	def on_pause(self,*args):
		if self.paused:
			self.reset_timer()
			self.paused = False
		else:
			self.stop_timer()
			self.paused = True
		self.set_title_status()
		self.update(False)

	def on_clear(self,*args):
		self.data = boundlist.BoundList(50)
		self.update(False)

	def reset_timer(self):
		ms = self.interval
		debug(ms)
		if ms < 100:
			ms = 100
		if self.update_timeout:
			GLib.source_remove(self.update_timeout)
		self.update_timeout = GLib.timeout_add(ms,self._trigger)
	
	def stop_timer(self):
		debug()
		if self.update_timeout:
			GLib.source_remove(self.update_timeout)
			self.update_timeout = None
			

	def _construct_cobj(self):
		cobj = {}
		cobj['background_color'] = self.background_color
		cobj['legend_color'] = self.legend_color
		cobj['line_color'] = self.line_color
		cobj['line_width'] = self.line_width
		cobj['interval'] = self.interval
		cobj['min_value'] = self.min_value
		cobj['max_value'] = self.max_value
		cobj['units'] = self.units
		cobj["key"] = self.key
		return cobj	

	def _resolve_cobj(self,cobj):
		self.background_color = cobj['background_color']
		self.legend_color = cobj['legend_color']
		self.line_color = cobj['line_color']
		self.line_width = cobj['line_width']
		self.interval = cobj['interval']
		self.min_value = cobj['min_value']
		self.max_value = cobj['max_value']
		self.units = cobj['units']
		self.key = cobj['key']
		return cobj
			
	def open_config(self,*args):
		if self.config_window:
			self.config_window.present()
			return
		self.stop_timer()
		self.config_window = chartconf.ChartConfig(
			self._construct_cobj(),
			on_complete=self.on_chart_config_complete,
			key=self.key,
			sensor_name = self.name,
			sensor_type = self.sen
		)
		self.config_window.move(*self.position())

	def reconfig(self, newkey, cobj):
		debug()
		self.chart_obj = self._resolve_cobj(cobj)
		self.chart.set_scale(self.min_value,self.max_value,False)
		self.chart.set_colors(
			line_color=self.line_color,
			legend_color=self.legend_color,
			background_color=self.background_color
			)
		self.chart.set_line_width(self.line_width)
		if newkey != self.key:
			self.data = boundlist.BoundList(50)
		self.key = newkey
		debug("Calling save config")
		self.cobj = cobj

	def on_chart_config_complete(self,action, name, newkey, cobj):
		del self.config_window
		self.config_window = None
		debug(f'name [{name}],newkey [{newkey}], action [{action}])')
		if action == 'ok':
			debug('saving values and setting variables')
			self.reconfig(newkey,cobj)
			self.save_config()		
		self.set_title_status()
		self.reset_timer()

	def _set_initialized(self):
		debug()
		self._initialized = True
		self.active = True
		self.save_config()
		return False

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

	def _xyfixup(self,x,y):
		'''
		Window management on macos is a little weird. This fixes it
		'''
		if x + y != 0:
			yoffset = 28 if os.uname()[0] == 'Darwin' else 0
			y+=yoffset
			if x < 0:
				x=0
		return (x,y)

	def xmove(self,x,y):
		'''
		move the window
		'''
		return super().move(x,y)
		#return super().move(*self._xyfixup(x,y))

	def set_title_status(self):
		self.rate.set_markup(f'Interval {int(self.interval/1000)}')
		if len(self.data):
			samples = f' - {len(self.data)} samples'
		else:
			samples = ''
		if self.paused:
			icon = 'media-playback-start'
			tooltip = 'Resume chart'
			paused = "(paused)"
		else:
			paused = ""
			icon = 'media-playback-pause'
			tooltip = 'Pause chart'
		self.toolbar.change_button_image('Pause chart',icon,tooltip)
		self.set_title(f'{self.name} - {self.key} {paused}{samples}')
		

	def position(self, new_position=None):
		if type(new_position) is tuple:
			self.move(*new_position)
		return tuple(self.get_window().get_position())

	def on_configure(self,widget,event):
		self.pos = self.position()
		self.save_config()

	def update(self, read_data=True):
		chart = self.config['sensors'][self.name]
		if not self.key:
			debug("No key set")
			return
		if read_data:
			sdata = self.sensor.read()
			if not sdata or 'error' in sdata:
				debug("error, sdata",sdata)
				return
			value = v = sdata[self.key]
			if not self.key in self.units:
				u  = ''
				p = 4
			else:
				p = self.units[self.key]['digits']
				u = self.units[self.key]['text']
			v = format_number(value,5,p)
			self.vlabel.set_text(v)
			self.vcap.set_text(f'Charted Value {self.key}')
			self.vunits.set_text(u)
			self.data.append(value)
		else:
			self.vlabel.set_text('waiting...')
			self.vunits.set_text('')
		self.set_title_status()
		self.chart.set_data(self.data)

	def _trigger(self):
		if self.reconfig_timer:
			self.reset_timer()
			return False
		if self.keepging:
			self.update()
			return True
		else:
			return False

	def stopit(self,*args):
		self.save_config()
		debug("bye")
		self.keepging = False
		if callable(self.on_close):
			self.on_close(self.name)
		self.destroy()

	def save_config(self):
		if not self._initialized:
			return
		if callable(self.config_callback):
			keys_to_save = [
				'active',
				'background_color',
				'key',
				'interval',
				'legend_color',
				'line_color',
				'line_width',
				'min_value',
				'max_value',
				'pos',
				'units',
			]
			cobj = {key: self.__dict__[key] for key in keys_to_save}
			debug("sending config data to app for save")
			self.config_callback(self.name,cobj)

if __name__ == "__main__":
	from dflib.theme import change_theme
	from dflib.debug import set_debug
	set_debug(True)
	if len(sys.argv) != 3:
		key = 'temp'
		name = 'Sensor - bmp280(1)'
	else:
		name = sys.argv[1]
		key = sys.argv[2]

	try:
		with open('sensors.json') as f:
			config = json.load(f)
	except:
		print("Can't read sensors.json",file=sys.stderr)
		sys.exit(1)
	
	change_theme(config['dark_mode'])

	if name in config['sensors']:
		cobj = config['sensors'][name]['chart']
		del cobj['keyranges']
		del cobj['units']
		debug("cobj")
		dpprint(cobj)
		win = ChartWindow(
			config,
			name=name,
			key=key,
			data_path='/Users/nicci/Network/sensor')
		win.connect('destroy',Gtk.main_quit)
		win.show_all()
		win.present()
		Gtk.main()
		#else:
		#	print(f'No chart defined for {name}',file=sys.stderr)
	else:
		print(f'No sensor defined for {name}',file=sys.stderr)

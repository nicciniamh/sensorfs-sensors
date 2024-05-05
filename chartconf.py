'''
This module handles the chart configuration. 
Usage is to create either:
	ChartConfigPane - to embed in a layout or toplevel
	ChartConfig - to create a window sublcass of gtk window and chartconfigpane

	Flow:
		WHen the object is created a callback is used to indicate ok or cancel 
		depending on the button pressed. the chart configuration data is passed 
		to the callback. In the sensor editor the editor uses that callback to 
		save all the values not just the chart config's values. 

		A key is the key into the data dict from sensor readings. These are the 
		values that are charted. This key is crucial for determining defaults.
		This should be stored in the config object (dict) used to represet the
		 data configured here.  

		Chart configuration object is a dictionary with things like chart colors,
		line with, position, whether they are active, charting parmaeters and
		display information such as units. 

		The chart confiuration object is what is passed back to the parent in 
		the callback which also indicates a new key if amy. Once the callback 
		is made, the window is destroyed if the configuration controls are in
		a window or a box.
'''
import sys
import os
import gi
import matplotlib.colors as mpcolors
import copy
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

prog_dir = os.path.expanduser('~/sensors-gui')
sys.path.append(os.path.expanduser('~/lib'))
sys.path.append(prog_dir)
os.chdir(prog_dir)

import sencaps
from dflib import widgets
from dflib.debug import debug, dpprint

class ChartConfigPane(Gtk.Box):
	'''
	Create a configuration dialog in a box. 
	This creates a Gtk.Box with all the controls needed and event management 
	to configure chart settings. This is embedded in the sensor editor
	Arguments:
		key: current key used to plot or default if not.
		on_complete: callback to hand off button clicked and new data
		sensor_type: type  of sensor (aht10, bmp280, etc.)
		sensor_name: name of the sensor as shown in the iconwindow.

	After this class is instantiated  the config_pane property is availble to be 
	embedded in layout or toplevel. 
	'''
	def __init__(self,cobj,**kwargs):
		self.key = None
		self.on_complete = None
		self.sensor_type = None
		self.sensor_name = None
		self.color_buttons = {}
		Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
		for k,v in kwargs.items():
			if k in ['key','on_complete','sensor_type', 'sensor_name']:
				setattr(self,k,v)
			else:
				raise AttributeError(f'{k} is not a valid keyword argument')
		if not self.sensor_type:
			raise AttributeError('sensor_type must be specified')

		if not self.sensor_name:
			raise AttributeError('sensor_name must be specified')

		if not self.on_complete:
			raise AttributeError('on_complete must be specified')

		if not callable(self.on_complete):
			raise AttributeError('on_complete must be callable')

		self.cobj = copy.deepcopy(cobj) # We'll work on a copy and hand it back.
		self.sencap = sencaps.SensorCapabilities(self.sensor_type).get_cap()
		debug("cobj",'key' in self.cobj)
		dpprint(self.cobj)
		if not self.key:
			if 'key' in self.cobj:
				self.key = self.cobj['key']
				debug(f"using key {self.key} from cobj")
		else:
			#self.key = list(self.sencap['units'].keys())[0]
			debug(f"using key {self.key} from init parameters")

	
		if not 'min_value' in self.cobj:
			debug('setting min from sencap')
			self.cobj['min_value'] = self.sencap.ranges[self.key][0]
		else:
			debug('setting min from cobj')
		
		if not 'max_value' in self.cobj:
			debug('setting max from sencap')
			self.cobj['max_value'] = self.sencap.ranges[self.key][1]
		else:
			debug('setting max from cobj')

		self.min_value = self.cobj['min_value']
		self.max_value = self.cobj['max_value']

		if not 'units' in self.cobj:
			debug("using units from sencap")
			self.cobj['units'] = copy.deepcopy(self.sencap['units'])
		else:
			debug("using units from cobj")

		self.kavail = list(self.sencap['ranges'].keys())
		self.config_pane = self.get_config_box()

		self.scale.set_value(self.cobj['line_width'])  # Set the initial value
		self.keysel.set_value(self.key)
		self.units_entry.set_text(self.cobj['units'][self.key]['text'])
		GLib.timeout_add(100,self.set_range_and_units,False)
		self.set_range_and_units()

	def reconfigure(self,sendev,corb):
		'''
		reconfigure the pane by taking a new sensor in sendev and a new chart object
		'''
		self.sensor_type = sendev
		self.corb = copy.deepcopy(corb)
		self.sencap = sencaps.SensorCapabilities(sendev).get_cap()
		keys = list(self.sencap['units'].keys())
		if not self.key or not self.key in keys:
			self.key = keys[0]

		self.units = self.cobj['units'] = self.sencap['units']
		
		self.keysel.set_value(self.key,keys)
		self.min_value = self.cobj['min_value'] = self.sencap['ranges'][self.key][0]
		self.max_value = self.cobj['max_value'] = self.sencap['ranges'][self.key][1]

		debug('min/max',self.min_value,self.max_value)
		self.kavail = keys
		self.scale.set_value(self.cobj['line_width'])  # Set the initial value
		self.units_entry.set_text(self.cobj['units'][self.key]['text'])
		
		GLib.timeout_add(100,self.set_range_and_units,False)

	def set_range_and_units(self,rc=True):
		'''
		update the range, units and precision controls with new values. 
		'''
		debug()
		if not 'units' in self.cobj or not self.key in self.cobj['units']:
			debug('using default units')
			self.cobj['units'] = copy.deepcopy(self.sencap['units'])
		debug('setting m/x:',self.min_value,self.max_value)
		self.min_entry.set_text(f'{self.min_value}')
		self.max_entry.set_text(f'{self.max_value}')
		self.min_entry.show()
		self.max_entry.show()
		try:
			self.units_entry.set_text(self.cobj['units'][self.key]['text'])
			self.udigits.set_value(self.cobj['units'][self.key]['digits'])
		except:
			debug(f'wtf',self.key, self.cobj['units'])
		return rc

	def get_config_box(self):
		'''
		this is where we set up all the controls with the chart parrameters based 
		on current values.
		'''
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		ibox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ibox.pack_start(Gtk.Label(label='Update interval'),True,True,0)
		if not 'interval' in self.cobj:
			interval = 1000
		else:
			interval = self.cobj['interval']
		self.time_entry = widgets.TimeEntry(seconds=interval/1000.0)
		self.time_entry.set_tooltip_text('Select the interval for updating the chart')
		ibox.pack_start(self.time_entry,True,True,0)
		rbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		rbox.pack_start(Gtk.Label(label='Range'),True,True,0)
		self.range_set = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		self.range_set.pack_start(Gtk.Label(label='Min'),True,True,0)
		self.min_entry = Gtk.Entry()
		self.min_entry.set_tooltip_text('minimum value to  show on chart')
		self.range_set.pack_start(self.min_entry,True,True,0)
		self.range_set.pack_start(Gtk.Label(label='Max'),True,True,0)
		self.max_entry = Gtk.Entry()
		self.max_entry.set_tooltip_text('maximum value to  show on chart')
		self.range_set.pack_start(self.max_entry,True,True,0)

		rbox.pack_start(self.range_set,True,True,0)
		cbox_outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		cbox_outer.pack_start(Gtk.Label(label='Colors'),True,True,0)
		cbox_outer.pack_start(
			self._create_color_entry(self.cobj['background_color'],'Area','background_color'),True,True,0
		)
		cbox_outer.pack_start(
			self._create_color_entry(self.cobj['legend_color'],'Legend','legend_color'),True,True,0
		)
		cbox_outer.pack_start(
			self._create_color_entry(self.cobj['line_color'],'Line','line_color'),True,True,0
		)
		scbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		adjustment = Gtk.Adjustment(
			value = self.cobj['line_width'],
			lower = 1, 
			upper = 10,
			step_increment = 1,
			page_increment = 1,
			page_size = 0)
		self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
		self.scale.set_digits(0)
		self.scale.set_range(1, 10)  # Set the range of the scale
		self.scale.set_size_request(50, -1)  # Set the width of the scale
		self.scale.set_tooltip_text('slide to change size of chart lines')
		scbox.pack_start(Gtk.Label(label='Line Width'),True,True,0)
		scbox.pack_start(self.scale,True,True,0)
		rbox.pack_start(scbox,True,True,0)
		box.pack_start(ibox,True,True,0)
		box.pack_start(rbox,True,True,0)
		box.pack_start(cbox_outer,True,True,0)
		bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ok_button = Gtk.Button(label='Ok')
		ok_button.connect('clicked',self.on_ok_cancel_clicked,'ok')
		cancel_button = Gtk.Button(label='Cancel')
		cancel_button.connect('clicked',self.on_ok_cancel_clicked,'cancel')
		bbox.pack_start(Gtk.Label(label=' '),True,True,0)
		bbox.pack_start(ok_button,True,True,0)
		bbox.pack_start(cancel_button,True,True,0)
		self.keysel = widgets.SimpleCombo(self.kavail,on_change=self.on_key_select)
		#self.keysel = widgets.StringSpinButton(self.kavail,self.on_key_select)
		self.keysel.set_tooltip_text('Select item to chart')
		keybox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		keybox.pack_start(Gtk.Label(label='Value to chart'),True,True,0)
		keybox.pack_start(self.keysel,True,True,0)
		ubox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ubox.pack_start(Gtk.Label(label='Units'),True,True,0)
		self.units_entry = Gtk.Entry()
		ubox.pack_start(self.units_entry,True,True,0)
		digits = self.cobj['units'][self.key]['digits']
		adj = Gtk.Adjustment(value=digits, lower=0, upper=8,step_increment=1,page_increment=1)
		self.udigits = Gtk.SpinButton(adjustment=adj)
		ubox.pack_start(Gtk.Label(label='Digits'),True,True,0)
		ubox.pack_start(self.udigits,True,True,0)
		box.pack_start(keybox,True,True,0)
		box.pack_start(ubox,True,True,0)
		box.pack_start(bbox,True,True,0)
		return box

	def on_key_select(self,key):
		'''
		when a new key is used we have to adjust the ranges, so we get them 
		from sencap. This effectively nukes the previous range, digits and precision. 
		*sigh*
		'''
		debug(key)
		self.key = self.cobj['key'] = key
		self.min_value = self.cobj['min_value'] = self.sencap['ranges'][self.key][0]
		self.max_value = self.cobj['max_value'] = self.sencap['ranges'][self.key][1]
		self.set_range_and_units()


	def on_units_change(self,*args):
		'''
		When the units value changes, simply update the parameters
		'''
		self.units[self.key]['text'] = self.units_entry.get_text()
		self.units[self.key]['digits'] = self.udigits.get_value_as_int()
		self.set_range_and_units()
		dpprint(self.units)

	def on_ok_cancel_clicked(self,widget,action):
		'''
		This handles the ok and cancel button actions. We attached action
		to the event parameters. if Ok is pressed the current values are stored 
		in a chart object (dict)
		if the on_complete callback is defined the new object and action 
		are sent to the parent. 
		'''
		if action == 'ok':
			self.cobj['interval'] = int(self.time_entry.get_value())*1000
			debug(f"new interval is {self.cobj['interval']}")
			ustr = self.units_entry.get_text()
			udig = self.udigits.get_value_as_int()
			try:
				mv = float(self.min_entry.get_text())
				xv = float(self.max_entry.get_text())
			except:
				widgets.ErrorDialog('Error','Range values need to be numbers',None)
				return
			debug(f'mv/xv',mv,xv)
			self.cobj['background_color'] = self.color_buttons['Area'].get_color_value()
			self.cobj['line_color'] = self.color_buttons['Line'].get_color_value()
			self.cobj['legend_color'] = self.color_buttons['Legend'].get_color_value()
			self.cobj['line_width'] = self.scale.get_value()
			self.key = self.cobj['key'] = self.keysel.get_text()
			self.cobj['units'][self.key]['text'] = ustr
			self.cobj['units'][self.key]['digits'] = udig
			self.cobj['min_value'] = mv
			self.cobj['max_value'] = xv

		self.on_complete(action,self.sensor_name, self.key, self.cobj)
		#
		# If this is subclassed by ChartConfig there will be a window we need to 
		# destroy
  		#
		if isinstance(self, Gtk.Window):
			self.destroy()

	def _create_color_entry(self,color,text,tag):
		'''
		helper to generate the color entry widgets
		'''
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		label = Gtk.Label(label=text)
		button = ColorButton(color,None,None)
		self.color_buttons[text] = button
		box.pack_start(label,True,True,0)
		box.pack_start(button,True,True,0)
		return box

class ColorButton(Gtk.ColorButton):
	'''
	A nice clean interface for a colorbutton
	'''
	def __init__(self,color,cb_color_set,tag):
		self.cb_color_set = cb_color_set
		self.tag = tag
		self.hex = color
		Gtk.ColorButton.__init__(self)
		colors = list(mpcolors.hex2color(color))
		color = Gdk.RGBA(*colors,1.0)
		debug(self.hex,colors,color)
		self.set_rgba(color)
		self.set_size_request(64,64)
		self.set_tooltip_text('Select color')
		self.connect('color-set',self.on_color_set)

	def get_color_value(self):
		'''
		take the rgb values and convert to hex string`
		'''
		color = self.get_rgba()
		red = int(color.red * 255)
		green = int(color.green * 255)
		blue = int(color.blue * 255)
		return f'#{red:02x}{green:02x}{blue:02x}'

	def on_color_set(self,widget):
		'''
		activate callback when color is selected
		'''
		hexstr = self.get_color_value()
		if callable(self.cb_color_set):
			self.cb_color_set(hexstr,self.tag)

class ChartConfig(Gtk.Window, ChartConfigPane):
	'''
	This creates a Gtk.Window with all the controls needed and event
	management to configure chart settings. This is embedded in the 
	sensor editor
	Arguments:
		key: current key used to plot or default if not.
		on_complete: callback to hand off button clicked and new data
		sensor_type: type  of sensor (aht10, bmp280, etc.)
		sensor_name: name of the sensor as shown in the iconwindow.

	After this class is instantiated an object with all the properties
	of Gtk.Window and ChartConfigPane are available.
	'''
	def __init__(self,cobj, **kwargs):
		for k,v in kwargs.items():
			if k in ['key','on_complete','sensor_type', 'sensor_name']:
				setattr(self,k,v)
			else:
				raise AttributeError(f'{k} is not a valid keyword argument')
		if not self.sensor_type:
			raise AttributeError('sensor_type must be specified')

		if not self.sensor_name:
			raise AttributeError('sensor_name must be specified')

		Gtk.Window.__init__(self,title=f'Chart Settings for {self.sensor_name}')
		ChartConfigPane.__init__(self,cobj,**kwargs)
		self.add(self.config_pane)
		self.show_all()

if __name__ == "__main__":
	import json
	from dflib.theme import change_theme
	from dflib.debug import set_debug

	def config_complete(action,key,cobj):
		debug(action)
		dpprint(cobj)

	set_debug(True)
	change_theme(True)
	with open('sensors.json') as f:
		cobj = json.load(f)
	stype = 'aht10'
	name = 'Sensor - aht(1)'
	cobj = cobj['sensors'][name]['chart']
	win = ChartConfig(cobj,
		key='temp', 
		sensor_type=stype, 
		sensor_name=name,
		on_complete=config_complete)

	win.connect('destroy',Gtk.main_quit)
	Gtk.main()
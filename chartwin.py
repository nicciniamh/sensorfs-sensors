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

prog_dir = os.path.expanduser('/Users/nicci/sensors-gui')
sys.path.append(os.path.expanduser('/Users/nicci/lib'))
sys.path.append(prog_dir)
os.chdir(prog_dir)

import boundlist
from dflib import widgets, rest, psen
from dflib.LiveChart import LiveChart
from dflib.theme import change_theme
from dflib.debug import debug, set_debug, dpprint
import sensoredit
from sendetail import SenDetail
from about import AboutDialog
from config import SensorsConfig
from iconbox import IconWindow

class ColorButton(Gtk.ColorButton):
	def __init__(self,color,cb_color_set,tag):
		self.cb_color_set = cb_color_set
		self.tag = tag
		self.hex = color
		Gtk.ColorButton.__init__(self)
		colors = list(mpcolors.hex2color(color))
		color = Gdk.RGBA(*colors,1.0)
		debug(self.hex,colors,color)
		self.set_rgba(color)
		self.connect('color-set',self.on_color_set)
		self.set_size_request(64,64)
		self.set_tooltip_text('Select color')

	def get_color_value(self):
		color = self.get_rgba()
		red = int(color.red * 255)
		green = int(color.green * 255)
		blue = int(color.blue * 255)
		return f'#{red:02x}{green:02x}{blue:02x}'

	def on_color_set(self,widget):
		hexstr = self.get_color_value()
		if callable(self.cb_color_set):
			self.cb_color_set(hexstr,self.tag)

class ChartWindow(Gtk.Window):
	def __init__(self, config, **kwargs):
		# your initialization code remains the same
		self.keepging = True
		self.keyranges = {
			'tempc': (10,35),
			'temp': (50,95),
			'humidity': (30,100),
			'pressure': (950,1030),
			'core0': (0,100),
			'core1': (0,100),
			'core2': (0,100),
			'core3': (0,100),
			'core4': (0,100),
			'core5': (0,100),
			'core6': (0,100),
			'core7': (0,100),
			'cputemp': (0,100),
			'usage': (0,100),
			'vmem': (0,100)
		}
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
		self.min_value = kwargs.get('min_value',self.keyranges[self.key][0])
		self.max_value = kwargs.get('min_value',self.keyranges[self.key][1])
		self.data_path = kwargs.get('data_path')
		self.on_close = kwargs.get('on_close')
		self.chartdef_backup = None
		self.color_buttons = {}
		self.size = (0,0)
		if not self.name:
			raise AttributeError('name must be supplied')

		if not self.key:
			raise AttributeError('key must be specified')

		if not self.name in self.config['sensors']:
			raise AttributeError('name must be a valid sensor entry')

		host = self.config['sensors'][self.name]['host']
		sen = self.config['sensors'][self.name]['sensor']
		if not 'chart' in self.config['sensors'][self.name]:
			chart_obj = {
				'size': 			(0,0),
				'pos': 				(0,0),
				'keyranges':	 	self.keyranges,
				'background_color':	'#000000',
				'legend_color': 	'#A0A0A0',
				'line_color':		'#0000ff',
				'min_value':		self.keyranges[self.key][0],
				'max_value': 		self.keyranges[self.key][1],
			}
			debug(f'No chart in {self.name} creating new object:')
			dpprint(chart_obj)
			self.config['sensors'][self.name]['chart'] = chart_obj
		self.sensor = psen.PsuedoSensor(
			base_path = self.data_path,
			server = self.config['server'],
			host=host,
			sensor=sen)
		#self.kavail = []
		sdata = self.sensor.read()
		self.kavail = [ k for k in sdata.keys() if k not in ['description','loadavg','modinfo','name','time','boot_time']]
		Gtk.Window.__init__(self,title=self.name)
		self.connect('destroy',self.stopit)
		self.data = boundlist.BoundList(50)
		self.background_color = '#000000'
		self.legend_color = '#ffffff'
		self.line_color = '#0000ff'
		if 'chart' in self.config['sensors'][self.name]:
			for k,v in self.config['sensors'][self.name]['chart'].items():
				#debug(f'{self.name}::{k} = {v}')
				setattr(self,k,v)
		else:
			debug("no chart in",self.config['sensors'][self.name])
		self.chart = LiveChart(
			500,300,
			background_color=self.background_color,
			legend_color=self.legend_color,
			line_color=self.line_color,
			line_width=self.line_width,
			min_value=self.min_value,
			max_value=self.max_value,
			relative_scale=False)


		self.connect('destroy', self.stopit)
		self.data = boundlist.BoundList(50)
		#self.background_color = '#000000'
		#self.legend_color = '#ffffff'
		#self.line_color = '#0000ff'
		# Create a grid layout container
		grid = Gtk.Grid()
		self.add(grid)

		style = '''.current { font-family: "Arial"; font-size: 16px; padding: 10px} '''

		# Create an expander with settings box
		self.expander = Gtk.Expander(label="Chart Settings")
		self.expander.connect("notify::expanded", self.on_expander_changed)
		elabel = Gtk.Label()
		elabel.set_markup('Chart Settings')
		widgets._widget_set_css(elabel,'current',style)
		self.expander.set_resize_toplevel(True)
		cbox = self.get_config_box()
		self.expander.add(cbox)
		grid.attach(self.expander, 0, 0, 1, 1)

		# Create a box for the labels
		label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		cap = Gtk.Label()
		cap.set_markup('<span size="large">Last Reading</span>')
		self.vlabel = Gtk.Label(label="<span background='black' color='#00ff00'></span>", use_markup=True)
		widgets._widget_set_css(cap,'current',style)
		widgets._widget_set_css(self.vlabel,'current',style)

		label_box.pack_start(cap, False, False, 0)
		label_box.pack_start(self.vlabel, False, False, 0)
		grid.attach(label_box, 0, 1, 1, 1)

		# Attach the chart to the grid
		grid.attach(self.chart, 0, 2, 1, 2)

		# Set chart data and other configurations
		if 'chart' in self.config['sensors'][self.name]:
			cobj = self.config['sensors'][self.name]['chart']
			#if 'size' in cobj:
			#	self.size = cobj['size']
			#	debug(f"setting size: {cobj['size']}")
			#	#self.resize(*cobj['size'])
			if 'pos' in cobj:
				self.pos = cobj['pos']
				debug(f"setting pos: {cobj['pos']}")
				self.move(*cobj['pos'])

		self.data.append(self.sensor.read()[self.key])
		self.chart.set_data(self.data)
		self.set_title(f'{self.name} - {self.key}')
		self.update()
		self.show_all()
		self._trigger()
		self.connect('configure-event', self.on_configure)
		self.set_resizable(False)
		self._initialized = True

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

	def move(self,x,y):
		'''
		move the window
		'''
		return super().move(*self._xyfixup(x,y))


	def get_config_box(self):
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		ibox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ibox.pack_start(Gtk.Label(label='Update (ms)'),True,True,0)
		button = Gtk.SpinButton.new_with_range(500,36000,500)
		button.set_tooltip_text('Select the interval for updating the chart')
		button.set_value(self.interval)
		button.connect('value-changed',self.on_interval_change)
		button.connect('changed',self.on_interval_change)
		ibox.pack_start(button,True,True,0)
		rbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		rbox.pack_start(Gtk.Label(label='Range'),True,True,0)
		self.range_set = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		self.range_set.pack_start(Gtk.Label(label='Min'),True,True,0)
		self.min_entry = Gtk.Entry()
		self.min_entry.connect('changed',self.on_range_entry_changed,'min')
		self.min_entry.set_tooltip_text('minimum value to  show on chart')
		self.range_set.pack_start(self.min_entry,True,True,0)
		self.range_set.pack_start(Gtk.Label(label='Max'),True,True,0)
		self.max_entry = Gtk.Entry()
		self.max_entry.connect('changed',self.on_range_entry_changed,'max')
		self.max_entry.set_tooltip_text('maximum value to  show on chart')
		self.range_set.pack_start(self.max_entry,True,True,0)
		self.range_set.set_sensitive(self.chart.relative_scale==False)
		self.min_entry.set_text(f'{self.min_value}')
		self.max_entry.set_text(f'{self.max_value}')

		rbox.pack_start(self.range_set,True,True,0)
		cbox_outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		cbox_outer.pack_start(Gtk.Label(label='Colors'),True,True,0)
		cbox_outer.pack_start(
			self.create_color_entry(self.background_color,'Area','background_color'),True,True,0
		)
		cbox_outer.pack_start(
			self.create_color_entry(self.legend_color,'Legend','legend_color'),True,True,0
		)
		cbox_outer.pack_start(
			self.create_color_entry(self.line_color,'Line','line_color'),True,True,0
		)
		scbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		adjustment = Gtk.Adjustment(
			value = self.line_width,
			lower = 1, 
			upper = 10,
			step_increment = 1,
			page_increment = 1,
			page_size = 0)
		self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
		self.scale.set_digits(0)
		self.scale.set_range(1, 10)  # Set the range of the scale
		self.scale.set_value(self.line_width)  # Set the initial value
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
		bbox.pack_start(Gtk.Label(label='Save Changes'),True,True,0)
		bbox.pack_start(ok_button,True,True,0)
		bbox.pack_start(cancel_button,True,True,0)
		self.keysel = widgets.ListBox(self.kavail,onSelect=self.change_key)
		self.keysel.set_tooltip_text('Select item to chart')
		keybox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		keybox.pack_start(Gtk.Label(label='Value to chart'),True,True,0)
		keybox.pack_start(self.keysel,True,True,0)
		self.keysel.select_row_by_label(self.key)
		box.pack_start(keybox,True,True,0)
		box.pack_start(bbox,True,True,0)
		return box

	def on_ok_cancel_clicked(self,widget,action):
		if action == 'ok':
			try:
				mv = float(self.min_entry.get_text())
				xv = float(self.max_entry.get_text())
			except:
				widgets.ErrorDialog('Error','Range values need to be numbers',None)
			debug(f'mv/xv',mv,xv)
			self.min_value = mv
			self.max_value = xv
			self.background_color = self.color_buttons['Area'].get_color_value()
			self.line_color = self.color_buttons['Line'].get_color_value()
			self.legend_color = self.color_buttons['Legend'].get_color_value()
			self.line_width = self.scale.get_value()
			self.key = self.keysel.get_selected_item()
			self.keyranges[self.key] = (mv,xv)
			self.chart.set_line_width(self.line_width)
			self.chart.set_colors(
				line_color=self.line_color,
				legend_color=self.legend_color,
				background_color=self.background_color
				)
			self.chart.set_scale(*self.keyranges[self.key],False)
			debug('scale: ',self.keyranges[self.key])
			self.save_config()
		self.expander.set_expanded(False)

	def on_scale_changed(self,widget):
		self.line_width = int(widget.get_value())
		self.chart.set_line_width(self.line_width)

	def on_expander_changed(self,widget,event):
		pass

	def on_configure(self,widget,event):
		self.pos = tuple(self.get_window().get_position())
		if not self.expander.get_expanded():
			self.size = tuple(self.get_size())

	def on_range_entry_changed(self,widget,tag):
		return
		try:
			value = float(widget.get_text())
		except:
			return
		if not tag in ['min','max']:
			return
		debug("setattr(self,f'{}_value',{})".format(tag,value))
		setattr(self,f'{tag}_value',value)
		self.keyranges[self.key] = (self.min_value,self.max_value)
		self.chart.set_scale(self.min_value,self.max_value,False)
		self.save_config()
		debug(f'new range is {self.min_value}-{self.max_value}')

	def on_interval_change(self,widget,*args):
		self.interval = widget.get_value()
		debug("new interval",self.interval)

	def create_color_entry(self,color,text,tag):
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		label = Gtk.Label(label=text)
		button = ColorButton(color,None,None)
		self.color_buttons[text] = button
		box.pack_start(label,True,True,0)
		box.pack_start(button,True,True,0)
		return box

	def set_a_color(self, color, tag):
		try:
			if getattr(self,tag):
				setattr(self,tag,color)
				setattr(self.chart,tag,color)
		except:
			debug(f"Invalid color/tag combination {color}/{tag}")

	def change_key(self,widget, key):
		if key == self.key:
			return
		self.key = key
		if not key in self.keyranges:
			mnv,mxv = (0,100)
		else:
			mnv,mxv = self.keyranges[self.key]
		self.data = boundlist.BoundList(50)
		self.min_entry.set_text(f'{mnv}')
		self.max_entry.set_text(f'{mxv}')
		self.chart.set_scale(mnv,mxv)
		self.min_value = mnv
		self.max_value = mxv
		self.set_title(f'{self.name} - {self.key}')


	def update(self):
		if not self.key:
			debug("No key set")
			return
		sdata = self.sensor.read()
		if not sdata or 'error' in sdata:
			debug("error, sdata",sdata)
			return
		value = sdata[self.key]
		self.vlabel.set_markup(f'<span background="black" color="#00ff00">{value:>8.4f}</span>')
		self.data.append(value,)
		self.chart.set_data(self.data)

	def _trigger(self):
		if self.keepging:
			self.update()
			GLib.timeout_add(self.interval,self._trigger)

	def stopit(self,*args):
		self.save_config()
		debug("bye")
		self.keepging = False
		if callable(self.on_close):
			self.on_close(self.name)
		self.destroy()

	def save_config(self):
		config_file = 'sensors.json'
		if not self._initialized:
			debug("changes not save, class isn't initialized yet")
			return
		vals = [
			'keyranges',
			'key',
			'size',
			'pos',
			'interval',
			'background_color',
			'legend_color',
			'line_color',
			'line_width',
			'min_value',
			'max_value'
		]
		if not 'chart' in self.config['sensors'][self.name]:
			self.config['sensors'][self.name]['chart'] = {}

		if not 'keyranges' in self.config['sensors'][self.name]['chart']:
			self.config['sensors'][self.name]['chart']['keyranges'] = self.keyranges
		else:
			self.min_value,self.max_value = self.config['sensors'][self.name]['chart']['keyranges'][self.key]
		size = self.size
		pos = self.pos
		self.config['sensors'][self.name]['chart']['size'] = size
		self.config['sensors'][self.name]['chart']['pos'] = pos
		for v in vals:
			iv = getattr(self,v)
			if type(v) is set or type(v) is tuple:
				debug(f'VSET {v} will be {tuple(v)}')
				v = tuple(v)
			debug(f'{v} = {iv}')
			self.config['sensors'][self.name]['chart'][v] = getattr(self,v)

		tmpfile = f'.sensors-{os.getpid()}.tmp'
		with open(tmpfile,'w') as f:
			json.dump(self.config,f,indent=4)
		os.rename(tmpfile,config_file)

if __name__ == "__main__":
	from dflib.theme import change_theme
	if len(sys.argv) != 3:
		print(f"usage: {sys.argv[0]} sensor name key",file=sys.stderr)
		sys.exit(1)
	try:
		with open('sensors.json') as f:
			config = json.load(f)
	except:
		print("Can't read sensors.json",file=sys.stderr)
		sys.exit(1)
	
	change_theme(config['dark_mode'])
	name = sys.argv[1]
	key = sys.argv[2]

	if name in config['sensors']:
		#if 'chart' in config['sensors'][name]:
		win = ChartWindow(config,name=name,key=key,data_path='/Users/nicci/Network/sensor')
		win.connect('destroy',Gtk.main_quit)
		win.show_all()
		win.present()
		Gtk.main()
		#else:
		#	print(f'No chart defined for {name}',file=sys.stderr)
	else:
		print(f'No sensor defined for {name}',file=sys.stderr)

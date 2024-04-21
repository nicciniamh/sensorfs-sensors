#!/Users/nicci/pyenv/bin/python
'''
Sensor display in an explorer/finder like window. Each sensor is represented 
by an icon. Each sensor may be edited by clicking on a context-meny. Sensors
may be added or removed. The icons may be sorted Each sensor can have a quick
view of their settings via "get info" on their meny. The overall program 
settings are set via the tool bar. When the program starts any active sendetail
windows are reopeneed. from the toolbar active windows may be hidden or raised. 
'''
import argparse
import sys
import os
import json
import psutil
import gi
import time
import signal
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

prog_dir = os.path.expanduser('/Users/nicci/sensors-gui')
sys.path.append(os.path.expanduser('/Users/nicci/lib'))
sys.path.append(prog_dir)
os.chdir(prog_dir)

from dflib import widgets, rest
from dflib.LiveChart import LiveChart
from dflib.theme import change_theme
from dflib.debug import debug, set_debug, dpprint, set_log_file
import sensoredit
from sendetail import SenDetail
from about import AboutDialog
from config import SensorsConfig
from iconbox import IconWindow
import chartwin

program_version="2.5.0 (20 April 2024)"
pid_file = '/tmp/.sensors'

class Toolbar(Gtk.Toolbar):
	''' Generate a toolbar of TooButtons. To create the toolbar, 
		a dict is passed indexed title (for tooltip) with:
			name: a simple name
			icon: gtk icon name
			callback: function to call with button is clicked.
	'''
	def __init__(self,items):
		Gtk.Toolbar.__init__(self,orientation=Gtk.Orientation.HORIZONTAL)
		self.buttons = {}
		for item,definition in items.items():
			icon = definition['icon']
			callback = definition['callback']
			image = Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.SMALL_TOOLBAR)
			button = Gtk.ToolButton()
			button.set_icon_widget(image)
			button.set_tooltip_text(item)
			self.buttons[item] = {
				"icon": button,
				"name": item,
				"callback": callback
			}
			button.connect('clicked',self.on_button_click,item)
			self.insert(button,0)

	def on_button_click(self,button,item):
		self.buttons[item]['callback'](item)

class Sensors(Gtk.Window):
	''' Main window
	Present a finder like window with icons for each defined sensor.
	Handle aaddition, editing and removal of sensors. Icons can be sorted 
	through the context menu. Program configuration is done from the toolbar
	config item. 

	Key attributes:
		config: Global program configuration dict
		actives: The "actives list": A dict, keyed by title, of active detail window objects
		icon_dict: a dictionary formatted for IconWindow

	'''
	def __init__(self,config):
		tbitems = {
			"Hide all windows": {"icon": "go-down", 		"callback": self.minmize_all},
			"Show all windows": {"icon": "go-up", 			"callback": self.maximize_all},
			"Configure App": 	{"icon": 'emblem-system',	"callback": self.open_config},
			"Add a  sensor":	{"icon": 'list-add', 		"callback": self.add_sensor},
			"About Sensors": 	{"icon": 'help-about', 		"callback": self.about},
		}
		self.config = config
		Gtk.Window.__init__(self, title=f"Sensors {program_version}")
		self.actives = {}
		self.charts = {}
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.set_border_width(5)
		self.set_default_size(900, 450)  # Set a fixed window size

		self.icon_dict = {}
		for s, d in self.config['sensors'].items():
			if s.startswith('::'):
				continue
			icon = d['icon'] 
			itype = d['sensor']
			self.icon_dict[s] = {"name": s, "icon": os.path.join(prog_dir,icon), "type": itype}

		self.icon_window = IconWindow(
			config=config,
			icon_dict=self.icon_dict,
			menu_callback=self.menu_event,
			activate_callback=self.activate_event,
			context_menu=self.menu_event,
			info_menu=self.get_info,
			add_item_callback=self.add_sensor,
			activate_on_single_click=False,
			active_windows=self.actives,
			active_charts=self.charts
		)
		self.toolbar = Toolbar(tbitems)
		box.pack_start(self.toolbar,False,False,0)
		box.pack_start(self.icon_window,True,True,0)
		self.add(box)
		self.connect('destroy', self.on_self_destroy)
		self.connect('configure-event', self.on_configure_event)
		#self.connect("window-state-event", self.on_window_state_event)
		#self.connect("delete-event", self.on_window_state_event)

		self.show_all()
		window_icon = GdkPixbuf.Pixbuf.new_from_file('icons/humidity.png')
		self.set_icon(window_icon)
		GLib.timeout_add(50,self.present)
		self.open_previous_windows()
		GLib.timeout_add(250,self.check_window_state)
		signal.signal(signal.SIGUSR1,self.on_sig_user1)

	def on_window_state_event(self, widget, event):
		debug('event mask: event.new_window_state & Gdk.WindowState.WITHDRAWN',event.new_window_state & Gdk.WindowState.WITHDRAWN )
		# Check if the window is about to be minimized
		if event.new_window_state & Gdk.WindowState.WITHDRAWN:
			# Restore the window
			#self.deiconify()
			self.present()
			return True

	def check_window_state(self):
		state = self.get_window().get_state()
		if state & Gdk.WindowState.ICONIFIED:
			debug("Iconified state, lets fix it")
			self.present()
		GLib.timeout_add(250,self.check_window_state)

	def on_sig_user1(self,*args):
		debug("")
		self.maximize_all()

	def minmize_all(self,*args):
		''' hide all windows '''
		for label,window in self.actives.items():
			window.do_iconify()
		for label, window in self.charts.items():
			window.do_iconify()

	def maximize_all(self,*args):
		''' show all windows '''
		for label,window in self.actives.items():
			window.do_deiconify()
			window.present()
		for label, window in self.charts.items():
			window.do_deiconify()
			window.present()

		self.deiconify()
		self.present()

	def open_previous_windows(self):
		''' open any previous windows based on active flag in config '''
		if '::main::' in self.config['sensors']:
			debug('moving main')
			if 'size' in self.config['sensors']['::main::']:
				size = self.config['sensors']['::main::']['size']
				self.set_default_size(*size)
				self.resize(*size)
			self.move(*self.config['sensors']['::main::']['pos'])
		for name,sensdef in self.config['sensors'].items():
			if name.startswith('::'):
				continue
			if sensdef['active']:
				self.open_detail_window(name)
			if 'chart' in sensdef:
				if 'active' in sensdef['chart']:
					if sensdef['chart']['active']:
						self.open_chart(name)

	def save_config(self):
		''' Save program configuration '''
		try:
			os.unlink(config_file)
		except:
			pass
		with open(config_file,'w') as f:
			json.dump(self.config,f,indent=4)
	
	def on_configure_event(self, widget, event):
		''' when the window is moved, save the position '''
		current_size = tuple(self.get_size())
		if self.config['sensors']['::main::']['size'] != current_size:
			resized = True
		else:
			resized = False
		self.config['sensors']['::main::']['pos'] = tuple(self.get_position())
		self.config['sensors']['::main::']['size'] = tuple(self.get_size())
		self.save_config()
		if resized:
			GLib.timeout_add(250,self.fixup_after_resize)

	def fixup_after_resize(self,*args):
		'''
		Try to combat weirdness with python gtk windowing on macOS
		'''
		self.show_all()
		self.icon_window.show_all()
		self.toolbar.show_all()

	def open_chart(self, item):
			if item in self.charts:
				self.charts[item].present()
				return
			stype = self.config['sensors'][item]['sensor']
			if stype == 'cpu_usage':
				keyname = 'usage'
			else:
				keyname = 'temp'
			self.charts[item] = chartwin.ChartWindow(
				self.config,
				name=item,
				key=keyname,
				data_path=data_path,
				on_close=self.chart_done)
			debug(f"opened chartwindow for {item}[{keyname}], charts")
			self.config['sensors'][item]['chart']['active'] = True
			if item in self.actives:
				atype=3
			else:
				atype=2
			self.icon_window.activate_icon(item,atype)
			self.save_config()


	def menu_event(self, action, item):
		''' oepn SensorEditor for selected sensor '''
		if item in self.config['sensors']:
			debug(item,action,self.config['sensors'][item])
			if action == 'chart':
				self.open_chart(item)
			elif action == 'show':
				debug('show')
				if item in self.actives:
					self.actives[item].present()
				else:
					debug(f'{item} not active')
			elif action == 'detail':
				if not item in self.actives:
					self.open_detail_window(item)
				else:
					self.actives[item].stopit()
			elif action == 'edit':
				sensoredit.SensorEditor(
					name=item,
					config=self.config,
					callback=self.on_edit_done,
					prog_dir=prog_dir)
			elif action == 'remove':
				self.remove_sensor(item)
		else:
			debug(f'no {item} in sensors')

	def chart_done(self,item):
		debug(f"chart for {item} complete")
		if item in self.charts:
			del self.charts[item] 
		if item in self.actives:
			atype = 1
		else:
			atype = 0
		self.icon_window.activate_icon(item,atype)
		self.config['sensors'][item]['chart']['active'] = False
		self.save_config()

	def on_edit_done(self, name_in, sensor_in, name, sensor):
		'''
		Handle return from the sensor editor. We get in the 
		original name and original sensor definition, plus a new name 
		and new definition. It gets saved to the config. If an open 
		detail window is running it is notifed of the new configuration.
		'''
		self.icon_window.update_icon(name_in,name,sensor['icon'])
		del self.config["sensors"][name_in]
		self.config['sensors'][name] = sensor
		host = self.config['sensors'][name]['host']
		sensor = self.config['sensors'][name]['sensor']
		self.save_config()
		if name_in in self.actives:
			''' get window for the old sensor name, assign it to active list 
			and delete the old active entry. '''
			win = self.actives[name_in]
			self.actives[name_in] = None
			del self.actives[name_in]
			self.actives[name] = win
			self.actives[name].change_sensor(name,host,sensor)
			self.icon_window.update_icon(name_in,name,self.config['sensors'][name]['icon'])
		else:
			debug(f'{name} not found in actives')
			dpprint(self.actives)
		self.save_config()
		debug(f'new config for {name}: {self.config["sensors"][name]}')

	def open_detail_window(self, name):
		'''
		Open detial window for sensor. Place window in list of active windows.
		mark sensor as active in config and save. the icon_window is told 
		to set the icon as active. 
		'''
		sensor = self.config['sensors'][name]
		sen = sensor['sensor']
		host = sensor['host']
		pos = sensor['pos']
		debug(name,sensor)
		win = SenDetail(
			config=config,
			sensor_name=sen,
			host=host,
			title=name,
			position=pos,
			callback=self.on_detail_done,
			move_callback=self.on_detail_move)
		debug("Attemping activation",name)
		if self.charts and name in self.charts:
			atype=3
		else:
			atype=1
		self.icon_window.activate_icon(name,atype)
		debug("setting active to true",name)
		self.actives[name] = win
		self.config['sensors'][name]['active'] = True
		self.save_config()
		win.present()

	def on_detail_move(self,name,position):
		''' this callback is called when the detail window is moved '''
		self.config['sensors'][name]['pos'] = position
		self.save_config()

	def activate_event(self,item):
		''' when an icon is clicked (activated) this 
		method is called to handle the click. item 
		is looked for in actives and if not, a new window
		is created. otherwise the existing window is raised.
		'''
		debug(item)
		if item in self.config['sensors']:
			if item in self.actives:
				self.actives[item].present()
			else:
				self.open_detail_window(item)
		else:
			debug(f'no {item} in sensors')

	def on_detail_done(self,name):
		'''
		when a detail window is close, remove it from
		the active list, tell the icon_window to update 
		the icon to show inactive.
		'''
		self.config['sensors'][name]['active'] = False
		if self.charts and name in self.charts:
			atype=2
		else:
			atype=0
		self.icon_window.deactivate_icon(name,atype)
		del self.actives[name]
		self.save_config()

	def open_config(self,*args):
		''' Open program configuration when config is clicked on toolbar '''
		SensorsConfig(config = self.config,on_complete=self.on_config_done)

	def on_config_done(self,*args):
		''' callback for when program configuration is complete '''
		self.save_config()

	def about(self,item):
		''' open about box '''
		AboutDialog(
			self,
			config,
			os.path.join(prog_dir,'icons','duckie.png'),
			program_version,
	#		self.config['sensors']['::about::']['pos'],
			['::main::'],
			self.about_moved,
			)

	def about_moved(self,position):
		''' callback for hwen aboutbox is moved '''
		self.config['sensors']['::about::']['active'] = False
		self.config['sensors']['::about::']['pos'] = position

	def remove_sensor(self,item):
		''' remove sensor if confirmed '''
		if widgets.yesno(self,f"This cannot be undone. Remoe {item}?") == 'yes':
			if not item in self.config['sensors']:
				debug(f'No such sensor {item}')
				return
			self.icon_window.delete_icon(item)
			if item in self.actives:
				self.actives[item].destroy()
				del self.actives[item]
			del self.config['sensors'][item]


	def add_sensor(self,*args):
		''' add new sensor by calling the sensor editor. '''
		sensoredit.SensorEditor(name=None,config=self.config,callback=self.on_add_sen_done,prog_dir=prog_dir)

	def on_add_sen_done(self,ni,ci,name,definition):
		''' when sensor editor is done on add we get here '''
		definition['pos'] = (0,0)
		definition['active'] = False
		self.config['sensors'][name] = definition
		self.save_config()
		self.icon_window.add_icon(definition['icon'],name)
		debug(name,definition)

	def on_self_destroy(self,*args):
		'''
		When the window is closed perform a little cleanup
		'''
		if os.path.exists(pid_file):
			os.unlink(pid_file)

	def get_info(self,item):
		'''
		when the get_info icon menu is clicked we build up a 
		list of tuples. Each tuple is of label, data. 
		This list is used to create and InfoWindow
		'''
		sensor = self.config['sensors'][item]
		server = self.config['server']
		sensor_name = sensor['sensor']
		sensor_host = sensor['host']
		sdata = rest.RestClient(server=server,host=sensor_host,sensor=sensor_name).read()
		info = [
			('Sensor Host',sensor['host']),
			('Sensor',sensor['sensor']),
			('Active', sensor['active']),
			('icon',sensor['icon']),
		]
		if 'modinfo' in sdata:
			info.append(('module',sdata['modinfo']))
		if 'description' in sdata:
			info.append(('type',sdata['description']))
		debug('info',info)
		pos = (self.icon_window.selected_x+20,self.icon_window.selected_y+75)
		InfoWindow(pos,item,info)


class InfoWindow(Gtk.Window):
	''' simple dialog to show sensor information '''
	def __init__(self,position, title,info):
		def make_label(caption):
			label = Gtk.Label()
			label.set_markup(caption)
			label.set_halign(Gtk.Align.START)
			label.set_justify(Gtk.Justification.LEFT)
			css_data = '.infolabel {font-family: Mono; padding-left: 5px; padding-right: 5px }'
			widgets._widget_set_css(label, 'infolabel', css_data)
			return label

		Gtk.Window.__init__(self,title="Sensor Information")
		self.set_border_width(10)
		grid = Gtk.Grid()
		row = 0
		icon = False
		for i in info:
			label,value = i
			if label == 'icon' and value:
				debug("getting icon",value)
				icon = os.path.join(prog_dir,value)
				icon = Gtk.Image.new_from_file(icon)
			if dark_mode:
				cap = make_label(f'<span color="#AfAfAf">{label}:</span>')
			else:
				cap = make_label(f'<span color="#7f7f7f">{label}:</span>')
			val = make_label(f'<b>{value}</b>')
			grid.attach(cap,0,row,1,1)
			grid.attach(val,1,row,1,1)
			row += 1
		label = Gtk.Label()
		if dark_mode:
			tcolor="#AFAFAF"
		else:
			tcolor="#7f7f7f"
		label.set_markup(f'<span color="{tcolor}"><b>{title}</b></span>')
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		box.pack_start(label,True,True,0)
		if icon:
			box.pack_start(icon,True,True,0)
		box.pack_start(grid,True,True,0)
		self.add(box)
		self.set_decorated(False)
		self.connect('key-press-event', self.on_key_press)
		self.connect('focus-out-event', self.on_focus_out)
		debug("moving to",*position)
		self.move(*position)
		self.show_all()

	def on_focus_out(self,*args):
		'''
		when the "get info" pane loses focus, kill it.
		'''
		self.destroy()

	def on_key_press(self,widget,event,*args):
		'''
		if the window receives a key, check for escape if so close
		'''
		if event.keyval == Gdk.KEY_Escape:
			self.destroy()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
			prog=f"Sensors {program_version}",
			description="GUI Interface to read sensors via SensorFS RestAPI",
			epilog="A SensorFS RestAPI Example. See https://github.com/nicciniamh/sensorfs"
		)
	parser.add_argument('-d','--debug',action='store_true',help='turn on copious debugging messages',default=False)
	parser.add_argument('--no-daemon',action='store_true',default=False, help='do not start daemon if not running')
	parser.add_argument('--run-dir',type=str,default=prog_dir,help='Set runtime path')
	parser.add_argument('-l','--logfile',type=str,metavar='file',default=False, help='send debug messages to file')
	if os.uname()[0] == 'Darwin':
		data_path = '/Users/nicci/Network/sensor'
	else:
		data_path = '/sensor'
	if not os.path.exists(data_path) or not os.path.isdir(data_path):
		print(f"The path, {data_path}, does not exist. Cannot continue",file=sys.stderr)
		sys.exit(1)
	args = parser.parse_args()
	config_file = os.path.join(prog_dir,'sensors.json')
	with open(config_file,"r") as f:
		config = json.load(f)
	set_debug(args.debug)
	if args.debug:
		set_debug(True)
	if args.logfile:
		set_log_file(args.logfile)
	dark_mode = False
	if 'dark_mode' in config:
		dark_mode = config['dark_mode']
	change_theme(dark_mode)
	other_instance = False
	if os.path.exists(pid_file):
		debug("pid file found")
		with open(pid_file,'r') as f:
			pid = int(f.read().strip())
		try:
			p = psutil.Process(pid=pid)
			other_instance = True
			os.kill(pid,signal.SIGUSR1)
		except:
			os.unlink(pid_file)
			other_instance = False
	with open(pid_file,'w') as f:
		f.write(f'{os.getpid()}')
	win = Sensors(config)
	win.connect("destroy", Gtk.main_quit)
	Gtk.main()

'''
Module to edit sensor definitons

From this module a Gtk Window is created. The top portion of the window 
contains fields for name host, sensor, and icon. 
The bottom portion contains the ChartConfigPane (see chartconf.py)
the ok and cancel buttons are handled by ChartConfigPane, which hands us back
the chart configuration object. from there we pull in the other data and callback
to the parent. 
'''
import os
import gi
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
from sencaps import SensorCapabilities
from iconbox import IconWindow
from dflib import widgets
from dflib.debug import debug, dpprint, set_debug
from dflib import rest, theme
import chartconf
import copy
import defaults

class SensorInfo:
	'''
	retrieve sensor information in a nice little dict
	'''
	def __init__(self,server):
		'''
		server = SensorFS RestAPI server to retrieve data from
		'''
		self.server = server
		self.hosts = {}
		r = rest.RestClient(server=self.server,host='none',sensor='none')
		hlist = r.hosts()
		for host in hlist:
			r = rest.RestClient(server=self.server,host=host,sensor='none')
			self.hosts[host] = r.list()
			self.hosts[host].sort()

	def sensor_hosts(self):
		'''
		return a list of hosts on which sensors reside
		'''
		return list(self.hosts.keys())
	
	def sensors_on_host(self,host):
		'''
		return a list of sensors for a host
		'''
		return self.hosts[host]
	
		
class IconSelector(Gtk.Window):
	'''
	This class creates a window with an IconWindow from a dict of icon
	definitions to be chosen for a sensor. 
	'''
	def __init__(self,parent,base_dir, callback):
		self.callback = callback
		Gtk.Window.__init__(self, title="Select Icon")
		with open('icons/icons.json') as f:
			self.icon_dict = json.load(f)

		self.base_dir = base_dir
		self.set_border_width(10)
		self.set_default_size(900, 550)  # Set a fixed window size
		for item, definition in self.icon_dict.items():
			debug('fixing',definition)
			definition['icon'] = os.path.join(base_dir,definition['icon'])
		# Set the window type hint to override the decoration
		self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
		self.set_transient_for(parent)
		# Set the window size and position
		self.set_position(Gtk.WindowPosition.CENTER)
		self.icon_window = IconWindow(
			icon_dict=self.icon_dict,
			activate_callback=self.activate_event,
			context_menu=False,
			info_menu=False,
			activate_on_single_click=True
		)
		self.add(self.icon_window)
		self.show_all()

	def activate_event(self,item):
		'''
		when activated send the icon path to the caller 
		'''
		if callable(self.callback):
			iconpath =  self.icon_dict[item]['icon'].replace(f'{self.base_dir}/','')
			self.callback(iconpath)
		self.destroy()


class SensorEditor(Gtk.Window):
	'''
	This class creates a window with a label for sensor name, a listbox for 
	sensor hosts and sensor names each. A button can be clicked to set the
	icon for the sensor. This class can be called for a new sensor or existing one. 
	'''
	def __init__(self,*args,**kwargs):
		self.name = None
		self.config = None
		self.callback = None
		self.config_in = {}
		self.name_in = None
		self.posiition = (0,0)
		for k,v in kwargs.items():
			if k in ['name','config','callback','text','prog_dir','position']:
				setattr(self,k,v)
			else:
				raise ValueError(f"Invalid keyword argument {k}")
		if self.name:
			self.sensor = self.config['sensors'][self.name]
			self.sensor_in = copy.deepcopy(self.sensor)
			self.name_in = self.name
			self.sensor_set = self.host_set = True

			Gtk.Window.__init__(self,title=f"Sensor Editor - {self.name}")
		else:
			self.sensor = {}
			self.sensor_in = {}
			Gtk.Window.__init__(self,title="Sensor Editor - (new sensor)")
		
		if not 'chart' in self.sensor:
			self.sensor['chart'] = defaults.chart

		self.si = SensorInfo(self.config['server'])
		if 'key' in self.sensor['chart']:
			key = self.sensor['chart']['key']
		else:
			sc = SensorCapabilities(self.sensor['sensor'])
			key = sc.get_sensor_keys()[0]
		self.sensor['chart']['key'] = key
		self.connect('delete-event',self.on_wm_delete_event)
		self.hosts = self.si.sensor_hosts()

		if self.name:
			self.host = self.sensor['host']
			self.sendev = self.sensor['sensor']
			imgpath = os.path.join(self.prog_dir,self.sensor['icon'])
		else:
			imgpath = os.path.join(self.prog_dir,'icons/select.png')
			self.host = self.hosts[0]
			self.sendev = self.sensors[self.host][0]

		self.sensors = self.si.sensors_on_host(self.host)

		img =  Gtk.Image.new_from_file(imgpath)
		img.set_size_request(64, 64)

		debug('icon path',imgpath,'img',img)
		self.icon = Gtk.Button()
		self.icon.set_image(img)
		self.icon.connect('clicked',self.select_icon)
		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		
		## Create HBOX for sensor name and entry field
		lbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		self.entry = Gtk.Entry()
		self.entry.set_width_chars(50)
		if self.name:
			self.entry.set_text(self.name)
		lbox.pack_start(Gtk.Label(label='Sensor Name'), True, True, 0)
		lbox.pack_start(self.entry, True, True, 0)
		vbox.pack_start(lbox,True,True,0)

		hsenbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		vbox.pack_start(hsenbox,True,True,0)

		hsenbox.pack_start(Gtk.Label(label="Select host and Sensor"),True,True,0)
		self.host_select = self._get_selector(hsenbox,self.hosts,'Host',self.on_hostname_changed)
		self.sen_select = self._get_selector(hsenbox,self.sensors,'Sensor',self.on_sensor_changed)

		ibox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ibox.pack_start(Gtk.Label(label="Sensor Icon"),True,True,0)
		ibox.pack_start(self.icon,False,False,10)
		hsenbox.pack_start(ibox,True,True,0)

		self.cconf = chartconf.ChartConfigPane(
			self.sensor['chart'],
			sensor_name = self.name or "(new sensor)",
			sensor_type = self.sendev,
			on_complete = self.on_conf_complete
			)
		confpane = self.cconf.config_pane
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		widgets._widget_set_css(box,'box','.box {padding: 5px}')
		if theme.dark_mode:
			label_css = """
			.slabel {
				margin-bottom: 5px; 
				padding-bottom: 10px; 
				padding-top: 10px;
				color: white;
				background-color: #00005f;
				}
			"""
		else:
			label_css = """	.slabel {
			margin-bottom: 5px; 
			padding-bottom: 10px; 
			padding-top: 10px;
			color: white;
			background-color: #00007f;
			}
		"""

		slabel = Gtk.Label()
		slabel.set_markup('Sensor Settings')
		widgets._widget_set_css(slabel,'slabel',label_css)
		box.pack_start(slabel,True,True,0)
		box.pack_start(vbox,True,True,0)
		clabel = Gtk.Label()
		clabel.set_markup('Chart Settings')
		widgets._widget_set_css(clabel,'slabel',label_css)
		box.pack_start(clabel,True,True,0)
		box.pack_start(confpane,True,True,0)
		debug("setting values:",self.host,self.sendev)
		self.host_select.set_value(self.host)
		self.sen_select.set_value(self.sendev)
		self.add(box)
		self.show_all()

	def _get_selector(self, box, strings, caption, callback):
		line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		hlabel = Gtk.Label(label=caption)
		hlabel.set_width_chars(20)
		line.pack_start(hlabel,True,True,0)
		#select = widgets.StringSpinButton(strings,callback)
		#select.set_content_width(10)
		select = widgets.SimpleCombo(strings,on_change=callback)
		line.pack_start(select,True,True,0)
		box.pack_start(line,True,True,0)
		return select

	def on_conf_complete(self,button,senname,key,cobj):
		debug(button,senname,key)
		if button == 'cancel':
			self.destroy()
			return
		name = self.entry.get_text()
		#debug(f'Ok: {name}::{self.sensor}')
		self.sensor['chart'] = copy.deepcopy(cobj)
		self.on_ok_clicked(True)

	def on_hostname_changed(self,host):
		self.host = host
		self.sensors = self.si.sensors_on_host(self.host)
		if not self.sendev in self.sensors:
			self.sendev = self.sensors[0]
		debug(self.sendev, self.sensor['chart'])
		self.sen_select.set_value(self.sendev,self.sensors)
		self.cconf.reconfigure(self.sendev,self.sensor['chart'])
	
	def on_sensor_changed(self,sendev):
		self.sendev = sendev
		cap = SensorCapabilities(sendev).get_cap()
		self.cconf.reconfigure(self.sendev,self.sensor['chart'])
		debug()

	def select_icon(self,*args):
		'''
		when the icon select button is clicked we create an IconSelector
		'''
		IconSelector(self,self.prog_dir, self.on_icon_selected)

	def on_icon_selected(self,iconpath):
		'''
		When an icon is selected in the icon selector this function is called
		to save it in the sensor definition
		'''
		self.sensor['icon'] = iconpath
		iconpath = os.path.join(self.prog_dir,iconpath)
		img = Gtk.Image.new_from_file(iconpath)
		self.icon.set_image(img)

	def on_wm_delete_event(self,*args):
		'''
		if the close button is clicked check to save changes
		'''
		if widgets.yesno(self,'Save any changes and Close?') == 'yes':
			self.on_ok_clicked()
			return False
		else:
			return True

	def on_ok_clicked(self,obj_init=False):
		if not obj_init:
			self.sensor['chart'] = self.cconf.cobj
		sensor = copy.deepcopy(self.sensor)
		self.callback(self.name_in, self.sensor_in, self.name,self.sensor)
		self.destroy()

	def on_cancel_clicked(self,*args):
		''' if cancel is clicked we just go away '''
		self.destroy()

	def on_select_host(self,widget,host,*args):
		'''
		when a host is selected our 'being edited' sensor definition is modified
		with the new sensor host 
		'''
		self.host = host;
		self.sensor['host'] = host
		debug(f'selected host {host}: {self.sensors[host]}')
		self.sensor_box.populate(self.sensors[host])
		self.hostLabel.set_text(host)

	def on_select_sensor(self,widget, sensor,*args):
		'''
		when a sensor is selected our 'being edited' sensor definition is modified
		with the new sensor host 
		'''
		self.sensor['sensor'] = sensor
		debug(f'Selected sensor is {self.sensor}')
		self.sensorLabel.set_text(sensor)

if __name__ == "__main__":
	def dummy_callback(*args):
		debug(args)
	import cfg
	from dflib.theme import change_theme
	import argparse
	parser = argparse.ArgumentParser(description="edit test")
	parser.add_argument('-d','--debug',action='store_true',default=False)
	parser.add_argument('-m','--dark-mode',action='store_true',default=False)
	parser.add_argument('-n','--name',type=str, default='Sensor - bmp280(1)')
	args = parser.parse_args()
	change_theme(args.dark_mode)
	config = cfg.get_config()
	set_debug(args.debug)
	w = SensorEditor(name=args.name, config=config, prog_dir=os.getcwd(),callback=dummy_callback)
	w.connect('destroy',Gtk.main_quit)
	w.show_all()
	Gtk.main()
'''
Module to edit sensor definitons
'''
import os
import gi
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
from iconbox import IconWindow
from dflib import widgets
from dflib.debug import debug
from dflib import rest

def sensorHosts(server):
	'''
	use REST client to retrieve list of sensor hosts
	'''
	global config
	debug(f'sensorHosts: server={server}')
	h = rest.RestClient(server=server,host='none',sensor='none')
	hosts = h.hosts()
	hosts.sort()
	return hosts

def sensorsOnHost(server,host):
	'''
	use REST client to retrieve list of seonsor for a given host
	'''
	global config
	h = rest.RestClient(server=server,host=host,sensor='none')
	sensors = h.list()
	sensors.sort()
	return sensors

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
			self.sensor_in = self.sensor.copy()
			self.name_in = self.name
			Gtk.Window.__init__(self,title=f"Sensor Editor - {self.name}")
		else:
			self.sensor = {}
			self.sensor_in = {}
			Gtk.Window.__init__(self,title="Sensor Editor - (new sensor)")


		self.connect('delete-event',self.on_wm_delete_event)
		self.sensors = {}
		self.hosts = sensorHosts(self.config['server'])
		for h in self.hosts:
			self.sensors[h] = sensorsOnHost(self.config['server'],h)
		if self.name:
			self.host = self.sensor['host']
			self.sendev = self.sensor['sensor']
			imgpath = os.path.join(self.prog_dir,self.sensor['icon'])
		else:
			imgpath = os.path.join(self.prog_dir,'icons/select.png')
			self.host = self.hosts[0]
			self.sendev = self.sensors[self.host][0]

		img =  Gtk.Image.new_from_file(imgpath)
		img.set_size_request(64, 64)

		debug('icon path',imgpath,'img',img)
		self.icon = Gtk.Button()
		self.icon.set_image(img)

		left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
		center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
		right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)

		grid = Gtk.Grid()
		self.entry = Gtk.Entry()
		self.entry.set_width_chars(50)
		if self.name:
			self.entry.set_text(self.name)
		grid.attach(Gtk.Label(label='Sensor Name'),0,0,1,1)
		grid.attach(self.entry,1,0,2,1)
		grid.attach(left,0,1,1,1)
		grid.attach(center,1,1,1,1)
		grid.attach(right,2,1,1,1)

		center.pack_start(Gtk.Label(label="Hosts"),True,True,20)
		right.pack_start(Gtk.Label(label="Sensors"),True,True,20)
		if self.name:
			self.host = self.sensor['host']
			self.hostLabel = Gtk.Label(label=self.sensor['host'])
			self.sensorLabel = Gtk.Label(label=self.sensor['sensor'])
		else:
			self.hostLabel = Gtk.Label()
			self.sensorLabel = Gtk.Label()

		if self.name:
			self.hostLabel.set_text(self.sensor['host'])
			self.sensorLabel.set_text(self.sensor['sensor'])

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
		if self.name:
			vbox.pack_start(Gtk.Label(label=f"Sensor Editor - {self.name}"),True,True,10)
		else:
			vbox.pack_start(Gtk.Label(label="Sensor Editor"),True,True,10)
		vbox.pack_start(grid,True,True,0)
		ibox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		ibox.pack_start(Gtk.Label(label="Sensor Icon"),True,True,0)
		ibox.pack_start(self.icon,False,False,10)
		vbox.pack_start(ibox,True,True,0)
		self.icon.connect('clicked',self.select_icon)
		self.host_box = widgets.ListBox(self.hosts,onActivate=self.on_select_host)
		if self.name:
			self.host_box.select_row_by_label(self.sensor['host'])
		center.pack_start(self.host_box,True,True,0)
		self.sensor_box = widgets.ListBox(self.sensors[self.host],onActivate=self.on_select_sensor)
		if self.name:
			self.sensor_box.select_row_by_label(self.sensor['sensor'])
		right.pack_start(self.sensor_box,True,True,0)
		bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		okbutton = Gtk.Button(label="Ok")
		cancelbutton = Gtk.Button(label="Cancel")
		bbox.pack_start(okbutton,True,True,10)
		bbox.pack_start(cancelbutton,True,True,10)
		okbutton.connect('clicked',self.on_ok_clicked)
		cancelbutton.connect('clicked',self.on_cancel_clicked)
		vbox.pack_start(bbox,True,True,10)
		self.add(vbox)
		window_icon = GdkPixbuf.Pixbuf.new_from_file('icons/humidity.png')
		self.set_icon(window_icon)
		self.set_position(Gtk.WindowPosition.CENTER)
		self.show_all()

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

	def on_ok_clicked(self,*args):
		''' save changes when Ok is clicked or on_wm_delete_event '''
		name = self.entry.get_text()
		debug(f'Ok: {name}::{self.sensor}')
		self.callback(self.name_in, self.sensor_in, name,self.sensor)
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



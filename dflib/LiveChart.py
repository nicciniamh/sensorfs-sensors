import os
import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import numpy as np
import cairo
sys.path.append(os.path.expanduser('~/lib'))
import httpsen2
from dflib.debug import debug, set_debug
class LiveChart(Gtk.Box):
	def __init__(self, width, height, **kwargs):
		super().__init__()
		self.scale_set = False
		self.width = width
		self.height = height
		self.background_color = kwargs.get('background_color', 'white')
		self.legend_color = kwargs.get('legend_color', 'black')
		self.line_color = kwargs.get('line_color', 'blue')
		self.line_width = kwargs.get('line_width', 2)
		self.min_value = kwargs.get('min_value', 0)
		self.max_value = kwargs.get('max_value', 100)
		self.relative_scale = kwargs.get('relative_scale')
		self.data = []

		self.canvas = Gtk.DrawingArea()
		self.canvas.set_size_request(width - 10, height - 10)  # Offset by 10 pixels
		self.pack_start(self.canvas, True, True, 0)
		self.canvas.connect('configure-event',self.on_canvas_configure)
		self.connect('configure-event',self.on_configure)
		self.connect("draw", self.on_draw)

	def set_colors(self,**kwargs):
		for k,v in kwargs.items():
			debug(k,v)
			setattr(self,k,v)

	def on_configure(self, widget, event):
		self.show_all()

	def on_canvas_configure(self, widget, event):
		allocation = widget.get_allocation()
		self.width = allocation.width
		self.height = allocation.height
		widget.queue_draw()

	def on_draw(self, widget, cr):
		# Set background color
		cr.set_source_rgb(*self.hex_to_rgb(self.background_color))
		cr.paint()

		# Draw Y-axis tick marks and labels
		num_ticks = 5
		tick_spacing = (self.height - 10) / (num_ticks - 1)  # Adjusted spacing
		# Draw line graph
		try:
			#debug(self.min_value,self.max_value)
			cr.set_source_rgb(*self.hex_to_rgb(self.line_color))
			cr.set_line_width(self.line_width)
			num_points = len(self.data)
			if num_points >= 1:
				x_spacing = (self.width - 10) / (num_points - 1)  # Adjusted spacing
				for i in range(num_points - 1):
					x1 = i * x_spacing
					y1 = (self.data[i] - self.min_value) / (self.max_value - self.min_value) * (self.height - 10)  # Adjusted y position
					x2 = (i + 1) * x_spacing
					y2 = (self.data[i + 1] - self.min_value) / (self.max_value - self.min_value) * (self.height - 10)  # Adjusted y position
					cr.move_to(x1, self.height - y1 - 5)  # Adjusted y position
					cr.line_to(x2, self.height - y2 - 5)  # Adjusted y position
					cr.stroke()
		except ZeroDivisionError:
			pass

		for i in range(num_ticks):
			y = self.height - i * tick_spacing - 5  # Adjusted y position
			cr.move_to(0, y)
			cr.line_to(10, y)
			cr.stroke()

			# Calculate tick label value
			value = self.min_value + i * (self.max_value - self.min_value) / (num_ticks - 1)
			# Display tick label
			label = "{:.1f}".format(value)
			cr.set_source_rgb(*self.hex_to_rgb(self.legend_color))
			cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
			cr.set_font_size(14)
			_, text_width, text_height = cr.text_extents(label)[:3]
			if i == 0:  # Adjust position for top label
				y -= text_height
			cr.move_to(15, y + text_height / 2)  # Adjusted y position for label
			cr.show_text(label)


	def hex_to_rgb(self, hex_color):
		hex_color = hex_color.lstrip('#')
		return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))


	def set_scale(self,min_value=None,max_value=None,relative_scale=-1):
		scale = 'unused'
		if min_value != None and max_value != None:
			debug(f'min_value={min_value},max_value={max_value}')
		if relative_scale != -1:
			pass
		if min_value != None:
			self.min_value = min_value
			debug('new min',self.min_value)

		if max_value != None:
			self.max_value = max_value
			debug('new max',self.max_value)

		if self.relative_scale:
			if len(self.data) >1:
				mnv = min(self.data)
				mnv -= (mnv*1.25)
				mxv = max(self.data) 
				mxv += (mxv*1.25)
				scale = (mxv - mnv)

		self.queue_draw()

	def set_min_value(self,min_value):
		self.set_scale(min_value,None)

	def set_max_value(self,max_value):
		self.set_scale(None,max_value)

	def set_line_width(self,value):
		self.line_width = value
		self.queue_draw()

	def set_data(self, data):
		self.data = data
		self.set_scale(None,None)

if __name__ == "__main__":
	set_debug(True)
	sensor = httpsen2.httpSen(server='pi4',host='pi4',sensor='cpu_usage')
	data = [sensor.read()['usage']]
	win = Gtk.Window()
	size = (400,250)
	win.connect("destroy", Gtk.main_quit)
	win.set_default_size(*size)

	live_chart = LiveChart(
		*size, 
		background_color='#000000', 
		legend_color='#ffffff', 
		line_color='#0000FF', 
		line_width=4, 
		min_value=0,
		max_value=100)
	live_chart.set_data(data)  # Set initial data
	win.add(live_chart)
	win.show_all()

	def update_chart():
		global data
		data.append(sensor.read()['usage'])
		if len(data) > 50:
			data = data[:-50]
		live_chart.set_data(data)  # Update data with random values
		return True

	# Update the chart every 1000 milliseconds (1 second)
	GLib.timeout_add(1000, update_chart)

	Gtk.main()

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

def get_icon_images(source_image_path):
	'''
	Create a suitable icon from a file for both regular and acive by 
	applying an image with the active badge to the source. Return both GdkPixbufs
	'''

	source_image = GdkPixbuf.Pixbuf.new_from_file(source_image_path)
	image_list = [source_image]
	for active in ['badge','chart','both']:
		ipath = os.path.join(os.path.dirname(source_image_path),f"active_{active}.png")
		image2 = GdkPixbuf.Pixbuf.new_from_file(ipath)

		# Scale source_image to the desired dimensions
		scaled_source_image = source_image.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)

		# Create a new transparent image to composite onto
		composite_image = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 64, 64)
		composite_image.fill(0x000000)  # Fill with black

		# Draw scaled_source_image onto the composite image
		scaled_source_image.copy_area(0, 0, 64, 64, composite_image, 0, 0)

		# Calculate position to center image2 on composite_image
		x_offset = (64 - image2.get_width()) // 2
		y_offset = (64 - image2.get_height()) // 2

		# Draw image2 onto the composite image
		image2.composite(
			composite_image,
			x_offset,
			y_offset,
			image2.get_width(),
			image2.get_height(),
			x_offset,
			y_offset,
			1,
			1,
			GdkPixbuf.InterpType.BILINEAR,
			255,
		)
		image_list.append(composite_image)
	return (image_list)
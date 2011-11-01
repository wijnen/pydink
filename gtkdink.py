# gtk stuff for dink, used by editor and player.

import dink
import gtk

class GtkDink (dink.Dink):
	def __init__ (self, root, scale):
		dink.Dink.__init__ (self, root)
		self.colors = ['black', 'dark blue', 'light green', 'cyan', 'orange', 'lavender', '#cc7722', 'light grey', 'dark grey', 'sky blue', 'green', 'yellow', 'yellow', 'pink', 'yellow', 'white']
		for c in range (len (self.colors)):
			self.colors[c] = gtk.gdk.colormap_get_system ().alloc_color (self.colors[c])
		self.scale = scale
	def set_window (self, window):
		self.window = window
		self.gc = gtk.gdk.GC (self.window)
		self.set_scale (self.scale, True)
	def set_scale (self, scale, force = False):
		if self.scale == scale and not force:
			return
		self.scale = scale
		# Flush cache.
		self.cache = []
		self.cache_data = []
	def get_image (self, name):
		# Images are never cached.
		return self.load_pixbuf (self.image.get_file (name))
	def get_tiles (self, num):
		if ('t', num) in self.cache:
			idx = self.cache.index (('t', num))
			self.cache += (self.cache.pop (idx),)
			self.cache_data += (self.cache_data.pop (idx),)
		else:
			# TODO: Throw something out if required.
			self.cache += (('t', num),)
			pb = self.load_pixbuf (self.tile.get_file (num))
			ret = gtk.gdk.Pixmap (self.window, pb.get_width (), pb.get_height ())
			ret.draw_pixbuf (self.gc, pb, 0, 0, 0, 0)
			self.cache_data += (ret,)
		return self.cache_data[-1]
	def get_hard_tiles (self, name):
		if ('h', name) in self.cache:
			idx = self.cache.index (('h', name))
			self.cache += (self.cache.pop (idx),)
			self.cache_data += (self.cache_data.pop (idx),)
		else:
			# TODO: Throw something out if required.
			self.cache += (('h', name),)
			pb = self.load_pixbuf (self.tile.get_hard_file (name))
			ret = gtk.gdk.Pixmap (self.window, pb.get_width (), pb.get_height ())
			ret.draw_pixbuf (self.gc, pb, 0, 0, 0, 0)
			self.cache_data += (ret,)
		return self.cache_data[-1]
	def get_color (self, c):
		return self.colors[c if 0 <= c < len (self.colors) else 0]
	def get_seq (self, seq, frame):
		target = ('s', seq.name, frame)
		if target in self.cache:
			idx = self.cache.index (target)
			self.cache += (self.cache.pop (idx),)
			self.cache_data += (self.cache_data.pop (idx),)
		else:
			# TODO: Throw something out if required.
			self.cache += (target,)
			self.cache_data += (self.load_pixbuf (self.seq.get_file (seq, frame)),)
		return self.cache_data[-1]
	def get_box (self, size, pos, seq, box):
		x = pos[0] - 20
		y = pos[1]
		bb = seq.boundingbox
		w = bb[2] - bb[0]
		h = bb[3] - bb[1]
		# Blame Seth for the computation below.
		x_compat = w * (size - 100) / 100 / 2
		y_compat = h * (size - 100) / 100 / 2
		l = x - seq.position[0] - x_compat
		t = y - seq.position[1] - y_compat
		r = l + w * size / 100
		b = t + h * size / 100
		if box[0] != 0 or box[1] != 0 or box[2] != 0:
			box = list (box)
			if box[0] > w:
				box[0] = w
			if box[1] > h:
				box[1] = h
			if box[2] > w:
				box[2] = w
			if box[3] > h:
				box[3] = h
			l += box[0]
			t += box[1]
			r += box[2] - w
			b += box[3] - h
			bx = box
		else:
			bx = None
		return (x, y), (l, t, r, b), bx
	def load_pixbuf (self, file):
		pbl = gtk.gdk.PixbufLoader ()
		pbl.write (open (file[0]).read (file[1] + file[2])[file[1]:])
		pbl.close ()
		pb = pbl.get_pixbuf ()
		if self.scale != 50:
			pb = pb.scale_simple (pb.get_width () * self.scale / 50, pb.get_height () * self.scale / 50, gtk.gdk.INTERP_NEAREST)
		if file[3] != None:
			pb = pb.add_alpha (*((True,) + file[3]))
		return pb

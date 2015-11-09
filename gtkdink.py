# gtk stuff for dink, used by editor and player.
# vim: set fileencoding=utf-8 foldmethod=marker:

# {{{ Copyright header
# gtkdink.py - library for gtk parts of using pydink games.
# Copyright 2011-2013 Bas Wijnen
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# }}}
# {{{ Imports
import gi
gi.require_version('Gtk', '3.0')
import dink
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
import struct
import Image
# }}}

class GtkDink (dink.Dink): # {{{
	def __init__ (self, root, scale, hard_scale = True):
		dink.Dink.__init__ (self, root)
		self.hard_scale = hard_scale
		self.colors = ['black', 'dark blue', 'light green', 'cyan', 'orange', 'lavender', '#cc7722', 'light grey', 'dark grey', 'sky blue', 'green', 'yellow', 'yellow', 'pink', 'yellow', 'white']
		#for c in range (len (self.colors)):
		#	self.colors[c] = Gdk.colormap_get_system ().alloc_color (self.colors[c])
		self.time = 0
		self.scale = None
		self.set_scale (scale, True)
	def cache_get (self, type, name):
		try:
			ret = self.cache[(type, name)]
		except KeyError:
			return None
		ret[0] = self.time
		self.time += 1
		return ret[1]
	def cache_add (self, type, name, value):
		self.cache[(type, name)] = [self.time, value]
		self.time += 1
	def cache_flush (self):
		self.cache = {}
	def cache_flush_hard (self, name):
		if ('h', name) in self.cache:
			del self.cache[('h', name)]
	def set_window (self, window):
		self.window = window
		self.gc = Gdk.GC (self.window)
		self.set_scale (self.scale, True)
	def set_scale (self, scale, force = False):
		if self.scale == scale and not force:
			return
		self.scale = scale
		# Flush cache.
		self.cache_flush ()
	def get_image (self, name):
		# Images are never cached.
		return self.load_pixbuf (self.image.get_file (name))
	def get_tiles (self, num):
		tile = self.cache_get ('t', num)
		if tile == None:
			t = self.tile.get_file (num)
			if t == None:
				self.cache_add ('t', num, None)
				return None
			pb = self.load_pixbuf (t)
			if not pb:
				return None
			tile = Gdk.Pixmap (self.window, pb.get_width (), pb.get_height ())
			tile.draw_pixbuf (self.gc, pb, 0, 0, 0, 0)
			self.cache_add ('t', num, tile)
		return tile
	def get_hard_tiles (self, name):
		tile = self.cache_get ('h', name)
		if tile == None:
			t = self.tile.get_hard_file (name)
			if t == None:
				self.cache_add ('h', name, None)
				return None
			tile = self.load_pixbuf (t, self.hard_scale)
			self.cache_add ('h', name, tile)
		return tile
	def get_hard_tiles_PIL (self, name):
		tile = self.cache_get ('P', name)
		if tile == None:
			t = self.tile.get_hard_file (name)
			if t == None:
				self.cache_add ('P', name, None)
				return None
			tile = Image.open (dink.filepart (*t[:3]))
			self.cache_add ('P', name, tile)
		return tile
	def get_color (self, c):
		return self.colors[c if 0 <= c < len (self.colors) else 0]
	def get_seq (self, seq, frame):
		ret = self.cache_get ('s', (seq.name, frame))
		if ret == None:
			ret = self.load_pixbuf (self.seq.get_file (seq, frame))
			self.cache_add ('s', (seq.name, frame), ret)
		return ret
	def get_hard_seq (self, seq, frame):
		ret = self.cache_get ('S', (seq.name, frame))
		if ret == None:
			im = self.seq.get_hard_file (seq, frame)
			if not im:
				ret = None
			else:
				ret = self.load_pixbuf (self.seq.get_hard_file (seq, frame) + (None,))
			self.cache_add ('S', (seq.name, frame), ret)
		return ret
	def load_pixbuf (self, file, use_scale = True):
		if file is None:
			return None
		data = open (file[0], 'rb').read (file[1] + file[2])[file[1]:]
		try:
			pbl = Gdk.PixbufLoader ()
			pbl.write (data)
			pbl.close ()
		except GLib.GError:
			open ('/tmp/f.bmp', 'wb').write (data)
			assert data[:2] == 'BM'
			w, h = struct.unpack ('<II', data[0x12:0x1a])
			bpp = struct.unpack ('<H', data[0x1c:0x1e])[0]
			data = data[:0x22] + struct.pack ('<I', w * h * bpp / 8) + data[0x26:]
			pbl = Gdk.PixbufLoader ('bmp')
			pbl.write (data)
			pbl.close ()
		pb = pbl.get_pixbuf ()
		if self.scale != 50 and use_scale:
			w = pb.get_width () * self.scale / 50
			h = pb.get_height () * self.scale / 50
			if h <= 0 or w <= 0:
				return None
			pb = pb.scale_simple (pb.get_width () * self.scale / 50, pb.get_height () * self.scale / 50, Gdk.INTERP_NEAREST)
		if file[3] != None:
			pb = pb.add_alpha (*((True,) + file[3]))
		return pb
# }}}

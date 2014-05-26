#!/usr/bin/env python
# vim: set fileencoding=utf-8 foldmethod=marker:

# {{{ Copyright header
# pde - pydink editor: editor for pydink games.
# Copyright 2011 Bas Wijnen
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
import gtk
import gui
import re
import os
import sys
import dink
import gtkdink
import StringIO
import math
import random
import Image
import tempfile
import glib
#}}}
# {{{ Utility functions
def keylist (x, keyfun):
	l = x.keys ()
	l.sort (key = keyfun)
	return l

def seqlist ():
	return keylist (data.seq.seq, lambda x: data.seq.seq[x].code)

def collectionlist ():
	return keylist (data.seq.collection, lambda x: data.seq.collection[x]['code'])

def fullseqlist ():
	ret = seqlist ()
	for c in collectionlist ():
		for d in (1,2,3,4,5,6,7,8,9):
			if d in data.seq.collection[c]:
				ret += ('%s %d' % (c, d),)
	return ret

def musiclist ():
	return [''] + keylist (data.sound.music, lambda x: x)

def soundslist ():
	return [''] + keylist (data.sound.sound, lambda x: x)

def make_avg ():
	assert len (spriteselect) != 0
	avg = (0, 0)
	l = 0
	for s in spriteselect:
		if s[1]:
			# Don't paste warp points.
			continue
		avg = avg[0] + s[0].x, avg[1] + s[0].y
		l += 1
	return (avg[0] / l) * screenzoom / 50, avg[1] / l * screenzoom / 50

def make_dist (a, b):
	# Make sure it cannot be 0 by adding 1.
	return int (math.sqrt ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)) + 1

def add_warptarget (sp):
	if sp.warp == None:
		return
	if sp.warp[0] in warptargets:
		warptargets[sp.warp[0]].add (sp)
	elif sp.warp[0] in data.world.map:
		warptargets[sp.warp[0]] = set ([sp])
	else:
		warptargets['broken'].add (sp)

def remove_warptarget (sp):
	if sp.warp == None or sp.warp[0] not in warptargets or sp not in warptargets[sp.warp[0]]:
		return
	warptargets[sp.warp[0]].remove (sp)

def reset_globals ():
	global copybuffer, copystart, select, spriteselect, warptargets
	copybuffer = set ()		# Set of tile blocks currently in the buffer. Each element is (map,x,y,tmap,tx,ty), which is the location followed by the content. tmap is always 0-41.
	copystart = (0, 0, 0)		# Start tile at the time ctrl-c was pressed.
	select = Select ()		# Current tiles selection. See Select class above for contents.
	spriteselect = []		# Currently selected sprites: set of (Sprite, is_warp)
	warptargets = {'broken':set ()}	# Map of warp targets per map screen.
# }}}

class Select: # {{{ For tile selections
	def __init__ (self):
		self.start = (0, 0, 0)
		self.data = set ()
	def clear (self):
		self.data.clear ()
	def toggle (self, pos, type):
		p = (pos[0], pos[1], type)
		if p in self.data:
			self.data.remove (p)
		else:
			self.data.add (p)
	def empty (self):
		return len (self.data) == 0
	def compute (self):
		return [[x[t] - self.start[t] for t in range (2)] for x in self.data if x[2] == self.start[2]]
# }}}
# {{{ Global variables
screenzoom = 50			# Number of pixels per tile in view.
updating = True			# Flag if the edit-gui is being updated (which means don't respond to changes).
reset_globals ()
# }}}

class View (gtk.DrawingArea): # {{{
	components = []
	started = None
	collectiontype = None
	def make_gc (self, color):
		ret = gtk.gdk.GC (self.get_window ())
		c = gtk.gdk.colormap_get_system ().alloc_color (color)
		ret.set_foreground (c)
		ret.set_line_attributes (1, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		return ret
	def start (self, widget):
		if View.started != None:
			View.configure (self, self)
			View.update (self)
			return
		View.started = False
		data.set_window (self.get_window ())
		data.set_scale (screenzoom)
		View.gc = self.make_gc (the_gui.default_gc)
		View.gridgc = self.make_gc (the_gui.grid_gc)
		View.gridgc.set_line_attributes (1, gtk.gdk.LINE_ON_OFF_DASH, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		View.gridgc.set_dashes (0, (2, 3))
		View.bordergc = self.make_gc (the_gui.border_gc)
		View.invalidgc = self.make_gc (the_gui.invalid_gc)
		View.selectgc = self.make_gc (the_gui.select_gc)
		View.noselectgc = self.make_gc (the_gui.noselect_gc)
		View.noshowgc = self.make_gc (the_gui.noshow_gc)
		View.hardgc = self.make_gc (the_gui.hard_gc)
		View.warpgc = self.make_gc (the_gui.warp_gc)
		View.bggc = self.make_gc (the_gui.hard_gc)
		View.bggc.set_line_attributes (1, gtk.gdk.LINE_ON_OFF_DASH, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		View.bggc.set_dashes (3, (6, 4))
		View.warpbggc = self.make_gc (the_gui.warp_gc)
		View.warpbggc.set_line_attributes (1, gtk.gdk.LINE_ON_OFF_DASH, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		View.warpbggc.set_dashes (3, (6, 4))
		View.pastegc = self.make_gc (the_gui.paste_gc)
		View.emptygc = self.make_gc (the_gui.empty_gc)
		View.whitegc = self.make_gc (the_gui.white_gc)
		View.pathgc = self.make_gc (the_gui.path_gc)
		View.pathgc.set_line_attributes (5, gtk.gdk.LINE_SOLID, gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
		View.started = True
		View.configure (self, self)
		View.update (self)
	def __init__ (self):
		gtk.DrawingArea.__init__ (self)
		View.components += (self,)
		self.buffer = None		# Backing store for the screen.
		self.pointer_pos = (0, 0)	# Current position of pointer.
		self.selecting = False		# Whether tiles are being selected, or a sequence is being moved at this moment.
		self.panning = False		# Whether the screen is panned at this moment.
		self.offset = (0, 0)		# Current pan setting, in pixels (so after zoom)
		self.screensize = (0, 0)	# Size of the viewport in pixels (updated by configure).
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('configure-event', self.configure)
		self.connect ('enter-notify-event', self.enter)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.ENTER_NOTIFY_MASK)
	def enter (self, widget, dummy):
		self.grab_focus ()
	def configure (self, widget, e = None):
		mid = [(self.offset[x] + self.screensize[x] / 2) * 50 / screenzoom for x in range (2)]
		x, y, width, height = widget.get_allocation()
		self.screensize = (width, height)
		if self.screensize != (0, 0):
			self.offset = [mid[x] * screenzoom / 50 - self.screensize[x] / 2 for x in range (2)]
		if not View.started:
			return
		if the_gui.nobackingstore:
			self.buffer = self.get_window ()
		else:
			self.buffer = gtk.gdk.Pixmap (self.get_window (), width, height)
		self.clamp_offset ()
		if View.started == True:
			self.move (None, None)
		View.update (self)
	def clamp_offset (self):
		for t in range (2):
			if self.offset[t] + self.screensize[t] > self.tiles[t] * screenzoom:
				self.offset[t] = self.tiles[t] * screenzoom - self.screensize[t]
			if self.offset[t] < 0:
				self.offset[t] = 0
	def expose (self, widget, e):
		if the_gui.nobackingstore:
			self.update ()
		else:
			self.get_window ().draw_drawable (View.gc, self.buffer, e.area[0], e.area[1], e.area[0], e.area[1], e.area[2], e.area[3])
	def draw_tile (self, screenpos, worldpos, screen_lines):
		b = self.find_tile (worldpos)
		tiles = data.get_tiles (b[0])
		if tiles != None:
			w, h = tiles.get_size ()
			if b[1] * screenzoom >= w or b[2] * screenzoom >= h:
				self.buffer.draw_rectangle (View.invalidgc, True, screenpos[0], screenpos[1], screenzoom, screenzoom)
			else:
				self.buffer.draw_drawable (View.gc, tiles, b[1] * screenzoom, b[2] * screenzoom, screenpos[0], screenpos[1], screenzoom, screenzoom)
		else:
			self.buffer.draw_rectangle (View.invalidgc, True, screenpos[0], screenpos[1], screenzoom, screenzoom)
		if worldpos[1] % 8 == 0:
			self.buffer.draw_line (View.bordergc, screenpos[0], screenpos[1], screenpos[0] + screenzoom - 1, screenpos[1])
		if worldpos[0] % 12 == 0:
			self.buffer.draw_line (View.bordergc, screenpos[0], screenpos[1], screenpos[0], screenpos[1] + screenzoom - 1)
		if screen_lines and screenzoom >= 10:
			if worldpos[1] % 8 != 0:
				self.buffer.draw_line (View.gridgc, screenpos[0], screenpos[1], screenpos[0] + screenzoom - 1, screenpos[1])
			if worldpos[0] % 12 != 0:
				self.buffer.draw_line (View.gridgc, screenpos[0], screenpos[1] + 1, screenpos[0], screenpos[1] + screenzoom - 1)
	def draw_tile_hard (self, screenpos, worldpos):
		n = (worldpos[1] / 8) * 32 + (worldpos[0] / 12) + 1
		if n not in data.world.map:
			return
		h = data.world.map[n].hard
		if h != '':
			tiles = data.get_hard_tiles (h)
			if tiles:
				self.buffer.draw_pixbuf (View.gc, tiles, (worldpos[0] % 12) * screenzoom, (worldpos[1] % 8) * screenzoom, screenpos[0], screenpos[1], screenzoom, screenzoom)
			return
		b = self.find_tile (worldpos)
		if b[0] >= 0:
			tiles = data.get_hard_tiles (b[0])
			w, h = tiles.get_width (), tiles.get_height ()
			if b[1] * screenzoom >= w or b[2] * screenzoom >= h:
				return
			self.buffer.draw_pixbuf (None, tiles, b[1] * screenzoom, b[2] * screenzoom, screenpos[0], screenpos[1], screenzoom, screenzoom)
	def make_pixbuf50 (self, pb, newsize):	# TODO: scale to fit window.
		size = [pb.get_width (), pb.get_height ()]
		if size[0] <= newsize and size[1] <= newsize:
			pass
		elif size[0] > size[1]:
			size[1] = (size[1] * newsize) / size[0]
			size[0] = newsize
		else:
			size[0] = (size[0] * newsize) / size[1]
			size[1] = newsize
		return pb.scale_simple (size[0], size[1], gtk.gdk.INTERP_NEAREST)
	def draw_tiles (self, which):
		origin = [x / screenzoom for x in self.offset]
		offset = [x % screenzoom for x in self.offset]
		maps = set ()
		# Fill maps with all maps from which sprites should be drawn.
		for y in range (origin[1] / 8, (origin[1] + self.screensize[1] / screenzoom) / 8 + 1):
			if y >= 24:
				break
			for x in range (origin[0] / 12, (origin[0] + self.screensize[0] / screenzoom) / 12 + 1):
				if x >= 32:
					break
				maps.add (y * 32 + x + 1)
		# Draw tiles.
		for y in range (origin[1], origin[1] + self.screensize[1] / screenzoom + 2):
			for x in range (origin[0], origin[0] + self.screensize[0] / screenzoom + 2):
				if (x < 0 or x >= self.tiles[0]) or (y < 0 or y >= self.tiles[1]):
					self.buffer.draw_rectangle (self.emptygc, True, (x - origin[0]) * screenzoom, (y - origin[1]) * screenzoom, screenzoom, screenzoom)
					continue
				screenpos = (x - origin[0]) * screenzoom - offset[0], (y - origin[1]) * screenzoom - offset[1]
				worldpos = x, y
				self.draw_tile (screenpos, worldpos)
				check = (worldpos[0], worldpos[1], which)
				if check in select.data:
					if check == select.start:
						self.buffer.draw_rectangle (self.noshowgc, False, screenpos[0] + 1, screenpos[1] + 1, screenzoom - 2, screenzoom - 2)
					else:
						self.buffer.draw_rectangle (self.selectgc, False, screenpos[0] + 1, screenpos[1] + 1, screenzoom - 2, screenzoom - 2)
		return maps
	def update (self):
		for c in View.components:
			if c.buffer == None:
				continue
			c.update ()
	def tileselect (self, x, y, clear, type):
		if clear:
			select.clear ()
		self.selecting = True
		select.start = (x, y, type)
		select.toggle ((x, y), type)
		# This is called from button_on, not move, so it's acceptable to be a bit slow.
		View.update (self)
	def button_off (self, widget, e):
		if e.button == 1:
			self.selecting = False
		if e.button == 3:
			self.panning = False
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		pos = int (ex), int (ey)
		diff = [(pos[x] - self.pointer_pos[x]) * 50 / screenzoom for x in range (2)]
		self.pointer_pos = pos
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
			self.clamp_offset ()
			update_maps ()
		self.update ()
	def pos_from_event (self, e):
		return [(self.offset[x] + int (e[x])) / screenzoom for x in range (2)]
	def select_tiles (self, tile, which):
		if self.pointer_tile == tile:
			return
		def sort (ref, a, b):
			'Sort coordinates a and b with respect to a reference point; used for detrmining the effect of a pointer move. Return value is usable in range (), so the second value is one higher than the maximum.'
			if (a <= ref and b >= ref) or (a >= ref and b <= ref):
				if a < b:
					return a, b + 1
				return b, a + 1
			if a < ref:
				if a < b:
					return a, b
				return b, a
			if a < b:
				return a + 1, b + 1
			return b + 1, a + 1
		if self.pointer_tile[0] != tile[0]:
			# adjust horizontal size of selection.
			for x in range (*sort (select.start[0], tile[0], self.pointer_tile[0])):
				if x == select.start[0]:
					continue
				# The other axis is not yet adjusted, so use the old coordinate (tile), not the new one (self.pointer_tile).
				for y in range (*sort (select.start[1], select.start[1], tile[1])):
					select.toggle ((x, y), which)
		if self.pointer_tile[1] != tile[1]:
			# adjust vertical size of selection.
			for y in range (*sort (select.start[1], tile[1], self.pointer_tile[1])):
				if y == select.start[1]:
					continue
				# The other axis is already adjusted, so use the new coordinate (self.pointer_tile), not the old one (tile).
				for x in range (*sort (select.start[0], select.start[0], self.pointer_tile[0])):
					select.toggle ((x, y), which)
	def find_tile (self, pos, which):
		if which == 0:
			return viewmap.find_tile (pos)
		else:
			return viewtiles.find_tile (pos)
	def draw_seq (self, pos, pixbuf):
		dpos = [pos[t] * self.tilesize for t in range (2)]
		if pixbuf == None:
			self.buffer.draw_rectangle (self.invalidgc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
		else:
			self.buffer.draw_rectangle (self.whitegc, True, dpos[0], dpos[1], self.tilesize, self.tilesize)
			self.buffer.draw_pixbuf (None, self.make_pixbuf50 (pixbuf, self.tilesize), 0, 0, dpos[0], dpos[1])
	def key_global (self, key, ctrl, shift):
		if ctrl and not shift and key == gtk.keysyms.q:	# Quit.
			the_gui (False)
		elif not ctrl and not shift and key == gtk.keysyms.Escape: # Cancel operation.
			the_gui.setmap = True
		else:
			return False
		return True
	def key_seq (self, key, ctrl, shift):
		if not ctrl and not shift and key == gtk.keysyms.t: # set touch sequence.
			for s in spriteselect:
				if s[1]:
					continue
				s[0].touch_seq = self.get_selected_sequence ()
			the_gui.setmap = True
		else:
			return False
		return True
	def key_collection (self, key, ctrl, shift):
		if not ctrl and not shift and key == gtk.keysyms.a: # set base attack.
			for s in spriteselect:
				if s[1]:
					continue
				s[0].base_attack = self.get_selected_collection ()
			the_gui.setmap = True
		elif not ctrl and not shift and key == gtk.keysyms.w: # set base walk.
			for s in spriteselect:
				if s[1]:
					continue
				s[0].base_walk = self.get_selected_collection ()
			the_gui.setmap = True
		elif not ctrl and not shift and key == gtk.keysyms.d: # set base death.
			for s in spriteselect:
				if s[1]:
					continue
				s[0].base_death = self.get_selected_collection ()
			the_gui.setmap = True
		elif not ctrl and not shift and key == gtk.keysyms.i: # set base idle.
			for s in spriteselect:
				if s[1]:
					continue
				s[0].base_idle = self.get_selected_collection ()
			the_gui.setmap = True
		else:
			return False
		return True
	def key_home (self, key, ctrl, shift):
		if not ctrl and not shift and key == gtk.keysyms.Home:	# center map
			s = (12, 8)
			# Find screen where center is.
			m = self.get_pointed_map ()
			self.offset = [(m[t] * s[t] + s[t] / 2) * screenzoom - self.screensize[t] / 2 for t in range (2)]
			self.clamp_offset ()
			self.update ()
			return True
		return False
	def key_tiles (self, key, ctrl, shift):
		global copystart
		if self.key_home (key, ctrl, shift):
			pass
		elif key == gtk.keysyms.t:		# return to map
			the_gui.setmap = True
		elif key == gtk.keysyms.y:		# yank tiles into buffer
			copybuffer.clear ()
			for i in select.data:
				s = View.find_tile (self, i, i[2])
				copybuffer.add ((i[0], i[1], i[2], s[0], s[1], s[2]))
			copystart = select.start
			the_gui.setmap = True
		elif ctrl and not shift and key == gtk.keysyms.Prior:		# Zoom in.
			viewmap.zoom_screen (True)
		elif ctrl and not shift and key == gtk.keysyms.Next:		# Zoom out.
			viewmap.zoom_screen (False)
		elif ctrl and not shift and key == gtk.keysyms.Home:		# Restore zoom.
			viewmap.zoom_screen (50)
		else:
			return False
		return True
	def get_offsets (self, x0, y0, frames):
		if x0 + frames - 1 <= self.width:
			off = x0				# Start frames at x0 if it fits.
		else:
			off = max (0, self.width - (frames - 1))	# Otherwise, start as high as possible.
		rows = (off + frames - 1 + self.width - 1) / self.width	# Number of rows for frame list.
		if y0 + rows >= self.height:
			yoff = y0 - rows - 1
		else:
			yoff = y0
		return off, yoff
	def get_info (self, list, get_seq):
		self.pointer_tile = [self.pointer_pos[x] / self.tilesize for x in range (2)]	# Position of pointer in tiles.
		x0, y0 = self.selected_seq			# Position of seq that was clicked.
		pos0 = y0 * self.width + x0			# Position in list of selected seq.
		frames = get_seq (list[pos0]).frames		# Number of frames in selected seq.
		off, yoff = self.get_offsets (x0, y0, len (frames))
		lx = self.pointer_tile[0]
		ly = self.pointer_tile[1] - yoff - 1
		lframe = ly * self.width + lx + 1 - off
		if self.pointer_tile[0] == x0 and self.pointer_tile[1] == y0:
			frame = 1
		elif lframe >= 0 and lframe < len (frames):
			frame = lframe
		else:
			# Selected nothing; return to selection.
			self.selected_seq = None
			return None, None, None, None
		return list[y0 * self.width + x0], frame, x0, y0
# }}}

class ViewMap (View): # {{{
	def __init__ (self):
		View.__init__ (self)
		self.mapsource = None		# Source for a newly created map (for copying).
		self.moveinfo = None		# Information for what to do with pointer move events.
		self.pointer_tile = (0, 0)	# Tile that the pointer is currently pointing it, in world coordinates. That is: pointer_pos / 50.
		self.waitselect = None		# Selection to use if button is released without moving.
		self.tiles = (12 * 32, 8 * 24)	# Total number of tiles on map.
		self.current_selection = 0	# Index of "current" sprite in selection.
		self.set_size_request (50 * 12, 50 * 8)
		self.update_handle = None
	def find_tile (self, worldpos):
		n = (worldpos[1] / 8) * 32 + (worldpos[0] / 12) + 1
		if n in data.world.map:
			return data.world.map[n].tiles[worldpos[1] % 8][worldpos[0] % 12]
		return [-1, -1, -1]
	def draw_tile (self, screenpos, worldpos):
		View.draw_tile (self, screenpos, worldpos, True)
		if not self.selecting:
			if self.moveinfo is None and (worldpos[0] - self.pointer_tile[0] + select.start[0], worldpos[1] - self.pointer_tile[1] + select.start[1], select.start[2]) in select.data:
				self.buffer.draw_rectangle (self.pastegc, False, screenpos[0] + 1, screenpos[1] + 1, screenzoom - 2, screenzoom - 2)
	def update (self):
		if self.update_handle is not None:
			return
		self.update_handle = glib.idle_add (self.do_update)
	def do_update (self):
		self.update_handle = None
		if self.buffer is None:
			return False
		maps = View.draw_tiles (self, 0)
		# Draw sprites.
		lst = []
		# First get a list of sprites to draw, with their que so they can be drawn in the right order.
		# Check only maps in the viewport.
		for s in maps:
			if s not in data.world.map:
				# This map doesn't exist, so doesn't have sprites.
				continue
			# Add all sprites from this map to the list.
			for sp in data.world.map[s].sprite:
				if visibility (sp.layer) < 0:
					# Ignore invisible foreground sprites.
					continue
				pos = (sp.x - self.offset[0] * 50 / screenzoom, sp.y - self.offset[1] * 50 / screenzoom)
				seq = data.seq.find_seq (sp.seq)
				is_selected = (sp, False) in spriteselect
				item = (pos, sp, seq, is_selected)
				if item not in lst:
					lst.append (item)
		# Add warp targets.
		for s in maps:
			if s not in warptargets:
				continue
			for sp in warptargets[s]:
				if visibility (sp.layer) < 0:
					# Ignore invisible foreground sprites.
					continue
				is_selected = (sp, True) in spriteselect
				lst += (((None, 0), sp, None, is_selected),)
		# Add all selected sprites and warp targets in any case.
		for sp in spriteselect:
			if sp[1]:
				item = ((None, 0), sp[0], None, True)
			else:
				pos = (sp[0].x - self.offset[0] * 50 / screenzoom, sp[0].y - self.offset[1] * 50 / screenzoom)
				seq = data.seq.find_seq (sp[0].seq)
				item = (pos, sp[0], seq, True)
			if item not in lst:
				lst.append (item)
		# Sort the list by y coordinate, taking depth que into account.
		lst.sort (key = lambda x: x[0][1] - x[1].que)
		# Now draw them all in the right order. First the pixbufs, then hardness, then wireframe information.
		for s in lst:
			if s[2] is None or s[0][0] == None:
				# There is no seq, or this is a warp target.
				continue
			# Visibility -1 is not present; visibility is 0, 1 or 2.
			alpha = [0, 0x80, 0xff][visibility (s[1].layer)]
			if alpha == 0:
				continue
			(x, y), (left, top, right, bottom), box = data.seq.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
			box = [x * screenzoom / 50 for x in box]
			w = (right - left) * screenzoom / 50
			h = (bottom - top) * screenzoom / 50
			if w > 0 and h > 0 and left * screenzoom / 50 > -w and top * screenzoom / 50 > -h and left * screenzoom / 50 < self.screensize[0] and top * screenzoom / 50 < self.screensize[1]:
				# Draw the pixbuf.
				pb = data.get_seq (s[2], s[1].frame)
				if not pb:
					continue
				pb = pb.subpixbuf (box[0], box[1], box[2] - box[0], box[3] - box[1])
				pb = pb.scale_simple (w, h, gtk.gdk.INTERP_NEAREST)
				if alpha < 0xff:
					newpb = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, True, 8, w, h)
					newpb.fill (0x00000000)
					pb.composite (newpb, 0, 0, w, h, 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, alpha)
					pb = newpb
				self.buffer.draw_pixbuf (None, pb, 0, 0, left * screenzoom / 50, top * screenzoom / 50)
		for s in lst:
			# Draw per-sprite tile hardness
			if s[2] is None or s[0][0] == None or not s[1].use_hard:
				# There is no seq, or this is a warp target, or we don't want sprite hardness.
				continue
			hard = data.get_hard_seq (s[2], s[1].frame)
			if not hard:
				continue
			(x, y), (left, top, right, bottom), box = data.seq.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
			box = [x * screenzoom / 50 for x in box]
			w = (right - left) * screenzoom / 50
			h = (bottom - top) * screenzoom / 50
			hard = hard.subpixbuf (box[0], box[1], box[2] - box[0], box[3] - box[1])
			hard = hard.scale_simple (w, h, gtk.gdk.INTERP_NEAREST)
			newpb = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, True, 8, w, h)
			newpb.fill (0x00000000)
			hard.composite (newpb, 0, 0, w, h, 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 0x80)
			self.buffer.draw_pixbuf (None, newpb, 0, 0, left * screenzoom / 50, top * screenzoom / 50)
		# Tile hardness.
		origin = [x / screenzoom for x in self.offset]
		offset = [x % screenzoom for x in self.offset]
		for y in range (offset[1] / screenzoom, (self.screensize[1] + offset[1] + screenzoom) / screenzoom):
			for x in range (offset[0] / screenzoom, (self.screensize[0] + offset[0] + screenzoom) / screenzoom):
				if (origin[0] + x < 0 or origin[0] + x >= self.tiles[0]) or (origin[1] + y < 0 or origin[1] + y >= self.tiles[1]):
					continue
				self.draw_tile_hard ((x * screenzoom - offset[0], y * screenzoom - offset[1]), (origin[0] + x, origin[1] + y))
		# Sprite hardness.
		for spr in lst:
			if spr[2] is None:
				continue
			vis = visibility (spr[1].layer)
			if spr[0][0] == None:
				# This is a warp target.
				continue
			if not spr[1].hard:
				continue
			if spr[1].warp is not None:
				gc = self.warpbggc if vis < 2 else self.warpgc
			else:
				gc = self.bggc if vis < 2 else self.hardgc
			(x, y), (left, top, right, bottom), box = data.seq.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
			w = (right - left) * screenzoom / 50
			h = (bottom - top) * screenzoom / 50
			if w > 0 and h > 0 and left >= -w and top >= -h and left < self.screensize[0] and top < self.screensize[1]:
				self.buffer.draw_rectangle (gc, False, (x + spr[2].frames[spr[1].frame].hardbox[0]) * screenzoom / 50, (y + spr[2].frames[spr[1].frame].hardbox[1]) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[2] - spr[2].frames[spr[1].frame].hardbox[0] - 1) * screenzoom / 50, (spr[2].frames[spr[1].frame].hardbox[3] - spr[2].frames[spr[1].frame].hardbox[1] - 1) * screenzoom / 50)
		# Wireframe information.
		def draw_target (n, x, y, active, gc):
			x += ((n - 1) % 32) * 12 * 50 - 20
			y += ((n - 1) / 32) * 8 * 50
			x = x * screenzoom / 50
			y = y * screenzoom / 50
			x -= self.offset[0]
			y -= self.offset[1]
			s = 20 * screenzoom / 50
			a = 15 * screenzoom / 50
			if x >= -s and y >= -s and x - s < self.screensize[0] and y - s < self.screensize[1]:
				if active:
					self.buffer.draw_line (gc, x - s, y, x + s, y)
					self.buffer.draw_line (gc, x, y - s, x, y + s)
				self.buffer.draw_arc (gc, False, x - a, y - a, a * 2, a * 2, 0, 64 * 360)
		for spr in lst:
			if spr[0][0] is not None and spr[2] is None:
				continue
			if spr[3]:
				continue
			vis = visibility (spr[1].layer)
			if spr[0][0] != None:
				# This is a sprite, not a warp target.
				if spr[1].layer == the_gui.active_layer:
					(x, y), (left, top, right, bottom), box = data.seq.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
					w = (right - left) * screenzoom / 50
					h = (bottom - top) * screenzoom / 50
					if w > 0 and h > 0 and left >= -w and top >= -h and left < self.screensize[0] and top < self.screensize[1]:
					# Hotspot.
						self.buffer.draw_line (self.bggc if vis < 2 else self.noselectgc, (x - 10) * screenzoom / 50, y * screenzoom / 50, (x + 10) * screenzoom / 50, y * screenzoom / 50)
						self.buffer.draw_line (self.bggc if vis < 2 else self.noselectgc, x * screenzoom / 50, (y - 10) * screenzoom / 50, x * screenzoom / 50, (y + 10) * screenzoom / 50)
			else:
				# This is a warp target.
				n, x, y = spr[1].warp
				draw_target (n, x, y, spr[1].layer == the_gui.active_layer, self.bggc if vis < 2 else self.noselectgc)
		# No matter what is visible, always show selected sprite's stuff on top.
		for spr in lst:
			if not spr[3]:
				continue
			if spr[0][0] != None:
				# This is a sprite, not a warp target.
				(x, y), (left, top, right, bottom), box = data.seq.get_box (spr[1].size, spr[0], spr[2].frames[spr[1].frame], (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
				w = (right - left) * screenzoom / 50
				h = (bottom - top) * screenzoom / 50
				if w > 0 and h > 0 and left * screenzoom / 50 >= -w and top * screenzoom / 50 >= -h and left * screenzoom / 50 < self.screensize[0] and top * screenzoom / 50 < self.screensize[1]:
					# Que.
					self.buffer.draw_line (self.noshowgc, (x - 40) * screenzoom / 50, (y - spr[1].que) * screenzoom / 50, (x + 40) * screenzoom / 50, (y - spr[1].que) * screenzoom / 50)
					# Hotspot
					self.buffer.draw_line (self.selectgc, (x - 10) * screenzoom / 50, y * screenzoom / 50, (x + 10) * screenzoom / 50, y * screenzoom / 50)
					self.buffer.draw_line (self.selectgc, x * screenzoom / 50, (y - 10) * screenzoom / 50, x * screenzoom / 50, (y + 10) * screenzoom / 50)
			else:
				# This is a warp target.
				n, x, y = spr[1].warp
				draw_target (n, x, y, True, self.selectgc)
		# Finally, draw a line if we're resizing.
		if self.moveinfo != None and self.moveinfo[0] == 'resize':
			avg = [self.moveinfo[1][0][t] - self.offset[t] for t in range (2)]
			self.buffer.draw_line (self.noshowgc, avg[0], avg[1], self.pointer_pos[0], self.pointer_pos[1])
		# And a box if we're selecting.
		if self.moveinfo != None and self.moveinfo[0] == 'spriteselect' and self.moveinfo[1][0][0] != self.moveinfo[1][1][0] and self.moveinfo[1][0][1] != self.moveinfo[1][1][1]:
			x = [(self.moveinfo[1][t][0] - self.offset[0]) * screenzoom / 50 for t in range (2)]
			y = [(self.moveinfo[1][t][1] - self.offset[1]) * screenzoom / 50 for t in range (2)]
			x.sort ()
			y.sort ()
			self.buffer.draw_rectangle (self.selectgc, False, x[0], y[0], x[1] - x[0], y[1] - y[0])
		# And a hooked line if we're making a path.
		if self.moveinfo is not None and self.moveinfo[0] == 'path':
			tileset, origin, is_horizontal = self.moveinfo[1]
			origin = tuple ([origin[t] * screenzoom - self.offset[t] for t in range (2)])
			ap = [(self.pointer_pos[t] + self.offset[t]) * 50 / screenzoom for t in range (2)]
			pos = tuple ([(ap[t] + 25) / 50 * screenzoom - self.offset[t] for t in range (2)])
			if is_horizontal:
				# First horizontal, then vertical.
				self.buffer.draw_lines (self.pathgc, (origin, (pos[0], origin[1]), pos))
			else:
				# First vertical, then horizontal.
				self.buffer.draw_lines (self.pathgc, (origin, (origin[0], pos[1]), pos))
		if not the_gui.nobackingstore:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
		return False
	def make_global (self, map, pos):
		s = (12, 8)
		spos = ((map - 1) % 32, (map - 1) / 32)
		return [pos[x] + s[x] * spos[x] * 50 for x in range (2)]
	def goto (self, pos):
		self.offset = [pos[x] * screenzoom / 50 - self.screensize[x] / 2 for x in range (2)]
		self.clamp_offset ()
		self.update ()
		viewworld.update ()
	def get_pointed_map (self, pos = None):
		if pos is None:
			pos = self.pointer_pos
		ret = [(self.offset[x] + pos[x]) / ((12, 8)[x] * screenzoom) for x in range (2)]
		return (ret[0], ret[1], ret[0] + ret[1] * 32 + 1)
	def get_current_map (self):
		return self.get_pointed_map ([self.screensize[t] / 2 for t in range (2)])
	def make_cancel (self):
		ret = [self.offset, [], screenzoom]
		for s in spriteselect:
			spr = s[0]
			if s[1]:
				ret[1] += (spr.warp,)
			else:
				ret[1] += (((spr.x, spr.y), spr.que, spr.size, (spr.left, spr.top, spr.right, spr.bottom)),)
		return ret
	def zoom_screen (self, zoom_in):
		global screenzoom
		mid = [(self.offset[x] + self.screensize[x] / 2) * 50 / screenzoom for x in range (2)]
		if not isinstance (zoom_in, bool):
			screenzoom = int (zoom_in)
		elif zoom_in:
			if screenzoom < 10:
				screenzoom += 1
			else:
				screenzoom += 10
		elif screenzoom > 10:
			screenzoom -= 10
		elif screenzoom > 1:
			screenzoom -= 1
		self.offset = [mid[x] * screenzoom / 50 - self.screensize[x] / 2 for x in range (2)]
		data.set_scale (screenzoom)
		self.clamp_offset ()
		update_maps ()
		the_gui.statusbar = 'Screen zoom changed'
		viewtiles.update ()
	def finish_move (self):
		# Panning is done with pointer button 2, and should not respond to keys.
		if self.moveinfo is None or self.moveinfo[0] == 'pan':
			return
		if self.moveinfo[0] == 'path':
			def put_tile (pos, tile):
				n = (pos[1] / 8) * 32 + (pos[0] / 12) + 1
				if n not in data.world.map:
					return
				data.world.map[n].tiles[pos[1] % 8][pos[0] % 12] = tile
			def put_corner (pos, tileset, tiles):
				x, y = pos
				tx, ty = tiles
				for yy in range (2):
					for xx in range (2):
						put_tile ((x - 1 + xx, y - 1 + yy), (tileset, tx + xx, ty + yy))
			# Put the tiles on the path.
			tileset, origin, is_horizontal = self.moveinfo[1]
			ap = [((self.pointer_pos[t] + self.offset[t]) * 50 / screenzoom + 25) / 50 for t in range (2)]
			# There are three seqments, all of which may be length 0: the first leg, the corner, and the second leg.
			if is_horizontal:
				hleg = [origin, ap[0] - origin[0]]
				vleg = [(ap[0], origin[1]), ap[1] - origin[1]]
				if vleg[1] == 0:
					# No corner and no vleg.
					vleg = None
					if hleg[1] == 0:
						hleg = None
					hoffset = 0
				else:
					if hleg[1] == 0:
						hleg = None
						if vleg[1] < 0:
							voffset = 1
						else:
							voffset = 0
					else:
						put_corner (vleg[0], tileset, (((0, 4), (6, 0)), ((8, 2), (4, 0)))[hleg[1] > 0][vleg[1] > 0])
						if abs (vleg[1]) == 1:
							# No vleg.
							vleg = None
						else:
							if vleg[1] < 0:
								# Going up.
								voffset = 1
								vleg[0] = (vleg[0][0], vleg[0][1] - 1)
								vleg[1] += 1
							else:
								# Going down.
								voffset = 0
								vleg[0] = (vleg[0][0], vleg[0][1] + 1)
								vleg[1] -= 1
						if abs (hleg[1]) == 1:
							# No hleg.
							hleg = None
						else:
							if hleg[1] < 0:
								# Going left.
								hleg[1] += 1
							else:
								# Going right.
								hleg[1] -= 1
							hoffset = hleg[1]
			else:
				vleg = [origin, ap[1] - origin[1]]
				hleg = [(origin[0], ap[1]), ap[0] - origin[0]]
				if hleg[1] == 0:
					# No corner and no hleg.
					hleg = None
					if vleg[0] == 0:
						vleg = None
					voffset = 0
				else:
					if vleg[1] == 0:
						vleg = None
						if hleg[1] < 0:
							hoffset = 1
						else:
							hoffset = 0
					else:
						put_corner (hleg[0], tileset, (((8, 0), (0, 0)), ((4, 4), (6, 2)))[vleg[1] > 0][hleg[1] > 0])
						if abs (hleg[1]) == 1:
							# No hleg.
							hleg = None
						else:
							if hleg[1] < 0:
								# Going left.
								hoffset = 1
								hleg[0] = (hleg[0][0] - 1, hleg[0][1])
								hleg[1] += 1
							else:
								# Going right.
								hoffset = 0
								hleg[0] = (hleg[0][0] + 1, hleg[0][1])
								hleg[1] -= 1
						if abs (vleg[1]) == 1:
							# No vleg.
							vleg = None
						else:
							if vleg[1] < 0:
								# Going up.
								vleg[1] += 1
							else:
								# Going down.
								vleg[1] -= 1
							voffset = vleg[1]
			if hleg is not None:
				if hleg[1] < 0:
					# Going left.
					for t in range (-hleg[1]):
						put_tile ((hleg[0][0] - t - 1, hleg[0][1] - 1), [tileset, 2 + (t + hoffset) % 2, 4])
						put_tile ((hleg[0][0] - t - 1, hleg[0][1]), [tileset, 2 + (t + hoffset) % 2, 5])
				else:
					# Going right.
					for t in range (hleg[1]):
						put_tile ((hleg[0][0] + t, hleg[0][1] - 1), [tileset, 2 + (t + hoffset) % 2, 0])
						put_tile ((hleg[0][0] + t, hleg[0][1]), [tileset, 2 + (t + hoffset) % 2, 1])
			if vleg is not None:
				if vleg[1] < 0:
					# Going up.
					for t in range (-vleg[1]):
						put_tile ((vleg[0][0] - 1, vleg[0][1] - t - 1), [tileset, 0, 2 + (t + voffset) % 2])
						put_tile ((vleg[0][0], vleg[0][1] - t - 1), [tileset, 1, 2 + (t + voffset) % 2])
				else:
					# Going down.
					for t in range (vleg[1]):
						put_tile ((vleg[0][0] - 1, vleg[0][1] + t), [tileset, 4, 2 + (t + voffset) % 2])
						put_tile ((vleg[0][0], vleg[0][1] + t), [tileset, 5, 2 + (t + voffset) % 2])
			# Auto-restart path from new start point
			self.moveinfo = 'path', (tileset, ap, not is_horizontal), self.moveinfo[2]
			the_gui.statusbar = 'Added path segment'
			return
		self.moveinfo = None
		the_gui.statusbar = 'Operation finished'
	def abort_move (self):
		if self.moveinfo is None:
			return
		self.offset = self.moveinfo[2][0]
		screenzoom = self.moveinfo[2][2]
		data.set_scale (screenzoom)
		self.clamp_offset ()
		for s in range (len (spriteselect)):
			spriteselect[s][0].unregister ()
			spr = spriteselect[s][0]
			if spriteselect[s][1]:
				spr.warp = self.moveinfo[2][1][s]
			else:
				spr.x, spr.y = self.moveinfo[2][1][s][0]
				spr.que = self.moveinfo[2][1][s][1]
				spr.size = self.moveinfo[2][1][s][2]
				spr.left, spr.top, spr.right, spr.bottom = self.moveinfo[2][1][s][3]
			spriteselect[s][0].register ()
		update_editgui ()
		self.moveinfo = None
		the_gui.statusbar = 'Operation cancelled'
	def key_numpad (self, key, ap = None):
		if key == gtk.keysyms.KP_0 or key == gtk.keysyms.KP_Insert:	# new sprite from sequence
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewseq.update ()
			the_gui.setseq = True
		elif key == gtk.keysyms.KP_1 or key == gtk.keysyms.KP_End:		# new sprite with direction 1
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (1)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_2 or key == gtk.keysyms.KP_Down:	# new sprite with direction 2
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (2)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_3 or key == gtk.keysyms.KP_Next:	# new sprite with direction 3
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (3)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_4 or key == gtk.keysyms.KP_Left:	# new sprite with direction 4
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (4)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_5 or key == gtk.keysyms.KP_Begin:	# new sprite with direction die
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction ('die')
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_6 or key == gtk.keysyms.KP_Right:	# new sprite with direction 6
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (6)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_7 or key == gtk.keysyms.KP_Home:	# new sprite with direction 7
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (7)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_8 or key == gtk.keysyms.KP_Up:		# new sprite with direction 8
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (8)
			the_gui.setcollection = True
		elif key == gtk.keysyms.KP_9 or key == gtk.keysyms.KP_Prior:	# new sprite with direction 9
			select.clear ()
			if ap is not None:
				self.newinfo = ap
			viewcollection.direction (9)
			the_gui.setcollection = True
		else:
			return False
		return True
	def keypress (self, widget, e):
		global copystart
		p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
		ap = [p[t] * 50 / screenzoom for t in range (2)]
		sx = ap[0] / (12 * 50)
		sy = ap[1] / (8 * 50)
		ox = ap[0] - sx * 12 * 50
		oy = ap[1] - sy * 8 * 50
		n = sy * 32 + sx + 1
		self.selecting = False
		ctrl = e.state & gtk.gdk.CONTROL_MASK
		shift = e.state & gtk.gdk.SHIFT_MASK
		key = e.keyval
		# File actions.
		if ctrl and not shift and key == gtk.keysyms.o:		# Open.
			show_open ()
		elif ctrl and not shift and key == gtk.keysyms.s:	# Save.
			save ()
		elif ctrl and shift and key == gtk.keysyms.S:		# Save as.
			show_save_as ()
		elif ctrl and not shift and key == gtk.keysyms.q:	# Quit.
			the_gui (False)
		# DMod actions.
		elif ctrl and not shift and key == gtk.keysyms.b:	# Build.
			the_gui.statusbar = 'Syncing for build'
			os.system (the_gui.sync)
			sync ()
			the_gui.statusbar = 'Building DMod'
			data.build ()
			the_gui.statusbar = 'Built DMod'
		elif ctrl and not shift and key == gtk.keysyms.p:	# Play.
			the_gui.statusbar = 'Syncing for playtest'
			sync ()
			n = (ap[1] / (8 * 50)) * 32 + (ap[0] / (12 * 50)) + 1
			play (n, ap[0] % (12 * 50) + 20, ap[1] % (8 * 50))
		# Edit actions (select + view).
		elif ctrl and not shift and key == gtk.keysyms.c:	# Copy.
			self.copy ()
			the_gui.statusbar = 'Copied tiles to buffer'
		elif ctrl and not shift and key == gtk.keysyms.v:	# Paste.
			self.paste ([(self.pointer_pos[x] + self.offset[x]) / screenzoom for x in range (2)])
			the_gui.statusbar = 'Pasted tiles from buffer'
		elif not ctrl and not shift and key == gtk.keysyms.Escape: # Abort current action
			# Panning is done with pointer button 2, and should not respond to keys.
			if self.moveinfo is not None and self.moveinfo[0] != 'pan':
				# Reset change.
				self.abort_move ()
		elif not ctrl and not shift and key == gtk.keysyms.Return: # Confirm operation.
			self.finish_move ()
		elif ctrl and shift and key == gtk.keysyms.A:
			deselect_all ()
			the_gui.statusbar = 'Deselected all sprites'
		elif ctrl and not shift and key == gtk.keysyms.a:
			select_all ()
			the_gui.statusbar = 'Selected all sprites'
		elif ctrl and not shift and key == gtk.keysyms.i:
			select_invert ()
			the_gui.statusbar = 'Inverted sprite selection'
		elif not ctrl and not shift and key == gtk.keysyms.j:
			jump ()
			the_gui.statusbar = 'Jumped to sprite selection'
		elif not ctrl and not shift and key == gtk.keysyms.n:
			jump_next ()
			the_gui.statusbar = 'Jumped to next selected sprite'
		elif not ctrl and not shift and key == gtk.keysyms.Left:
			self.handle_cursor ((-1, 0))
		elif not ctrl and not shift and key == gtk.keysyms.Up:
			self.handle_cursor ((0, -1))
		elif not ctrl and not shift and key == gtk.keysyms.Right:
			self.handle_cursor ((1, 0))
		elif not ctrl and not shift and key == gtk.keysyms.Down:
			self.handle_cursor ((0, 1))
		elif not ctrl and not shift and key == gtk.keysyms.equal:	# Map select.
			self.moveinfo = None
			viewworld.update ()
			the_gui.setworld = True
			the_gui.statusbar = 'Select area to view'
		elif ctrl and not shift and key == gtk.keysyms.Prior:		# Zoom in.
			self.zoom_screen (True)
		elif ctrl and not shift and key == gtk.keysyms.Next:		# Zoom out.
			self.zoom_screen (False)
		elif ctrl and not shift and key == gtk.keysyms.Home:		# Restore zoom.
			self.zoom_screen (50)
		elif not ctrl and not shift and key == gtk.keysyms.Home:	# Center map.
			s = (12, 8)
			self.goto ([(self.pointer_pos[x] + self.offset[x]) / s[x] / screenzoom * s[x] * 50 + s[x] / 2 * 50 for x in range (2)])
			the_gui.statusbar = 'Map centered on screen'
		# Sprite actions.
		elif not ctrl and not shift and key == gtk.keysyms.e:		# Edit script(s).
			edit_sprite_scripts ()
			the_gui.statusbar = 'Editing sprite scripts'
		elif not shift and key == gtk.keysyms._0:
			self.layerkey (0, ctrl)
		elif not shift and key == gtk.keysyms._1:
			self.layerkey (1, ctrl)
		elif not shift and key == gtk.keysyms._2:
			self.layerkey (2, ctrl)
		elif not shift and key == gtk.keysyms._3:
			self.layerkey (3, ctrl)
		elif not shift and key == gtk.keysyms._4:
			self.layerkey (4, ctrl)
		elif not shift and key == gtk.keysyms._5:
			self.layerkey (5, ctrl)
		elif not shift and key == gtk.keysyms._6:
			self.layerkey (6, ctrl)
		elif not shift and key == gtk.keysyms._7:
			self.layerkey (7, ctrl)
		elif not shift and key == gtk.keysyms._8:
			self.layerkey (8, ctrl)
		elif not shift and key == gtk.keysyms._9:
			self.layerkey (9, ctrl)
		elif not ctrl and shift and key == gtk.keysyms.H:		# Toggle nohit
			toggle_nohit ()
		elif not ctrl and not shift and key == gtk.keysyms.m:		# move selected sprites
			self.moveinfo = 'move', None, self.make_cancel ()
			the_gui.statusbar = 'Starting move operation'
		elif not ctrl and not shift and self.key_numpad (key, ap):
			pass
		elif not ctrl and not shift and key == gtk.keysyms.s:
			if len (spriteselect) != 0:
				# Required info:
				# - average hotspot of selected sprites
				# - current distance from hotspot
				# - current size value
				avg = make_avg ()
				dist = make_dist (avg, ap)
				size = [x[0].size for x in spriteselect]
				self.moveinfo = 'resize', (avg, dist, size), self.make_cancel ()
			the_gui.statusbar = 'Starting scale operation'
		elif not ctrl and not shift and key == gtk.keysyms.p:
			tileset = viewtiles.find_tile (select.start[:2])[0]
			if select.start[2] != 1 or select.start not in select.data or tileset < 0:
				the_gui.statusbar = 'Not starting path, because no tile screen is selected'
			else:
				origin = [(ap[t] + 25) / 50 for t in range (2)]
				offset = [ap[t] - origin[t] * 50 for t in range(2)]
				is_horizontal = abs (offset[0]) > abs (offset[1])
				self.moveinfo = 'path', (tileset, origin, is_horizontal), self.make_cancel ()
				the_gui.statusbar = 'Starting path operation for tileset %d' % tileset
		elif not ctrl and not shift and key == gtk.keysyms.q:
			self.moveinfo = 'que', None, self.make_cancel ()
			the_gui.statusbar = 'Starting que move operation'
		elif ctrl and not shift and key == gtk.keysyms.l:		# Lock to pointed map
			p = viewmap.get_pointed_map ()[2]
			if p not in data.world.map:
				the_gui.statusbar = 'Not locking to nonexistent map'
			else:
				n = 0
				for s in spriteselect:
					if s[1]:
						continue
					n += 1
					s[0].unregister ()
					s[0].map = p
					s[0].register ()
				update_editgui ()
				the_gui.statusbar = 'Locked %d sprite(s) to map %d' % (n, p)
		elif ctrl and shift and key == gtk.keysyms.L:			# Unlock
			n = 0
			for s in spriteselect:
				if s[1]:
					continue
				n += 1
				s[0].unregister ()
				s[0].map = None
				s[0].register ()
			update_editgui ()
			the_gui.statusbar = 'Unlocked %d sprite(s)' % n
		elif ctrl and not shift and key == gtk.keysyms.w:		# Set warp.
			for spr in spriteselect:
				if spr[1]:
					continue
				remove_warptarget (spr[0])
				n = (ap[1] / (50 * 8)) * 32 + (ap[0] / (50 * 12)) + 1
				spr[0].warp = (n, ap[0] % (50 * 12), ap[1] % (50 * 8))
				add_warptarget (spr[0])
			update_editgui ()
			the_gui.statusbar = 'Set warp target'
		elif ctrl and shift and key == gtk.keysyms.W:			# Clear warp.
			clear_warp ()
			the_gui.statusbar = 'Cleared warp target'
		elif not ctrl and not shift and key == gtk.keysyms.w:		# Toggle select warp or object.
			toggle_warp ()
			the_gui.statusbar = 'Toggled warp target selection'
		elif not ctrl and not shift and key == gtk.keysyms.h:		# Toggle sprite hardness.
			toggle_hard ()
			the_gui.statusbar = 'Toggled sprite hardness'
		elif not ctrl and not shift and key == gtk.keysyms.Delete:	# Delete sprite(s)
			s = 0
			w = 0
			for killer in spriteselect:
				if killer[0].warp is not None:
					w += 1
				# Remove warp target in any case.
				remove_warptarget (killer[0])
				if not killer[1]:
					s += 1
					killer[0].unregister ()
					data.world.sprite.remove (killer[0])
				else:
					# Delete warp point
					killer[0].warp = None
			spriteselect[:] = []
			update_editgui ()
			the_gui.statusbar = 'Deleted %d sprite(s) and %d warp target(s)' % (s, w)
		# Ctrl+cursor: start crop
		elif ctrl and not shift and key == gtk.keysyms.Left:
			self.start_crop ()
			self.moveinfo = 'crop', (4, ap), self.make_cancel ()
		elif ctrl and not shift and key == gtk.keysyms.Up:
			self.start_crop ()
			self.moveinfo = 'crop', (8, ap), self.make_cancel ()
		elif ctrl and not shift and key == gtk.keysyms.Right:
			self.start_crop ()
			self.moveinfo = 'crop', (6, ap), self.make_cancel ()
		elif ctrl and not shift and key == gtk.keysyms.Down:
			self.start_crop ()
			self.moveinfo = 'crop', (2, ap), self.make_cancel ()
		elif not ctrl and not shift and key == gtk.keysyms.t:
			the_gui.settiles = True
		elif ctrl and not shift and key == gtk.keysyms.h:
			edit_map_hardness ()
			the_gui.statusbar = 'Editing map hardness'
		elif ctrl and not shift and key == gtk.keysyms.e:
			edit_map_script ()
			the_gui.statusbar = 'Editing map script'
		elif not ctrl and shift and key == gtk.keysyms.I:
			toggle_indoor ()
			the_gui.statusbar = 'Toggled indoor state'
		elif ctrl and not shift and key == gtk.keysyms.Insert:
			map_insert ()
		elif ctrl and not shift and key == gtk.keysyms.Delete:
			map_delete ()
		elif not ctrl and not shift and key == gtk.keysyms.y: # yank (copy) selected tiles into buffer
			self.copy ()
		elif not ctrl and not shift and key == gtk.keysyms.minus: # unselect all
			select.clear ()
		elif not ctrl and not shift and key == gtk.keysyms.f: # fill selected tiles with buffer
			if len (copybuffer) == 0:
				return
			tiles = list (copybuffer)
			min = [None, None]
			max = [None, None]
			for i in copybuffer:
				if i[2] != copystart[2]:
					continue
				for x in range (2):
					if min[x] == None or i[x] < min[x]:
						min[x] = i[x]
					if max[x] == None or i[x] > max[x]:
						max[x] = i[x]
			for i in select.data:
				# Don't try to paste into tile screens.
				if i[2] != 0:
					continue
				n = (i[1] / 8) * 32 + (i[0] / 12) + 1
				if n not in data.world.map:
					continue
				tile = None
				if min[0] == None:
					continue
				size = [max[x] - min[x] + 1 for x in range (2)]
				p = [(i[x] - select.start[x] + copystart[x]) % size[x] for x in range (2)]
				for b in copybuffer:
					if b[2] == copystart[2] and (b[0] - copystart[0]) % size[0] == p[0] and (b[1] - copystart[1]) % size[1] == p[1]:
						tile = b[3:6]
				if tile == None:
					tile = tiles[random.randrange (len (copybuffer))][3:6]
				data.world.map[n].tiles[i[1] % 8][i[0] % 12] = tile
		elif not ctrl and not shift and key == gtk.keysyms.r: # random fill tiles
			if len (copybuffer) == 0:
				return
			tiles = list (copybuffer)
			for i in select.data:
				# Don't try to paste into tile screens.
				if i[2] != 0:
					continue
				n = (i[1] / 8) * 32 + (i[0] / 12) + 1
				if n not in data.world.map:
					continue
				tile = tiles[random.randrange (len (copybuffer))][3:6]
				data.world.map[n].tiles[i[1] % 8][i[0] % 12] = tile
		else:
			return False
		self.update ()
		return True
	def layerkey (self, layer, ctrl):
		if ctrl:
			# Move all selected sprites to layer.
			for s in spriteselect:
				s[0].layer = layer
			the_gui.statusbar = 'Moved sprites to layer %d' % layer
		else:
			# Make layer active.
			the_gui.active_layer = layer
			update_editgui ()
			viewmap.update ()
			the_gui.statusbar = 'Active layer changed to %d' % layer
	def copy (self):
		global copystart
		copybuffer.clear ()
		for i in select.data:
			s = View.find_tile (self, i, i[2])
			copybuffer.add ((i[0], i[1], i[2], s[0], s[1], s[2]))
		copystart = select.start
	def paste (self, pos):
		for t in select.compute ():
			target = [pos[x] + t[x] for x in range (2)]
			n = (target[1] / 8) * 32 + (target[0] / 12) + 1
			if n not in data.world.map:
				continue
			p = [t[x] + select.start[x] for x in range (2)]
			data.world.map[n].tiles[target[1] % 8][target[0] % 12] = View.find_tile (self, p, select.start[2])
	def handle_cursor (self, diff):
		p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
		ap = [p[t] * 50 / screenzoom for t in range (2)]
		if self.moveinfo == None:
			self.offset = [self.offset[t] - diff[t] * self.screensize[t] / 4 for t in range (2)]
			self.clamp_offset ()
		elif self.moveinfo[0] == 'tileselect':
			# No response to cursor keys.
			pass
		elif self.moveinfo[0] == 'spriteselect':
			# No response to cursor keys.
			pass
		elif self.moveinfo[0] == 'resize':
			for s in spriteselect:
				if s[1]:
					continue
				s[0].size -= diff[1] * 10 + diff[0]
			# adjust moveinfo to use new data, but keep old cancel data.
			avg = make_avg ()
			dist = make_dist (avg, ap)
			size = [x[0].size for x in spriteselect]
			self.moveinfo = 'resize', (avg, dist, size), self.moveinfo[2]
			update_editgui ()
		elif self.moveinfo[0] == 'move':
			self.do_move (diff)
		elif self.moveinfo[0] == 'que':
			for s in spriteselect:
				if s[1]:
					continue
				s[0].que -= diff[1] * 10 + diff[0]
			update_editgui ()
		elif self.moveinfo[0] == 'crop':
			self.do_crop (diff)
		self.update ()
	def find_sprites (self, region, point):
		rx = [region[t][0] for t in range (2)]
		ry = [region[t][1] for t in range (2)]
		rx.sort ()
		ry.sort ()
		sx = [rx[t] / (12 * 50) for t in range (2)]
		sy = [ry[t] / (8 * 50) for t in range (2)]
		maps = []
		for dy in range (-1, sy[1] - sy[0] + 2):
			if sy[0] + dy < 0 or sy[0] + dy >= 24:
				continue
			for dx in range (-1, sx[1] - sx[0] + 2):
				if sx[0] + dx < 0 or sx[0] + dx >= 32:
					continue
				maps += ((sy[0] + dy) * 32 + (sx[0] + dx) + 1,)
		lst = []
		def try_add (que, sp, warp, pos):
			if (que, (sp, warp), pos) in lst:
				return
			lst.append ((que, (sp, warp), pos))
		for s in maps:
			# Only look at existing maps.
			if s in data.world.map:
				for sp in data.world.map[s].sprite:
					if sp.layer != the_gui.active_layer:
						continue
					pos = (sp.x, sp.y)
					if point:
						seq = data.seq.find_seq (sp.seq)
						if seq:
							(hotx, hoty), (left, top, right, bottom), box = data.seq.get_box (sp.size, (sp.x, sp.y), seq.frames[sp.frame], (sp.left, sp.top, sp.right, sp.bottom))
							if rx[0] >= left and ry[0] >= top and rx[0] < right and ry[0] < bottom:
								try_add (pos[1] - sp.que, sp, False, pos)
					else:
						if pos[0] >= rx[0] and pos[0] < rx[1] and pos[1] >= ry[0] and pos[1] < ry[1]:
							try_add (pos[1] - sp.que, sp, False, pos)
			# Add all warp points, too.
			if s in warptargets:
				# Origin of this map.
				sy = ((s - 1) / 32) * 50 * 8
				sx = ((s - 1) % 32) * 50 * 12
				for sp in warptargets[s]:
					if sp.layer != the_gui.active_layer:
						continue
					pos = (sx + sp.warp[1], sy + sp.warp[2])
					if point:
						if -20 <= rx[0] - pos[0] < 20 and -20 <= ry[0] - pos[1] < 20:
							try_add (pos[1] - sp.que, sp, True, pos)
					else:
						if pos[0] >= rx[0] and pos[0] < rx[1] and pos[1] >= ry[0] and pos[1] < ry[1]:
							try_add (pos[1] - sp.que, sp, True, pos)
		return lst
	def start_crop (self):
		for s in spriteselect:
			if s[1]:
				continue
			if s[0].left != 0 or s[0].right != 0 or s[0].top != 0 or s[0].bottom != 0:
				continue
			seq = data.seq.find_seq (s[0].seq)
			if not seq:
				continue
			bb = seq.frames[s[0].frame].boundingbox
			s[0].right = bb[2] - bb[0]
			s[0].bottom = bb[3] - bb[1]
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.offset[x] + self.pointer_pos[x]) / screenzoom for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if self.moveinfo is not None and e.button == 1:
			# Finish operation.
			self.finish_move ()
			return
		if e.button == 3:
			if self.moveinfo is not None and self.moveinfo[0] != 'pan':
				# Cancel operation.
				self.abort_move ()
			return
		if e.button == 2:
			p = [self.pointer_pos[x] + self.offset[x] for x in range (2)]
			ap = [p[t] * 50 / screenzoom for t in range (2)]
			self.moveinfo = 'pan', ap, self.make_cancel ()
			self.panned = False
			return
		x, y = [(self.offset[x] + self.pointer_pos[x]) * 50 / screenzoom for x in range (2)]
		keep_selection = e.state & gtk.gdk.CONTROL_MASK
		if e.state & gtk.gdk.SHIFT_MASK:
			spriteselect[:] = []
			x, y = self.pos_from_event ((e.x, e.y))
			View.tileselect (self, x, y, not keep_selection, 0)
			self.moveinfo = 'tileselect', (x, y), self.make_cancel ()
		else:
			# Clear tile selection.
			select.clear ()
			# Find all sprites which are pointed at.
			lst = self.find_sprites (((x, y), (x, y)), True)
			# If the list is empty, clear the selection.
			if lst == []:
				if not keep_selection:
					spriteselect[:] = []
				self.moveinfo = 'spriteselect', [(x, y), (x, y), None], self.make_cancel ()
				return
			# Sort the sprites by depth.
			lst.sort (key = lambda x: -x[0])
			# If the currently selected sprite is in the list, select the next; otherwise select the first.
			if not keep_selection:
				if len (spriteselect) == 1:
					for s in range (len (lst)):
						if spriteselect[0] == lst[s][1]:
							pos = lst[s][2]
							if s == len (lst) - 1:
								self.waitselect = lst[0][1:]
							else:
								self.waitselect = lst[s + 1][1:]
							break
					else:
						# Current selection is not in the list. Select first and update gui.
						spriteselect[:] = (lst[0][1],)
						pos = lst[0][2]
						update_editgui ()
				else:
					# There was not a 1-sprite selection. Select first and update gui.
					spriteselect[:] = (lst[0][1],)
					pos = lst[0][2]
					update_editgui ()
			else:
				# Add first not-yet-selected sprite to the selection.
				for s in lst:
					if s[1] in spriteselect:
						continue
					spriteselect.append (s[1])
					pos = s[2]
					break
			self.selecting = True
			self.moveinfo = 'spriteselect', [(x, y), (x, y), spriteselect[-1]], self.make_cancel ()
		self.update ()
	def button_off (self, widget, e):
		if e.button == 1:
			if self.moveinfo is not None and self.moveinfo[0] == 'path':
				return
			self.selecting = False
			self.moveinfo = None
			if self.waitselect != None:
				spriteselect[:] = (self.waitselect[0],)
				pos = self.waitselect[1]
				update_editgui ()
		elif e.button == 2:	# paste
			self.moveinfo = None
			if self.panned:
				return
			if select.empty ():
				# paste sprites.
				x, y = [(self.offset[x] + self.pointer_pos[x]) * 50 / screenzoom for x in range (2)]
				newselect = []
				avg = make_avg ()
				for paster in spriteselect:
					if paster[1]:
						# Don't paste warp points.
						continue
					src = paster[0]
					sp = data.world.add_sprite (paster[0].name, (x + src.x - avg[0] * 50 / screenzoom, y + src.y - avg[1] * 50 / screenzoom), src.seq, src.frame)
					sp.layer = int (the_gui.active_layer)
					sp.size = src.size
					sp.brain = src.brain
					sp.script = src.script
					sp.speed = src.speed
					sp.base_walk = src.base_walk
					sp.base_idle = src.base_idle
					sp.base_attack = src.base_attack
					sp.base_death = src.base_death
					sp.timing = src.timing
					sp.que = src.que
					sp.hard = src.hard
					sp.left = src.left
					sp.top = src.top
					sp.right = src.right
					sp.bottom = src.bottom
					sp.warp = None
					sp.touch_seq = src.touch_seq
					sp.gold = src.gold
					sp.hitpoints = src.hitpoints
					sp.strength = src.strength
					sp.defense = src.defense
					sp.experience = src.experience
					sp.sound = src.sound
					sp.vision = src.vision
					sp.nohit = src.nohit
					sp.touch_damage = src.touch_damage
					sp.register ()
					newselect += ((sp, False),)
				spriteselect[:] = newselect
				update_editgui ()
			else:
				# paste tiles.
				self.paste (self.pos_from_event ((e.x, e.y)))
			self.update ()
		elif e.button == 3:
			self.selecting = False
			self.moveinfo = None
		self.update ()
	def do_move (self, diff):
		for mover in range (len (spriteselect)):
			sp = spriteselect[mover][0]
			if not spriteselect[mover][1]:
				sp.unregister ()
				sp.x += diff[0]
				sp.y += diff[1]
				# Don't update entire gui, because it's too slow.
				global updating
				updating = True
				the_gui.x = int (sp.x)
				the_gui.y = int (sp.y)
				updating = False
				sp.register ()
			else:
				# Move the warp point.
				s = [((sp.warp[0] - 1) % 32) * (12 * 50), ((sp.warp[0] - 1) / 32) * (8 * 50)]
				p = [(sp.warp[1], sp.warp[2])[t] + diff[t] for t in range (2)]
				while p[0] < 0 and s[0] > 0:
					p[0] += 12 * 50
					s[0] -= 12 * 50
				while p[0] > 12 * 50 and s[0] < 32 * 8 * 50:
					p[0] -= 12 * 50
					s[0] += 12 * 50
				while p[1] < 0 and s[1] > 0:
					p[1] += 8 * 50
					s[1] -= 8 * 50
				while p[1] > 8 * 50 and s[1] < 24 * 8 * 50:
					p[1] -= 8 * 50
					s[1] += 8 * 50
				remove_warptarget (sp)
				sp.warp = ((s[1] / (8 * 50)) * 32 + (s[0] / (12 * 50)) + 1, p[0], p[1])
				add_warptarget (sp)
		update_editgui ()
	def do_crop (self, diff):
		for cropper in range (len (spriteselect)):
			if spriteselect[cropper][1]:
				continue
			s = spriteselect[cropper][0]
			s.unregister ()
			if self.moveinfo[1][0] == 2:
				s.bottom += diff[1]
				if s.bottom <= s.top:
					s.bottom = s.top + 1
			elif self.moveinfo[1][0] == 4:
				s.left += diff[0]
				if s.left < 0:
					s.left = 0
				elif s.left >= s.right:
					s.left = s.right - 1
			elif self.moveinfo[1][0] == 6:
				s.right += diff[0]
				if s.right <= s.left:
					s.right = s.left + 1
			elif self.moveinfo[1][0] == 8:
				s.top += diff[1]
				if s.top < 0:
					s.top = 0
				elif s.top >= s.bottom:
					s.top = s.bottom - 1
			s.register ()
	def move (self, widget, e):
		global screenzoom
		self.waitselect = None
		ex, ey, emask = self.get_window ().get_pointer ()
		tile = self.pointer_tile
		pos = int (ex), int (ey)
		diff = [(pos[t] - self.pointer_pos[t]) * 50 / screenzoom for t in range (2)]
		self.pointer_pos = pos
		apos = [(self.pointer_pos[t] + self.offset[t]) * 50 / screenzoom for t in range (2)]
		sx = apos[0] / (50 * 12)
		sy = apos[1] / (50 * 8)
		the_gui.statuslabel = '%03d/%03d,%03d' % (sx + 32 * sy + 1, apos[0] - sx * 50 * 12, apos[1] - sy * 50 * 8)
		self.pointer_tile = [(self.pointer_pos[t] + self.offset[t]) / screenzoom for t in range (2)]
		if self.moveinfo == None:
			if not select.empty ():
				self.update ()
			return
		elif self.moveinfo[0] == 'tileselect':
			View.select_tiles (self, tile, 0)
		elif self.moveinfo[0] == 'spriteselect':
			# Toggle selected-state of sprites on border.
			if self.moveinfo[1][2] != None:
				if self.moveinfo[1][2] in spriteselect:
					spriteselect.remove (self.moveinfo[1][2])
				else:
					spriteselect.append (self.moveinfo[1][2])
				self.moveinfo[1][2] = None
			old = self.moveinfo[1][0:2]
			new = self.moveinfo[1][0], [(pos[t] + self.offset[t]) * 50 / screenzoom for t in range (2)]
			oldlst = self.find_sprites (old, False)
			newlst = self.find_sprites (new, False)
			for i in newlst + oldlst:
				if i not in oldlst or i not in newlst:
					if i[1] in spriteselect:
						spriteselect.remove (i[1])
					else:
						spriteselect.append (i[1])
			self.moveinfo[1][1] = [(pos[t] + self.offset[t]) * 50 / screenzoom for t in range (2)]
			if len (spriteselect) == 1:
				self.current_selection = 0
			else:
				self.current_selection = len (spriteselect)
		elif self.moveinfo[0] == 'resize':
			# moveinfo[1] is (hotspot, dist, size[]).
			p = [self.pointer_pos[t] + self.offset[t] for t in range (2)]
			ap = [p[t] * 50 / screenzoom for t in range (2)]
			dist = make_dist (self.moveinfo[1][0], ap)
			for s in range (len (spriteselect)):
				if spriteselect[s][1]:
					continue
				spriteselect[s][0].size = self.moveinfo[1][2][s] * dist / self.moveinfo[1][1]
				# TODO: adjust position
		elif self.moveinfo[0] == 'move':
			self.do_move (diff)
		elif self.moveinfo[0] == 'que':
			for s in spriteselect:
				if s[1]:
					continue
				s[0].que -= diff[1]
		elif self.moveinfo[0] == 'crop':
			self.do_crop (diff)
		elif self.moveinfo[0] == 'pan':
			self.panned = True
			self.offset = [self.offset[x] - diff[x] * screenzoom / 50 for x in range (2)]
			self.clamp_offset ()
			update_maps ()
		elif self.moveinfo[0] == 'path':
			# Path is made at confirm, so nothing to do here.
			pass
		else:
			raise AssertionError ('invalid moveinfo type %s' % self.moveinfo[0])
		update_editgui ()
		self.update ()
# }}}

class ViewSeq (View): # {{{
	def __init__ (self):
		View.__init__ (self)
		self.selected_seq = None
		self.tiles = (0, 0)	# This must be defined for clamp_offset, but it isn't used.
		self.update_handle = None
	def update (self):
		if self.update_handle is not None:
			return
		self.update_handle = glib.idle_add (self.do_update)
	def do_update (self):
		self.update_handle = None
		if self.buffer == None:
			return
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		s = seqlist ()
		# Compute tile size.
		self.tilesize = int (math.sqrt (self.screensize[0] * self.screensize[1] / len (s)))
		while True:
			self.width = self.screensize[0] / self.tilesize
			if self.width > 0:
				ns = (len (s) + self.width - 1) / self.width
				if ns * self.tilesize <= self.screensize[1]:
					break
			self.tilesize -= 1
		self.height = ns
		if self.selected_seq == None:
			for y in range (ns):
				for x in range (self.width):
					if y * self.width + x >= len (s):
						self.draw_seq ((x, y), None)
						continue
					pb = data.get_seq (data.seq.seq[s[y * self.width + x]], 1)
					self.draw_seq ((x, y), pb)
		else:
			# Draw clicked sequence.
			x0, y0 = self.selected_seq
			pos0 = y0 * self.width + x0
			pb = data.get_seq (data.seq.seq[s[pos0]], 1)
			self.draw_seq (self.selected_seq, pb)
			# Draw selectable frames.
			frames = data.seq.seq[s[pos0]].frames
			off, yoff = self.get_offsets (x0, y0, len (frames))
			for f in range (1, len (frames)):
				pb = data.get_seq (data.seq.seq[s[pos0]], f)
				y = yoff + 1 + (f - 1 + off) / self.width
				x = (f - 1 + off) % self.width
				self.draw_seq ((x, y), pb)
		if not the_gui.nobackingstore:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		ctrl = e.state & gtk.gdk.CONTROL_MASK
		shift = e.state & gtk.gdk.SHIFT_MASK
		return self.key_global (e.keyval, ctrl, shift) or self.key_seq (e.keyval, ctrl, shift) or (not ctrl and not shift and viewmap.key_numpad (e.keyval))
	def get_selected_sequence (self):
		x, y = self.pointer_pos
		s = seqlist ()
		ns = (len (s) + self.width - 1) / self.width
		if x >= 0 and x < self.tilesize * self.width and y >= 0 and y < self.tilesize * ns:
			target = (y / self.tilesize) * self.width + x / self.tilesize
			if len (s) > target:
				return s[target]
		return None
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [self.pointer_pos[x] / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		seq = self.get_selected_sequence ()
		if e.button == 1:	# perform action or change selected sequence
			if seq != '':
				self.selected_seq = self.pointer_tile
				self.update ()
		elif e.button == 2:	# add new sprite
			if seq == '':
				return
			self.selected_seq = self.pointer_tile
			self.update ()
	def button_off (self, widget, e):
		if self.selected_seq == None:
			return
		# Find clicked frame and change sprite or create new.
		self.pointer_pos = int (e.x), int (e.y)	# Position of pointer in pixels.
		s = seqlist ()					# List of available sequences.
		seq, frame, x0, y0 = self.get_info (s, lambda x: data.seq.seq[x])
		if frame is None:
			return
		if e.button == 1:
			for spr in spriteselect:
				# Change sprites or warp animations.
				if spr[1]:
					spr[0].touch_seq = seq
				else:
					spr[0].unregister ()
					spr[0].seq = seq
					spr[0].frame = frame
					spr[0].register ()
			update_editgui ()
		elif e.button == 2:
			x, y = viewmap.newinfo
			sp = data.world.add_sprite (None, (x, y), s[y0 * self.width + x0], frame)
			sp.layer = int (the_gui.active_layer)
			spriteselect[:] = ((sp, False),)
			update_editgui ()
		else:
			# Don't return to the map.
			return
		self.selected_seq = None
		the_gui.setmap = True
		viewmap.update ()
# }}}

class ViewCollection (View): # {{{
	def __init__ (self):
		View.__init__ (self)
		self.available = []
		self.selected_seq = None
		self.tiles = (0, 0)	# This must be defined for clamp_offset, but it isn't used.
		self.update_handle = None
	def update (self):
		if self.update_handle is not None:
			return
		self.update_handle = glib.idle_add (self.do_update)
	def do_update (self):
		self.update_handle = None
		if self.buffer == None:
			return
		# TODO: clear only what is not going to be cleared
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		c = self.available
		# Compute tile size.
		self.tilesize = int (math.sqrt (self.screensize[0] * self.screensize[1] / len (c)))
		while True:
			self.width = self.screensize[0] / self.tilesize
			if self.width > 0:
				nc = (len (c) + self.width - 1) / self.width
				if nc * self.tilesize <= self.screensize[1]:
					break
			self.tilesize -= 1
		self.height = nc
		if self.selected_seq == None:
			for y in range (nc):
				for x in range (self.width):
					if y * self.width + x >= len (c):
						self.draw_seq ((x, y), None)
						continue
					if c[y * self.width + x][0] == '':
						continue
					seq = c[y * self.width + x]
					pb = data.get_seq (data.seq.collection[seq[0]][seq[1]], 1)
					self.draw_seq ((x, y), pb)
		else:
			# Draw clicked sequence.
			x0, y0 = self.selected_seq
			pos0 = y0 * self.width + x0
			seq = c[pos0]
			pb = data.get_seq (data.seq.collection[seq[0]][seq[1]], 1)
			self.draw_seq (self.selected_seq, pb)
			# Draw selectable frames.
			frames = data.seq.collection[seq[0]][seq[1]].frames
			off, yoff = self.get_offsets (x0, y0, len (frames))
			for f in range (1, len (frames)):
				pb = data.get_seq (data.seq.collection[seq[0]][seq[1]], f)
				y = yoff + 1 + (f - 1 + off) / self.width
				x = (f - 1 + off) % self.width
				self.draw_seq ((x, y), pb)
		if not the_gui.nobackingstore:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def direction (self, d):
		self.thedirection = d
		self.available = [('', None)]
		for c in collectionlist ():
			if d in data.seq.collection[c]:
				self.available += ((c, d),)
			elif d != 'die':
				self.available += ((c, data.seq.get_dir_seq (c, d, num = True)),)
		self.update ()
	def get_selected_sequence (self):
		x, y = self.pointer_pos
		c = self.available
		nc = (len (c) + self.width - 1) / self.width
		if x >= 0 and x < self.tilesize * self.width and y >= 0 and y < self.tilesize * nc:
			target = (y / self.tilesize) * self.width + x / self.tilesize
			if target <= len (c):
				return c[target]
		return None
	def get_selected_collection (self):
		s = self.get_selected_sequence ()
		if s is None:
			return None
		return s[0]
	def keypress (self, widget, e):
		ctrl = e.state & gtk.gdk.CONTROL_MASK
		shift = e.state & gtk.gdk.SHIFT_MASK
		return self.key_global (e.keyval, ctrl, shift) or self.key_collection (e.keyval, ctrl, shift) or (not ctrl and not shift and viewmap.key_numpad (e.keyval))
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [self.pointer_pos[x] / self.tilesize for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		seq = self.get_selected_sequence ()
		if seq == None:
			return
		if e.button == 1:	# perform action or change selected sequence
			if View.collectiontype == None:
				if len (spriteselect) != 1:
					return
				if spriteselect[0][1]:
					spr = spriteselect[0][0]
					spr.touch_seq = seq
					the_gui.setmap = True
					viewmap.update ()
				else:
					if seq[0] != '':
						self.selected_seq = self.pointer_tile
						self.update ()
			else:
				for s in spriteselect:
					if View.collectiontype == 'idle':
						s[0].base_idle = seq
					elif View.collectiontype == 'death':
						s[0].base_death = seq
					elif View.collectiontype == 'walk':
						s[0].base_walk = seq
					elif View.collectiontype == 'attack':
						s[0].base_attack = seq
					else:
						raise AssertionError ('invalid collection type %s' % View.collectiontype)
		elif e.button == 2:	# add new sprite
			if View.collectiontype != None or seq == '':
				return
			self.selected_seq = self.pointer_tile
			self.update ()
	def button_off (self, widget, e):
		if self.selected_seq == None:
			return
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [self.pointer_pos[x] / self.tilesize for x in range (2)]
		c = self.available
		seq, frame, x0, y0 = self.get_info (c, lambda x: data.seq.collection[x[0]][x[1]])
		if frame is None:
			return
		if e.button == 1:
			for spr in spriteselect:
				# Don't accidentily change sprite when warp target is selected.
				if spr[1]:
					# Don't return to the map.
					continue
				spr[0].seq = seq
				spr[0].frame = frame
			update_editgui ()
		elif e.button == 2:	# add new sprite
			x, y = viewmap.newinfo
			sp = data.world.add_sprite (None, (x, y), seq, 1)
			sp.layer = int (the_gui.active_layer)
			spriteselect[:] = ((sp, False),)
			update_editgui ()
		else:
			return
		self.selected_seq = None
		the_gui.setmap = True
		viewmap.update ()
# }}}

class ViewTiles (View): # {{{
	def __init__ (self):
		View.__init__ (self)
		self.pointer_tile = (0, 0)	# Tile that the pointer is currently pointing it, in world coordinates. That is: pointer_pos / screenzoom.
		self.tiles = (12 * 6, 8 * 7)	# Total number of tiles
		self.set_size_request (screenzoom * 12, screenzoom * 8)
		self.offset = (0, 0)
		self.update_handle = None
	def find_tile (self, worldpos):
		if worldpos[0] >= 0 and worldpos[0] < 6 * 12 and worldpos[1] >= 0 and worldpos[1] < 7 * 8:
			n = (worldpos[1] / 8) * 6 + worldpos[0] / 12 + 1
			if 1 <= n <= 41:
				return [n, worldpos[0] % 12, worldpos[1] % 8]
		return [-1, -1, -1]
	def draw_tile (self, screenpos, worldpos):
		View.draw_tile (self, screenpos, worldpos, True)
	def update (self):
		if self.update_handle is not None:
			return
		self.update_handle = glib.idle_add (self.do_update)
	def do_update (self):
		self.update_handle = None
		if self.buffer == None:
			return
		View.draw_tiles (self, 1)
		if not the_gui.nobackingstore:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		ctrl = e.state & gtk.gdk.CONTROL_MASK
		shift = e.state & gtk.gdk.SHIFT_MASK
		return self.key_global (e.keyval, ctrl, shift) or self.key_tiles (e.keyval, ctrl, shift)
	def get_pointed_map (self, pos = None):
		if pos is None:
			pos = self.pointer_pos
		ret = [(self.offset[x] + pos[x]) / ((12, 8)[x] * screenzoom) for x in range (2)]
		return (ret[0], ret[1], ret[0] + ret[1] * 32 + 1)
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		tile = self.pointer_tile
		pos = int (ex), int (ey)
		diff = [(pos[x] - self.pointer_pos[x]) * 50 / screenzoom for x in range (2)]
		self.pointer_pos = pos
		self.pointer_tile = [(pos[x] + self.offset[x]) / screenzoom for x in range (2)]
		if not self.panning and not self.selecting and select.empty ():
			return
		if self.panning:
			self.offset = [self.offset[x] - diff[x] for x in range (2)]
			self.clamp_offset ()
		if self.selecting:
			View.select_tiles (self, tile, 1)
		self.update ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		self.pointer_tile = [(self.pointer_pos[x] + self.offset[x]) / screenzoom for x in range (2)]
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 1:
			if self.panning:
				self.panning = False
			else:
				x, y = self.pos_from_event ((e.x, e.y))
				View.tileselect (self, x, y, not e.state & gtk.gdk.CONTROL_MASK, 1)
		elif e.button == 2:
			self.panning = True
	def button_off (self, widget, e):
		self.selecting = False
		if e.button == 2:
			self.panning = False
# }}}

class ViewWorld (View): # {{{
	def __init__ (self):
		View.__init__ (self)
		self.set_size_request (32 * 12, 24 * 8)
		self.tiles = (0, 0)	# This must be defined for clamp_offset, but it isn't used.
		self.tsize = 1
		self.off = (0, 0)
		self.update_handle = None
	def update (self):
		if self.update_handle is not None:
			return
		self.update_handle = glib.idle_add (self.do_update)
	def do_update (self):
		self.update_handle = None
		if not self.buffer:
			return
		s = (32, 24)
		scrsize = (12, 8)
		self.tsize = min ([self.screensize[x] / s[x] for x in range (2)])
		self.off = [(self.screensize[x] - s[x] * self.tsize) / 2 for x in range (2)]
		self.buffer.draw_rectangle (self.emptygc, True, 0, 0, self.screensize[0], self.screensize[1])
		for y in range (s[1]):
			self.buffer.draw_line (self.bordergc, self.off[0], self.off[1] + y * self.tsize, self.off[0] + s[0] * self.tsize - 1, self.off[1] + y * self.tsize)
			for x in range (s[0]):
				self.buffer.draw_line (self.bordergc, self.off[0] + x * self.tsize, self.off[1], self.off[0] + x * self.tsize, self.off[1] + s[1] * self.tsize - 1)
				n = y * 32 + x + 1
				if n in data.world.map:
					if data.world.map[n].indoor:
						self.buffer.draw_rectangle (self.noshowgc, True, self.off[0] + self.tsize * x + 1, self.off[1] + self.tsize * y + 1, self.tsize - 1, self.tsize - 1)
					else:
						self.buffer.draw_rectangle (self.noselectgc, True, self.off[0] + self.tsize * x + 1, self.off[1] + self.tsize * y + 1, self.tsize - 1, self.tsize - 1)
				else:
					self.buffer.draw_rectangle (self.invalidgc, True, self.off[0] + self.tsize * x + 1, self.off[1] + self.tsize * y + 1, self.tsize - 1, self.tsize - 1)
		self.buffer.draw_line (self.bordergc, self.off[0], self.off[1] + s[1] * self.tsize, self.off[0] + s[0] * self.tsize - 1, self.off[1] + s[1] * self.tsize)
		self.buffer.draw_line (self.bordergc, self.off[0] + s[0] * self.tsize, self.off[1], self.off[0] + s[0] * self.tsize, self.off[1] + s[1] * self.tsize - 1)
		targetsize = [max (2, viewmap.screensize[x] * self.tsize / screenzoom / scrsize[x]) for x in range (2)]
		current = [viewmap.offset[t] * self.tsize / scrsize[t] / screenzoom + self.off[t] for t in range (2)]
		self.buffer.draw_rectangle (self.selectgc, False, current[0], current[1], targetsize[0] - 1, targetsize[1] - 1)
		self.buffer.draw_rectangle (self.pastegc, False, self.pointer_pos[0] - targetsize[0] / 2, self.pointer_pos[1] - targetsize[1] / 2, targetsize[0] - 1, targetsize[1] - 1)
		if not the_gui.nobackingstore:
			self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, self.screensize[0], self.screensize[1])
	def keypress (self, widget, e):
		ctrl = e.state & gtk.gdk.CONTROL_MASK
		shift = e.state & gtk.gdk.SHIFT_MASK
		return self.key_global (e.keyval, ctrl, shift)
	def select (self):
		self.selecting = True
		s = (32, 24)
		scrsize = (12, 8)
		viewmap.offset = [(self.pointer_pos[x] - self.off[x]) * screenzoom * scrsize[x] / self.tsize - viewmap.screensize[x] / 2 for x in range (2)]
		viewmap.clamp_offset ()
		viewmap.update ()
		self.update ()
		update_maps ()
	def button_on (self, widget, e):
		self.grab_focus ()
		self.pointer_pos = int (e.x), int (e.y)
		if e.type != gtk.gdk.BUTTON_PRESS:
			return
		if e.button == 1:
			self.select ()
	def button_off (self, widget, e):
		self.selecting = False
		the_gui.setmap2 = True
	def move (self, widget, e):
		ex, ey, emask = self.get_window ().get_pointer ()
		self.pointer_pos = int (ex), int (ey)
		if self.selecting:
			self.select ()
		s = (32, 24)
		scrsize = (12, 8)
		pos = [(self.pointer_pos[x] - self.off[x]) / self.tsize for x in range (2)]
		the_gui.statuslabel = '%03d/%03d,%03d' % (pos[0] + pos[1] * 32 + 1, pos[0], pos[1])
		self.update ()
# }}}

# {{{ Gui utility functions
def show_error (message):
	if message == '':
		return
	the_gui.error = message
	the_gui.show_error = True

def visibility (layer):
	return 2 - getattr (the_gui, 'layer%d_presentation' % layer)

def get_map ():
	s = the_gui.map_text
	if s is None:
		return None
	x, y = [int (x) for x in s.split ()[0].split (',')]
	return y * 32 + x + 1

def new_sprite ():
	'''New sprite selected in the gui'''
	if updating:
		return
	sprite = the_gui.sprite
	if sprite == 0:
		viewmap.current_selection = len (spriteselect)
	else:
		viewmap.current_selection = sprite - 1
	update_editgui ()
	View.update (viewmap)

def new_map ():
	if updating:
		return
	txtmap = the_gui.map_text
	if txtmap is None:
		return
	x, y = [int (t) for t in txtmap.split ()[0].split (',')]
	viewmap.goto ((x * 600 + 300, y * 400 + 200))

def update_maps ():
	global updating
	if updating:
		return
	updating = True
	maps = data.world.map.keys ()
	maps.sort ()
	global map_list
	map_list = ['%d,%d (%d)' % ((n - 1) % 32, (n - 1) / 32, n) for n in maps]
	the_gui.set_map_list = map_list
	the_gui.map_text = '%d,%d (%d)' % viewmap.get_current_map ()
	updating = False

def update_editgui ():
	'''Update the sidebar so it reflects what is on the map.
	This is called after changing things with the mouse or shortcut keys.'''
	global updating
	if updating:
		# Not sure how this can happen, but prevent looping anyway.
		return
	updating = True
	# Update map information.
	map = viewmap.get_current_map ()[2]
	if map in data.world.map:
		the_gui.map_script = data.world.map[map].script
		the_gui.map_hardness = data.world.map[map].hard
		the_gui.map_music = data.world.map[map].music
		the_gui.indoor = data.world.map[map].indoor
	# Update list of selected sprites.
	the_gui.set_spritelist = ['All selected sprites'] + ['%s warp' % x[0].name if x[1] else x[0].name for x in spriteselect]
	if not 0 <= viewmap.current_selection < len (spriteselect):
		the_gui.sprite = 0
	else:
		the_gui.sprite = viewmap.current_selection + 1
	if len (spriteselect) == 0:
		# No selection, so nothing to update.
		updating = False
		return
	if len (spriteselect) == 1:
		sprite = spriteselect[0][0]
	elif not 0 <= viewmap.current_selection < len (spriteselect):
		# Combine stuff.
		def combine (item, default):
			a = [getattr (s[0], item) for s in spriteselect if not s[1]]
			if len (a) > 0 and all ([x == a[0] for x in a]):
				return a[0]
			return default
		the_gui.name = ''
		m = combine ('map', 0)
		the_gui.map = 0 if m is None else m
		the_gui.x = combine ('x', 0)
		the_gui.y = combine ('y', 0)
		the_gui.layer = combine ('layer', int (the_gui.active_layer))
		s = combine ('seq', '')
		if type (s) == str:
			the_gui.seq_text = s
		else:
			the_gui.seq_text = '%s %d' % s
		the_gui.frame = combine ('frame', 0)
		the_gui.size = combine ('size', 0)
		the_gui.brain = combine ('brain', '-')
		the_gui.script = combine ('script', '-')
		the_gui.speed = combine ('speed', 0)
		the_gui.base_walk_text = combine ('base_walk', '')
		the_gui.base_idle_text = combine ('base_idle', '')
		the_gui.base_attack_text = combine ('base_attack', '')
		the_gui.timing = combine ('timing', 0)
		the_gui.que = combine ('que', -1)
		the_gui.hard = combine ('hard', None)
		the_gui.use_hard = combine ('use_hard', None)
		crops = [(s[0].left != 0 or s[0].right != 0 or s[0].top != 0 or s[0].bottom != 0, s[0]) for s in spriteselect if not s[1]]
		if len (crops) > 0 and all ([c[0] == crops[0][0] for c in crops[1:]]):
			the_gui.crop = crops[0][0]
		else:
			the_gui.crop = None
		def combine_crop (item):
			a = [getattr (s[1], item) for s in crops if s[0]]
			if len (a) == 0 or not all ([x == a[0] for x in a]):
				return 0
			return a[0]
		the_gui.left = combine_crop ('left')
		the_gui.top = combine_crop ('top')
		the_gui.right = combine_crop ('right')
		the_gui.bottom = combine_crop ('bottom')
		warps = [(s[0].warp is not None, s[0]) for s in spriteselect if not s[1]]
		if len (warps) > 0 and all ([c[0] == warps[0][0] for c in warps[1:]]):
			the_gui.warp = warps[0][0]
		else:
			the_gui.warp = None
		def combine_warp (item):
			a = [s[1].warp[item] for s in warps if s[0]]
			if len (a) == 0 or not all ([x == a[0] for x in a]):
				return 0
			return a[0]
		the_gui.warpmap = combine_warp (0)
		the_gui.warpx = combine_warp (1)
		the_gui.warpy = combine_warp (2)
		ts = combine ('touch_seq', '')
		if type (ts) == str:
			the_gui.touchseq_text = ts
		else:
			the_gui.touchseq_text = '%s %d' % ts
		the_gui.base_death_text = combine ('base_death', '')
		the_gui.gold = combine ('gold', 0)
		the_gui.hitpoints = combine ('hitpoints', 0)
		the_gui.strength = combine ('strength', 0)
		the_gui.defense = combine ('defense', 0)
		the_gui.experience = combine ('experience', 0)
		the_gui.sound_text = combine ('sound', '')
		the_gui.vision = combine ('vision', 0)
		the_gui.nohit = combine ('nohit', None)
		the_gui.touch_damage = combine ('touch_damage', 0)
		updating = False
		return
	else:
		sprite = spriteselect[viewmap.current_selection][0]
	the_gui.name = sprite.name
	the_gui.map = sprite.map if sprite.map is not None else 0
	the_gui.x = sprite.x
	the_gui.y = sprite.y
	if type (sprite.seq) == str:
		the_gui.seq_text = sprite.seq
	else:
		the_gui.seq_text = '%s %s' % (sprite.seq[0], str (sprite.seq[1]))
	the_gui.frame = sprite.frame
	the_gui.size = sprite.size
	the_gui.brain = sprite.brain
	the_gui.script = sprite.script
	the_gui.speed = sprite.speed
	the_gui.base_walk_text = sprite.base_walk
	the_gui.base_idle_text = sprite.base_idle
	the_gui.base_attack_text = sprite.base_attack
	the_gui.timing = sprite.timing
	the_gui.que = sprite.que
	the_gui.hard = sprite.hard
	the_gui.use_hard = sprite.use_hard
	the_gui.crop = sprite.left != 0 or sprite.right != 0 or sprite.top != 0 or sprite.bottom != 0
	the_gui.left = sprite.left
	the_gui.top = sprite.top
	the_gui.right = sprite.right
	the_gui.bottom = sprite.bottom
	if sprite.warp == None:
		the_gui.warp = False
	else:
		the_gui.warp = True
		the_gui.warpmap = sprite.warp[0]
		the_gui.warpx = sprite.warp[1]
		the_gui.warpy = sprite.warp[2]
	if type (sprite.touch_seq) == str:
		the_gui.touchseq_text = sprite.touch_seq
	else:
		the_gui.touchseq_text = '%s %d' % sprite.touch_seq
	the_gui.base_death_text = sprite.base_death
	the_gui.gold = sprite.gold
	the_gui.hitpoints = sprite.hitpoints
	the_gui.strength = sprite.strength
	the_gui.defense = sprite.defense
	the_gui.experience = sprite.experience
	the_gui.sound_text = sprite.sound
	the_gui.vision = sprite.vision
	the_gui.nohit = sprite.nohit
	the_gui.touch_damage = sprite.touch_damage
	the_gui.layer = sprite.layer
	updating = False

# Update functions: change data to match gui.
# These functions are called when the gui is changed by the user.
def update_sprite_gui (name, action = setattr, type = int):
	if updating:
		return
	for s in (spriteselect if not 0 <= viewmap.current_selection < len (spriteselect) else (spriteselect[viewmap.current_selection],)):
		if s[1]:
			continue
		s[0].unregister ()
		action (s[0], name, type (getattr (the_gui, name)))
		s[0].register ()
	viewmap.update ()

def update_sprite_bool (name):
	# Like update_sprite_gui, this is called once for all sprites.
	if updating:
		return
	state = getattr (the_gui, name)
	if state == None:
		state = False
		setattr (the_gui, name, state)
	for s in (spriteselect if not 0 <= viewmap.current_selection < len (spriteselect) else (spriteselect[viewmap.current_selection],)):
		if s[1]:
			continue
		setattr (s[0], name, state)
	viewmap.update ()

def update_sprite_crop ():
	# Like update_sprite_gui, this is called once for all sprites.
	if updating:
		return
	state = the_gui.crop
	if state == None:
		state = False
		the_gui.crop = state
	for s in (spriteselect if not 0 <= viewmap.current_selection < len (spriteselect) else (spriteselect[viewmap.current_selection],)):
		if s[1]:
			continue
		if state:
			bbox = data.seq.find_seq (sprite.seq).boundingbox
			sprite.left = bbox[0]
			sprite.top = bbox[1]
			sprite.right = bbox[2]
			sprite.bottom = bbox[3]
		else:
			sprite.left = 0
			sprite.top = 0
			sprite.right = 0
			sprite.bottom = 0
	viewmap.update ()

def update_sprite_map (sprite, key, value):
	setattr (sprite, key, value if value > 0 else None)

def update_sprite_name (sprite, key, name):
	if name != '' and name != sprite.name:
		sprite.rename (name)

def update_sprite_layer ():
	update_sprite_gui ('layer')
	update_editgui ()

def update_sprite_seq (sprite, name, value):
	seq = fullseqlist ()[int (value)].split ()
	if len (seq) == 1:
		if data.seq.find_seq (seq[0]) != None:
			setattr (sprite, name, seq[0])
		else:
			print ('seq not found: %s', str (seq))
	else:
		if data.seq.find_collection (seq[0]) != None:
			setattr (sprite, name, seq)
		else:
			print ('collection not found: %s', str (seq))

def update_sprite_collection (sprite, name, value):
	collection = ([''] + collectionlist ())[int (value)]
	if data.seq.find_collection (collection) != None:
		setattr (sprite, name, collection)
	else:
		sprite.base_walk = ''

def update_sprite_warp (sprite, name, value):
	remove_warptarget (sprite)
	sprite.warp = None
	the_gui.warp = False

def update_sprite_warp_detail (sprite, name, value):
	if sprite.warp is None:
		return
	remove_warptarget (sprite)
	if name == 'warpmap':
		sprite.warp = (value, sprite.warp[1], sprite.warp[2])
	elif name == 'warpx':
		sprite.warp = (sprite.warp[0], value, sprite.warp[2])
	elif name == 'warpy':
		sprite.warp = (sprite.warp[0], sprite.warp[1], value)
	add_warptarget (sprite)

def update_sprite_crop_detail (sprite, name, value):
	if sprite.left == 0 and sprite.top == 0 and sprite.right == 0 and sprite.bottom == 0:
		return
	setattr (sprite, name, value)

def update_tile_gui ():
	if updating:
		return
	View.update (viewmap)
def update_map_gui ():
	if updating:
		return
	try:
		map = get_map ()
	except TypeError:
		map = None
	if map not in data.world.map:
		View.update (viewmap)
		return
	# Selected map: update
	# Screen script
	data.world.map[map].script = the_gui.map_script
	# Screen hardness
	data.world.map[map].hard = the_gui.map_hardness
	# Screen music
	data.world.map[map].music = the_gui.map_music
	# Indoor
	data.world.map[map].indoor = the_gui.indoor
	View.update (viewmap)
def update_layer_gui ():
	if updating:
		return
	viewmap.update ()
def update_world_gui ():
	if updating:
		return
	View.update (viewmap)

def do_edit (s, ext = 'c'):
	if s == '' or data is None:
		return
	name = os.path.join (tmpdir, s + os.extsep + ext)
	if s not in data.script.data:
		if ext == 'c':
			data.script.data[s] = ''
		# Create the empty file.
		if not os.path.exists (name):
			open (name, 'w')
		the_gui.set_scripts = data.script.data.keys ()
	os.system (the_gui.script_editor.replace ('$SCRIPT', name))

def do_delete_script ():
	if data is None:
		return
	script = the_gui.dmod_script
	if script not in data.script.data:
		the_gui.statusbar = "Cannot delete script %s: it doesn't exist" % script
	else:
		del data.script.data[script]
		the_gui.statusbar = "Deleted script %s" % script
		# Remove the file.
		os.unlink (os.path.join (tmpdir, script + os.extsep + 'c'))
		# Update the list.
		the_gui.set_scripts = data.script.data.keys ()

def do_edit_hard (h, map):
	if h == '' or map not in data.world.map:
		return
	sx = ((map - 1) % 32) * 12 * 50
	sy = ((map - 1) / 32) * 8 * 50
	name = os.path.join (tmpdir, h + os.extsep + 'png')
	if os.path.exists (name):
		# Update hardness.
		dink.make_hard_image (name).save (name)
		data.tile.hard[h] = (name, 0, os.stat (name).st_size)
	image = Image.new ('RGB', (50 * 12, 50 * 8), (0, 0, 0))
	# Write all tiles
	for y in range (8):
		for x in range (12):
			n, tx, ty = data.world.map[map].tiles[y][x]
			image.paste (Image.open (dink.filepart (*(data.tile.get_file (n)[:-1]))).crop ((tx * 50, ty * 50, (tx + 1) * 50, (ty + 1) * 50)), (x * 50, y * 50))
	# Write all sprites. Ignore sprites from other maps.
	lst = []
	for sp in data.world.map[map].sprite:
		pos = (sp.x, sp.y)
		seq = data.seq.find_seq (sp.seq)
		lst += ((pos, sp, seq),)
	lst.sort (key = lambda x: x[0][1] - x[1].que)
	for spr in lst:
		frame = spr[2].frames[spr[1].frame]
		(x, y), (left, top, right, bottom), box = data.seq.get_box (spr[1].size, spr[0], frame, (spr[1].left, spr[1].top, spr[1].right, spr[1].bottom))
		if right <= left or bottom <= top:
			continue
		# Draw the pixbuf.
		sprite = Image.open (dink.filepart (*frame.cache)).convert ('RGBA')
		p = sprite.load ()
		for y in range (sprite.size[1]):
			for x in range (sprite.size[0]):
				if (spr[2].type == 'black' and p[x, y][:3] == (0, 0, 0)) or (spr[2].type != 'black' and p[x, y][:3] == (255, 255, 255)):
					p[x, y] = (0, 0, 0, 0)
		sprite = sprite.crop (box)
		sprite = sprite.resize ((right - left, bottom - top))
		image.paste (sprite, (left - sx, top - sy), sprite)
	# Write sprite hardness as red boxes (ignored when reading back).
	pixels = image.load ()
	for spr in lst:
		if not spr[1].hard:
			continue
		frame = spr[2].frames[spr[1].frame]
		for x in range (frame.hardbox[2] - frame.hardbox[0]):
			px = spr[0][0] + frame.hardbox[0] + x
			if not 0 <= px < 600:
				continue
			y = spr[0][1] + frame.hardbox[1]
			if 0 <= y < 400:
				p = px, y
				pixels[p] = tuple ([255] + list (pixels[p])[1:])
			y = spr[0][1] + frame.hardbox[3]
			if 0 <= y < 400:
				p = px, y
				pixels[p] = tuple ([255] + list (pixels[p])[1:])
		for y in range (frame.hardbox[3] - frame.hardbox[1]):
			py = spr[0][1] + frame.hardbox[1] + y
			if not 0 <= py < 400:
				continue
			x = spr[0][0] + frame.hardbox[0]
			if 0 <= x < 600:
				p = x, py
				pixels[p] = tuple ([255] + list (pixels[p])[1:])
			x = spr[0][0] + frame.hardbox[2]
			if 0 <= x < 600:
				p = x, py
				pixels[p] = tuple ([255] + list (pixels[p])[1:])
	# Make dark
	image = Image.eval (image, lambda v: v / 2)
	# Add hardness
	f = data.tile.get_hard_file (h)
	if f == None:
		# Fill with default hardness for tiles.
		for y in range (8):
			for x in range (12):
				n, tx, ty = data.world.map[map].tiles[y][x]
				hard = Image.open (dink.filepart (*(data.tile.get_hard_file (n)[:-1]))).crop ((tx * 50, ty * 50, (tx + 1) * 50, (ty + 1) * 50))
				# Paste twice for extra intensity (190 minimum)
				image.paste (hard, (x * 50, y * 50), hard)
				image.paste (hard, (x * 50, y * 50), hard)
	else:
		im = Image.open (dink.filepart (*(f[:-1])))
		# Paste twice for extra intensity (190 minimum)
		image.paste (im, None, im)
		image.paste (im, None, im)
	image.save (name)
	os.system (the_gui.hardness_editor.replace ('$IMAGE', name))
	data.cache_flush_hard (h)
	data.tile.hard[h] = (name, 0, os.stat (name).st_size)
	sync ()
	viewmap.update ()

def edit_map_hardness (action = None):
	map = get_map ()
	if the_gui.map_hardness == '':
		the_gui.map_hardness = '%03d' % map
	do_edit_hard (the_gui.map_hardness, map)

def edit_map_script (action = None):
	if the_gui.map_script == '':
		the_gui.map_script = 'map%d' % get_map ()
	do_edit (the_gui.map_script)

def edit_sprite_scripts (action = None):
	if len (spriteselect) == 0:
		s = the_gui.script
		if s != '':
			do_edit (s)
		return
	scripts = set ()
	newscript = None
	for s in spriteselect:
		if s[1]:
			continue
		spr = s[0]
		if not spr.script:
			if newscript is None:
				if spr.name not in data.script.data:
					newscript = spr.name
				else:
					n = 0
					while True:
						newscript = '%s-%03d' % (spr.name, n)
						if newscript not in data.script.data:
							break
						n += 1
			spr.script = newscript
		scripts.add (spr.script)
	if newscript is not None:
		update_editgui ()
	for s in scripts:
		do_edit (s)

def toggle_nohit (action = None):
	for s in spriteselect:
		if s[1]:
			continue
		s[0].nohit = not s[0].nohit
	update_editgui ()
	the_gui.statusbar = 'Toggled nohit property'

def clear_warp (action = None):
	for spr in spriteselect:
		remove_warptarget (spr[0])
		spr[0].warp = None
	spriteselect[:] = [s for s in spriteselect if not s[1]]
	update_editgui ()

def toggle_warp (action = None):
	spriteselect[:] = [(s[0], s[0].warp is not None and not s[1]) for s in spriteselect]
	update_editgui ()

def toggle_hard (action = None):
	for s in spriteselect:
		if s[1]:
			continue
		spr = s[0]
		spr.hard = not spr.hard
	update_editgui ()

def toggle_use_hard (action = None):
	for s in spriteselect:
		if s[1]:
			continue
		spr = s[0]
		spr.use_hard = not spr.use_hard
	update_editgui ()

def toggle_indoor (action = None):
	n = viewmap.get_pointed_map ()[2]
	if n not in data.world.map:
		return
	data.world.map[n].indoor = not data.world.map[n].indoor
	update_editgui ()

def map_insert (action = None):
	n = viewmap.get_pointed_map ()[2]
	if n in data.world.map:
		viewmap.mapsource = n
		return
	# Reregister all sprites, so they can pick up the new map.
	for s in data.world.sprite:
		s.unregister ()
	data.world.map[n] = dink.Map (data)
	if viewmap.mapsource in data.world.map:
		for y in range (8):
			for x in range (12):
				data.world.map[n].tiles[y][x] = data.world.map[viewmap.mapsource].tiles[y][x]
	for s in data.world.sprite:
		s.register ()
	update_maps ()
	viewmap.update ()

def map_delete (action = None):
	n = viewmap.get_pointed_map ()[2]
	if n not in data.world.map:
		return
	spr = list (data.world.map[n].sprite)
	for s in spr:
		if s.map is not None:
			s.map = None
		s.unregister ()
	del data.world.map[n]
	for s in spr:
		s.register ()
	if viewmap.mapsource == n:
		viewmap.mapsource = None
	update_maps ()
	viewmap.update ()

def map_lock (map = None):
	for s in spriteselect:
		if s[1]:
			continue
		if map is None:
			sx = s[0].x / 50 / 12
			sy = s[0].y / 50 / 8
			n = sy * 32 + sx + 1
			if n not in data.world.map:
				continue
		else:
			n = map
		s[0].unregister ()
		s[0].map = n
		s[0].register ()
	update_editgui ()

def sync ():
	if updating:
		# Don't sync while updating.
		return
	synccmd = the_gui.sync
	if synccmd:
		os.system (synccmd)
	for s in data.script.data:
		data.script.data[s] = open (os.path.join (tmpdir, s + os.extsep + 'c')).read ()
	data.info = open (os.path.join (tmpdir, 'info' + os.extsep + 'txt')).read ()
	for h in data.tile.hard:
		p = os.path.join (tmpdir, h + os.extsep + 'png')
		if os.path.exists (p):
			dink.make_hard_image (p).save (p)
			data.tile.hard[h] = (p, 0, os.stat (p).st_size)
	for l in range (10):
		data.layer_background[l] = bool (getattr (the_gui, 'layer%d_background' % l))
		data.layer_visible[l] = bool (getattr (the_gui, 'layer%d_visible' % l))

def clean_fs ():
	for s in data.script.data:
		os.unlink (os.path.join (tmpdir, s + os.extsep + 'c'))
	os.unlink (os.path.join (tmpdir, 'info' + os.extsep + 'txt'))
	for h in data.tile.hard:
		p = os.path.join (tmpdir, h + os.extsep + 'png')
		if os.path.exists (p):
			os.unlink (p)
	os.rmdir (tmpdir)

def new_game (root = None):
	global data, tmpdir, updating
	if data is not None:
		clean_fs ()
	if root is None:
		the_gui.title = 'Python Dink Editor'
	else:
		the_gui.title = os.path.basename (root) + ' - Python Dink Editor'
	reset_globals ()
	updating = True
	try:
		data = gtkdink.GtkDink (root, screenzoom)
	except:
		os.system (os.path.join (os.path.dirname (os.path.abspath (sys.argv[0])), 'makecache' + os.extsep + 'py'))
		data = gtkdink.GtkDink (root, screenzoom)
	w = viewmap.get_window ()
	if w:
		data.set_window (w)
	# initialize warp targets.
	for s in data.world.sprite:
		add_warptarget (s)
	tmpdir = tempfile.mkdtemp (prefix = 'pydink-scripts-')
	for s in data.script.data:
		open (os.path.join (tmpdir, s + os.extsep + 'c'), 'w').write (data.script.data[s])
	open (os.path.join (tmpdir, 'info' + os.extsep + 'txt'), 'w').write (data.info)
	sync ()
	the_gui.setworld = True
	update_maps ()
	the_gui.set_music_list = musiclist ()
	the_gui.set_sounds_list = soundslist ()
	the_gui.set_walk_list = [''] + collectionlist ()
	the_gui.set_idle_list = [''] + collectionlist ()
	the_gui.set_attack_list = [''] + collectionlist ()
	the_gui.set_death_list = [''] + collectionlist ()
	the_gui.set_seq_list = fullseqlist ()
	the_gui.set_touch_list = [''] + fullseqlist ()
	for i in range (10):
		setattr (the_gui, 'layer%d_background' % i, data.layer_background[i])
		setattr (the_gui, 'layer%d_visible' % i, data.layer_visible[i])
		setattr (the_gui, 'layer%d_presentation' % i, ((3, 0), (2, 1))[data.layer_background[i]][data.layer_visible[i]])
	the_gui.active_layer = 1
	updating = False
	viewmap.update ()
	scripts = data.script.data.keys ()
	scripts.sort ()
	the_gui.set_scripts = scripts

def new_layer ():
	#the_gui.statusbar = 'Active layer: %d' % the_gui.active_layer
	pass

def save (dirname = None):
	if dirname is None and data.root is None:
		show_save_as ()
	else:
		sync ()
		if data.save (dirname):
			the_gui.statusbar = 'Saved DMod to %s' % data.root
		else:
			the_gui.statusbar = 'Not saved, because there was something wrong (please report as a bug)'
		the_gui.title = os.path.basename (data.root) + ' - Python Dink Editor'
# }}}

# {{{ Main program
if len (sys.argv) == 2:
	root = sys.argv[1]
elif len (sys.argv) > 2:
	sys.stderr.write ('Give no arguments or only a game directory.\n')
	sys.exit (1)
else:
	root = None

viewmap = ViewMap ()
viewseq = ViewSeq ()
viewcollection = ViewCollection ()
viewtiles = ViewTiles ()
viewworld = ViewWorld ()

def show_open ():
	the_gui.show_open = True
def show_save_as ():
	the_gui.show_save_as = True
def show_about ():
	the_gui.show_about = True
def select_all ():
	global spriteselect
	spriteselect += [(s, False) for s in data.world.sprite if s.layer == the_gui.active_layer and (s, False) not in spriteselect]
	spriteselect += [(s, True) for s in data.world.sprite if s.layer == the_gui.active_layer and s.warp is not None and (s, True) not in spriteselect]
	View.update (viewmap)
def deselect_all ():
	global spriteselect
	spriteselect = []
	View.update (viewmap)
def select_invert ():
	global spriteselect
	other = [s for s in spriteselect if s[0].layer != the_gui.active_layer]
	spriteselect = [(s, False) for s in data.world.sprite if s.layer == the_gui.active_layer and (s, False) not in spriteselect] + other
	View.update (viewmap)
def save_as (dirname):
	if dirname is None:
		return
	save (dirname)
def jump ():
	target = (0, 0)
	if len (spriteselect) > 0:
		for s in spriteselect:
			spr = s[0]
			if s[1]:
				n = viewmap.make_global (spr.warp[0], spr.warp[1:])
			else:
				n = [spr.x, spr.y]
			target = (target[0] + n[0], target[1] + n[1])
		viewmap.goto ([target[x] / len (spriteselect) for x in range (2)])
def jump_next ():
	if len (spriteselect) > 0:
		viewmap.current_selection += 1
		if viewmap.current_selection >= len (spriteselect):
			viewmap.current_selection = 0
		s = spriteselect[viewmap.current_selection]
		spr = s[0]
		if s[1]:
			viewmap.goto (viewmap.make_global (s[0].warp[0], s[0].warp[1:]))
		else:
			viewmap.goto ([spr.x, spr.y])
		update_editgui ()

def play (n = None, x = None, y = None):
	sync ()
	the_gui.statusbar = 'Building and play-testing DMod; please wait'
	the_gui (1)
	if y is None:
		err = data.play ()
	else:
		err = data.play (n, x, y)
	show_error (err)
	the_gui.statusbar = 'Done play-testing'


events = {}

# Menubar
events['file_new'] = lambda x: new_game ()
events['file_open'] = lambda x: show_open ()
events['open'] = lambda x: new_game ()
events['file_save'] = lambda x: save ()
events['file_save_as'] = lambda x: show_save_as ()
events['save_as'] = lambda x: save_as ()
events['file_quit'] = lambda x: the_gui (False)
events['edit_deselect_all'] = lambda x: deselect_all ()
events['edit_select_all'] = lambda x: select_all ()
events['edit_invert_select'] = lambda x: select_invert ()
events['jump'] = lambda x: jump ()
events['jump_next'] = lambda x: jump_next ()
events['dmod_edit_info'] = lambda x: do_edit ('info', 'txt')
events['dmod_edit_start'] = lambda x: do_edit ('start')
events['dmod_edit_intro'] = lambda x: do_edit ('intro')
events['dmod_edit_init'] = lambda x: do_edit ('init')
events['dmod_edit_script'] = lambda x: do_edit (the_gui.dmod_script)
events['dmod_delete_script'] = lambda x: do_delete_script ()
events['dmod_build'] = lambda x: data.build ()
events['dmod_play'] = lambda x: play ()
events['sprite_edit'] = lambda x: edit_sprite_scripts ()
events['sprite_nohit'] = lambda x: toggle_nohit ()
events['sprite_toggle_warp'] = lambda x: toggle_warp ()
events['sprite_clear_warp'] = lambda x: clear_warp ()
events['sprite_hard'] = lambda x: toggle_hard ()
events['sprite_use_hard'] = lambda x: toggle_use_hard ()
events['map_insert'] = lambda x: map_insert ()
events['map_delete'] = lambda x: map_delete ()
events['map_edit_hard'] = lambda x: edit_map_hardness ()
events['map_edit'] = lambda x: edit_map_script ()
events['map_indoor'] = lambda x: toggle_indoor ()
events['help_about'] = lambda x: show_about ()

events['update_map'] = update_map_gui
events['update_layer'] = update_layer_gui
#events['update_world'] = update_world_gui
#events['update_tile'] = update_tile_gui
events['new_sprite'] = new_sprite
events['new_map'] = new_map
events['edit_map_script'] = edit_map_script
events['edit_map_hardness'] = edit_map_hardness
events['edit_script'] = edit_sprite_scripts
events['new_layer'] = new_layer
events['map_lock'] = map_lock

events['update_sprite_name'] = lambda: update_sprite_gui ('name', update_sprite_name, type = str)
events['update_sprite_walk'] = lambda: update_sprite_gui ('base_walk', update_sprite_collection, type = str)
events['update_sprite_idle'] = lambda: update_sprite_gui ('base_idle', update_sprite_collection, type = str)
events['update_sprite_attack'] = lambda: update_sprite_gui ('base_attack', update_sprite_collection, type = str)
events['update_sprite_die'] = lambda: update_sprite_gui ('base_death', update_sprite_collection, type = str)
events['update_sprite_seq'] = lambda: update_sprite_gui ('seq', update_sprite_seq, type = str)
events['update_sprite_touchseq'] = lambda: update_sprite_gui ('touchseq', update_sprite_seq, type = str)
events['update_sprite_warp'] = lambda: update_sprite_gui ('warp', update_sprite_warp)
events['update_sprite_warpmap'] = lambda: update_sprite_gui ('warpmap', update_sprite_warp_detail)
events['update_sprite_warpx'] = lambda: update_sprite_gui ('warpx', update_sprite_warp_detail)
events['update_sprite_warpy'] = lambda: update_sprite_gui ('warpy', update_sprite_warp_detail)
events['update_sprite_nohit'] = lambda: update_sprite_bool ('nohit')
events['update_sprite_hard'] = lambda: update_sprite_bool ('hard')
events['update_sprite_use_hard'] = lambda: update_sprite_bool ('use_hard')
events['update_sprite_crop'] = update_sprite_crop
events['update_sprite_left'] = lambda: update_sprite_gui ('left', update_sprite_crop_detail)
events['update_sprite_top'] = lambda: update_sprite_gui ('top', update_sprite_crop_detail)
events['update_sprite_right'] = lambda: update_sprite_gui ('right', update_sprite_crop_detail)
events['update_sprite_bottom'] = lambda: update_sprite_gui ('bottom', update_sprite_crop_detail)
events['update_sprite_sound'] = lambda: update_sprite_gui ('sound', type = str)
events['update_sprite_frame'] = lambda: update_sprite_gui ('frame')
events['update_sprite_brain'] = lambda: update_sprite_gui ('brain', type = str)
events['update_sprite_script'] = lambda: update_sprite_gui ('script', type = str)
events['update_sprite_vision'] = lambda: update_sprite_gui ('vision')
events['update_sprite_speed'] = lambda: update_sprite_gui ('speed')
events['update_sprite_timing'] = lambda: update_sprite_gui ('timing')
events['update_sprite_hitpoints'] = lambda: update_sprite_gui ('hitpoints')
events['update_sprite_strength'] = lambda: update_sprite_gui ('strength')
events['update_sprite_defense'] = lambda: update_sprite_gui ('defense')
events['update_sprite_experience'] = lambda: update_sprite_gui ('experience')
events['update_sprite_touch_damage'] = lambda: update_sprite_gui ('touch_damage')
events['update_sprite_gold'] = lambda: update_sprite_gui ('gold')
events['update_sprite_x'] = lambda: update_sprite_gui ('x')
events['update_sprite_y'] = lambda: update_sprite_gui ('y')
events['update_sprite_size'] = lambda: update_sprite_gui ('size')
events['update_sprite_que'] = lambda: update_sprite_gui ('que')
events['update_sprite_layer'] = update_sprite_layer
events['update_sprite_map'] = lambda: update_sprite_gui ('map')

inputs = ('active_layer', 'base_attack', 'base_attack_text', 'base_death', 'base_death_text', 'base_idle', 'base_idle_text', 'base_walk', 'base_walk_text', 'bottom', 'brain', 'crop', 'current_map', 'defense', 'dmod_num', 'dmod_script', 'experience', 'frame', 'gold', 'hard', 'hitpoints', 'indoor', 'layer', 'layer0_background', 'layer0_presentation', 'layer0_visible', 'layer1_background', 'layer1_presentation', 'layer1_visible', 'layer2_background', 'layer2_presentation', 'layer2_visible', 'layer3_background', 'layer3_presentation', 'layer3_visible', 'layer4_background', 'layer4_presentation', 'layer4_visible', 'layer5_background', 'layer5_presentation', 'layer5_visible', 'layer6_background', 'layer6_presentation', 'layer6_visible', 'layer7_background', 'layer7_presentation', 'layer7_visible', 'layer8_background', 'layer8_presentation', 'layer8_visible', 'layer9_background', 'layer9_presentation', 'layer9_visible', 'layers_num', 'left', 'map', 'map_hardness', 'map_music', 'map_num', 'map_script', 'map_text', 'name', 'size', 'sound', 'sound_text', 'speed', 'splash', 'sprite', 'sprite_num', 'sprite_text', 'statusbar', 'statuslabel', 'strength', 'timing', 'title', 'top', 'touch_damage', 'touchseq', 'touchseq_text', 'use_hard', 'vision', 'warp', 'warpmap', 'warpx', 'warpy', 'x', 'y', 'border_gc', 'default_gc', 'empty_gc', 'grid_gc', 'hard_gc', 'invalid_gc', 'noselect_gc', 'noshow_gc', 'paste_gc', 'path_gc', 'select_gc', 'warp_gc', 'white_gc', 'hardness_editor', 'script_editor', 'nobackingstore', 'sync')
outputs = ('about', 'error', 'nohit', 'preview', 'que', 'right', 'script', 'seq', 'seq_text', 'set_attack_list', 'set_death_list', 'set_idle_list', 'set_map_hardness_list', 'set_layer_edit', 'set_sprite_edit', 'setworld', 'setseq', 'setmap', 'settiles', 'setmap2', 'set_map_edit', 'set_map_list', 'set_music_list', 'set_num_frames', 'set_scripts', 'set_seq_list', 'set_sounds_list', 'set_spritelist', 'set_touch_list', 'set_walk_list', 'show_about', 'show_error', 'show_open', 'show_save_as', 'setcollection', 'set_dmod_edit')

the_gui = gui.Gui ('pydink', gtk = { 'viewmap': viewmap, 'viewseq': viewseq, 'viewcollection': viewcollection, 'viewtiles': viewtiles, 'viewworld': viewworld }, events = events, inputs = inputs, outputs = outputs)

the_gui.about = {
	'name': 'PyDink',
	'program_name': 'pde',
	'version': '0.2',
	'copyright': 'Copyright 2012-2013 Bas Wijnen <wijnen@debian.org>',
	'license': 'GNU Affero General Public License, version 3 or later (at your option). The full text of the license should be distributed with your package. If not, you can find it at http://www.gnu.org/licenses/agpl.html',
	'wrap_license': True,
	'website': 'https://github.com/wijnen/pydink',
	'website_label': 'Get the newest version from gihub',
	'authors': ('Bas Wijnen <wijnen@debian.org>', 'Special thanks to everyone on http://dinknetwork.com/forum.cgi', 'In particular MsDink for letting me test on her computer and Magicman for discussing the many bugs in the Dink engine', "And of course Seth for making Dink in the first place. It may be buggy as hell, but it's a great game anyway."),
	'artists': ('Seth Robinson, http://www.rtsoft.com',)}

data = None
new_game (root)

update_maps ()
updating = False

the_gui.set_sprite_edit = True
# Make sure the map is realized before showing the world.
the_gui.setmap = True
the_gui (1)
viewmap.realize ()
the_gui.setworld = True
the_gui.statusbar = 'Welcome to PyDink Editor'
the_gui ()

clean_fs ()
# }}}

#!/usr/bin/env python

import dink
import gtk

class play (gtk.DrawingArea):
	"Widget for playing dink."
	def __init__ (self, dat, scale):
		"Arguments: dink data and number of pixels per tile"
		self.data = data
		self.scale = scale
		self.offset = 20 * scale / 50
		gtk.DrawingArea.__init__ (self)
		self.set_can_focus (True)
		self.connect_after ('realize', self.start)
		self.pointer = True
		self.pointerbutton = None
		self.key = None
		self.quit = False
		self.brains = {
				'dink': self.dinkbrain,
				'bounce': self.bouncebrain,
				'duck': self.duckbrain,
				'pig': self.pigbrain,
				'mark': self.markbrain,
				'repeat': self.repeatbrain,
				'play': self.playbrain,
				'text': self.textbrain,
				'bisshop': self.bisshopbrain,
				'rook': self.rookbrain,
				'missile': self.missilebrain,
				'resize': self.resizebrain,
				'pointer': self.pointerbrain,
				'button': self.buttonbrain,
				'shadow': self.shadowbrain,
				'person': self.personbrain,
				'flare': self.flarebrain
				}
	def start (self):
		gtk.DrawingArea.realize (self)
		self.gc = gtk.gdk.gc (self.get_window ())
		self.move (None)
		self.pointerlast = self.pointerpos
		w = 12 * scale + 2 * self.offset
		h = 8 * scale + 80 * scale / 50
		self.buffer = gtk.gdk.pixmap (self.get_window (), w, h)
		self.bg = gtk.gdk.pixmap (self.get_window (), w, h)
		self.connect ('expose-event', self.expose)
		self.connect ('key-press-event', self.keypress)
		self.connect ('button-press-event', self.button_on)
		self.connect ('button-release-event', self.button_off)
		self.connect ('motion-notify-event', self.move)
		self.connect ('enter-notify-event', self.enter)
		self.set_size_request (w, h)
		self.add_events (gtk.gdk.KEY_PRESS_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.ENTER_NOTIFY_MASK)
		self.gc.set_foreground (self.data.script.title_color)
		self.buffer.draw_rectangle (self.gc, True, 0, 0, w, h)
		if self.data.script.title_bg != '':
			self.buffer.draw_pixbuf (None, self.data.image[self.data.script.title_bg], 0, 0, 0, 0, w, h)
		self.add_sprite (self.data.title_pointer_seq, self.data.title_pointer_frame, 0, 0, 'pointer')
		for spr in self.data.title_sprite:
			self.add_sprite (*spr)
		if self.data.title_music != '':
			self.play_music (self.data.title_music)
		self.get_window ().draw_drawable (self.gc, self.buffer, 0, 0, 0, 0, w, h);
		# Schedule first event immediately.
		self.current_time = 0
		gobject.idle_add (self.next_event)
	def next_event (self):
		self.current_time = self.events[0][0]
		while self.current_time == self.events[0][0]:
			event = self.events.pop (0)[1]
			if type (event) == Sprite:
				self.brains[event.brain] (event)
			elif type (event) == dink.Script:
				# TODO
				pass
			# TODO: handle event.
		if self.events != []:
			gobject.timeout_add (self.events[0].time - self.current_time, self.next_event)
		return False
	def play_music (self, music):
		pass
	def add_sprite (self, seq, frame, x, y, brain, script = ''):
		pass
	def expose (self, event):
		self.get_window ().draw_drawable (View.gc, self.buffer, event.area[0], event.area[1], event.area[0], event.area[1], event.area[2], event.area[3])
	def update (self):
		self.buffer.draw_drawable (self.gc, self.bg, 0, 0, 0, 0)
		self.sprites.sort (key = lambda x: x[0] - x[1].que)
		for s in self.sprites:
			(x, y), (left, top, right, bottom), box = self.get_box (s[1].size, s[0], s[2].frames[s[1].frame], (s[1].left, s[1].top, s[1].right, s[1].bottom))
			if type (s[2].name) == str:
				pb = self.get_pixbuf (self.pixbufs[s[2].name][s[1].frame])
			else:
				pb = self.get_pixbuf (self.cpixbufs[s[2].name[0]][s[2].name[1]][s[1].frame])
			if box != None:
				pb = pb.subpixbuf (box[0], box[1], box[2] - box[0], box[3] - box[1])
			w = (right - left) * self.scale / 50
			h = (bottom - top) * self.scale / 50
			if w > 0 and h > 0:
				pb = pb.scale_simple (w, h, gtk.gdk.INTERP_NEAREST)
				self.buffer.draw_pixbuf (None, pb, 0, 0, self.offset + left * self.scale / 50, top * self.scale / 50)
		self.expose ((0, 0, 0, 0, None, None))
		# TODO: status bar and lock stuff.
	def make_bg (self):
		# Draw tiles
		# Draw bg sprites
	def keypress (self, event):
		self.key = event.keyval
	def button_on (self, event):
		if self.pointer == False:
			return
		self.pointerbutton = True
	def button_off (self, event):
		if self.pointer == False:
			return
		self.pointerbutton = False
	def move (self, event):
		if self.pointer == False:
			return
		ex, ey, emask = self.get_window ().get_pointer ()
		self.pointerpos = (int (ex) - self.offset) * 50 / self.scale, int (ey) * 50 / self.scale
	def enter (self, event):
		self.grab_focus ()
	def tick (self):
		for s in self.sprites:
			if s.brain not in self.brains:
				continue
			self.brains[s.brain] (s)
			if s.seq != None:
				if s.frame < len (s.seq.frames):
					++s.frame
				elif s.brain == 'repeat':
					s.frame = 1
				else:
					s.seq = 0
					s.frame = 0
		self.pointerlast = self.pointerpos
		self.pointerbutton = None
		self.key = None
		self.update ()
		if not self.quit:
			# TODO: schedule next tick
			pass
		return self.quit
	def dinkbrain (self, sprite):
		if e.keyval == gtk.keysyms.Left:
			pass
		elif e.keyval == gtk.keysyms.Up:
			pass
		elif e.keyval == gtk.keysyms.Right:
			pass
		elif e.keyval == gtk.keysyms.Down:
			pass
		elif e.keyval == gtk.keysyms.Escape:
			pass
		elif e.keyval == gtk.keysyms.m:
			pass
		elif e.keyval == gtk.keysyms._6:
			pass
		else:
			pass
	def bouncebrain (self, sprite):
		pass
	def duckbrain (self, sprite):
		pass
	def pigbrain (self, sprite):
		pass
	def markbrain (self, sprite):
		pass
	def repeatbrain (self, sprite):
		pass
	def playbrain (self, sprite):
		pass
	def textbrain (self, sprite):
		pass
	def bisshopbrain (self, sprite):
		pass
	def rookbrain (self, sprite):
		pass
	def missilebrain (self, sprite):
		pass
	def resizebrain (self, sprite):
		pass
	def pointerbrain (self, sprite):
		if not self.pointer:
			return
		sprite.pos = self.pointerpos
	def buttonbrain (self, sprite):
		pass
	def shadowbrain (self, sprite):
		pass
	def personbrain (self, sprite):
		pass
	def flarebrain (self, sprite):
		pass

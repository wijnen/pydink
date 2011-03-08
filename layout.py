#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

#world
#	nnn-xx-yy
#		info.txt		script, tiles, hardness
#		sprite
#			id.txt		script, x, y, etc.
#tile
#	nn.png				tile map (00-41)
#	hard-nn.png			hardness for tile map (same range)
#	hard-nnn.png			other hardness (anything not in tile map, max 800)
#anim
#	name.gif			sequence
#	name.txt			info about name.gif if it exists, generated sequence otherwise
#sound.txt				list of name filename (number)?
#music.txt				list of name filename (number)?
#script
#	name.c				script to be preprocessed (sound and music names, possibly spacing)

import os
import re

def readlines (f):
	ret = {}
	while True:
		l = f.readline ():
		if l.strip () == '':
			break
		r = re.match (r'(.*)=(.*)', l.strip ())
		assert r != None
		assert r.group (1) not in ret
		ret[r.group (1)] = r.group (2)
	return ret

def get (d, member, default = None):
	if member not in d:
		assert default != None
		return default
	ret = d[member]
	del d[member]
	return ret

class World:
	def __init (self, parent):
		self.parent = parent
		for y in range (24):
			for x in range (32):
				n = y * 32 + x + 1
				dirname = os.path.join (parent.root, '%03d-%02d-%02d' % (n, x, y))
				if not os.path.exists (dirname):
					continue
				self.room[n].tiles = []
				f = open (os.path.join (dirname, "info.txt"))
				for ty in range (8):
					ln = f.readline ()
					self.room[n].tiles += (re.findall (r'\b(\d+),(\d+)\b', ln),)
					assert len (self.room[n].tiles) == 12
				r = re.match ('script = (.*)', f.readline ())
				self.room[n].script = r.group (1)
				r = re.match ('midi = (.*)', f.readline ())
				self.room[n].midi = r.group (1)
				ln = f.readline ().strip ()
				if ln == "indoor":
					self.room[n].indoor = True
				else:
					self.room[n].indoor = False
					assert ln == "outdoor"
				self.room[n].sprite = {}
				sdir = os.path.join (dirname, "sprite")
				for s in os.listdir (sdir):
					info = readlines (open (os.path.join (sdir, s)))
					self.room[n].sprite[s].x = int (get (info, 'x'))
					self.room[n].sprite[s].y = int (get (info, 'y'))
					self.room[n].sprite[s].seq = get (info, 'seq')
					self.room[n].sprite[s].frame = int (get (info, 'frame', 0))
					self.room[n].sprite[s].type = int (get (info, 'type', 1))	# 0 for background, 1 for person or sprite, 3 for invisible
					self.room[n].sprite[s].size = int (get (info, 'size', 100))
					self.room[n].sprite[s].active = bool (get (info, 'active', True))
					self.room[n].sprite[s].brain = get (info, 'brain')
					self.room[n].sprite[s].script = get (info, 'script')
					self.room[n].sprite[s].speed = int (get (info, 'speed', 1))
					self.room[n].sprite[s].base_walk = get (info, 'base_walk')
					self.room[n].sprite[s].base_idle = get (info, 'base_idle')
					self.room[n].sprite[s].base_attack = get (info, 'base_attack')
					self.room[n].sprite[s].base_hit = get (info, 'base_hit')
					self.room[n].sprite[s].timer = int (get (info, 'timer', 33))
					self.room[n].sprite[s].que = int (get (info, 'que', 0))
					self.room[n].sprite[s].hard = bool (get (info, 'hard', True))
					self.room[n].sprite[s].left = int (get (info, 'left', 0))
					self.room[n].sprite[s].top = int (get (info, 'top', 0))
					self.room[n].sprite[s].right = int (get (info, 'right', 0))
					self.room[n].sprite[s].bottom = int (get (info, 'bottom', 0))
					if 'warp_map' in info:
						self.room[n].sprite[s].warp_map = int (get (info, 'warp_map'))
						self.room[n].sprite[s].warp_x = int (get (info, 'warp_x'))
						self.room[n].sprite[s].warp_y = int (get (info, 'warp_y'))
					self.room[n].sprite[s].touch_seq = get (info, 'parm_seq')
					self.room[n].sprite[s].base_die = get (info, 'base_die')
					self.room[n].sprite[s].gold = int (get (info, 'gold'))
					self.room[n].sprite[s].hitpoints = int (get (info, 'hitpoints'))
					self.room[n].sprite[s].strength = int (get (info, 'strength'))
					self.room[n].sprite[s].defense = int (get (info, 'defense'))
					self.room[n].sprite[s].exp = int (get (info, 'exp'))
					self.room[n].sprite[s].sound = get (info, 'sound')
					self.room[n].sprite[s].vision = int (get (info, 'vision'))
					self.room[n].sprite[s].nohit = bool (get (info, 'nohit'))
					self.room[n].sprite[s].touch_damage = bool (get (info, 'touch_damage'))
					assert info == {}

class Tile:

class Anim:
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		for a in os.listdir (os.path.join (parent.root, "anim")):
			ext = os.extsep + 'txt'
			if not a.endswith (ext):
				continue
			base = a[:-len (ext)]
			self.data[base].frames = []
			gif = base + os.extsep + 'gif'
			if os.path.exists (gif):
				f = Image.open (gif)
				while True:
					self.data[base].frames += ((f.info['duration'], f.convert ('RGBA').tostring ()),)
					try:
						f.seek (len (self.data[base].frames))
					except EOFError:
						break
			f = open (a)
			while True:
				info = readlines (f)
				if len (self.data[base].desc) >= len (self.frames):
					if info == {}:
						break
				else:
					self.data[base].desc += (get (info, 'anim', base), get (info, 'frame', 0))
				self.data[base].special = int (get (info, 'special', 0))
				self.data[base].x = int (get (info, 'x'))
				self.data[base].y = int (get (info, 'y'))
				if 'left' in info:
					self.data[base].left = int (get (info, 'left'))
					self.data[base].right = int (get (info, 'right'))
					self.data[base].top = int (get (info, 'top'))
					self.data[base].bottom = int (get (info, 'bottom'))
				self.data[base].type = get (info, 'type', 'normal')
				assert self.data[base].type in ('normal', 'black', 'leftalign', 'noanim')
				assert info == {}

class Sound:
	def __init__ (self, parent):
		self.parent = parent
		self.sound = {}
		self.music = {}
		for l in open (os.path.join (parent.root, "sound.txt")).readlines ():
			w = l.split ()
			assert len (w) == 2 or len (w) == 3
			if len (w) == 2:
				w += (-1,)
			assert w[0] not in self.sound
			self.sound[w[0]] = w[1:]
		for l in open (os.path.join (parent.root, "music.txt")).readlines ():
			w = l.split ()
			assert len (w) == 2 or len (w) == 3
			if len (w) == 2:
				w += (-1,)
			assert w[0] not in self.music
			self.music[w[0]] = w[1:]

class Script:
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		for s in os.listdir (os.path.join (parent.root, "script")):
			ext = os.extsep + 'c'
			if not s.endswith (ext):
				continue
			base = s[:-len (ext)]
			assert base not in self.data
			self.data[base] = open (s).read ()

class Dink:
	def read (self, root):
		self.root = root
		self.world = World (self)
		self.tile = Tile (self)
		self.anim = Anim (self)
		self.sound = Sound (self)
		self.script = Script (self)

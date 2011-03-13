#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

#world
#	nnn-xx-yy
#		info.txt		script, tiles, hardness
#		sprite
#			id.txt		script, x, y, etc.
#tile
#	name-tile.png			tile map (00-41)
#	name-hard.png			hardness for tile map, or for screen
#anim
#	name.gif			sequence
#	name.txt			info about name.gif if it exists, generated sequence otherwise
#sound.txt				list of name filename (number)?
#music.txt				list of name filename (number)?
#script
#	name.c				script to be preprocessed (sound and music names, possibly spacing)

import os
import re

# brain 0: no brain -- sprite will not do anything automatically
# brain 1: Human [that is, sprite 1 / Dink] brain.
# brain 2: ["Dumb Sprite Bouncer", per DinkEdit.  See below.]
# brain 3: Duck brain.
# brain 4: Pig brain.
# brain 5: When seq is done, kills but leaves last frame drawn to the
# background
# brain 6: Repeat brain - does the active SEQ over and over.
# brain 7: Same as brain 5 but does not draw last frame to the background.
# [brain 8: text sprite brain]
# brain 9: Person/monster ([Only] diagonals)
# brain 10: Person/monster ([No] diagonals)
# brain 11: Missile brain - repeats SEQ [compare brain 17].
# brain 12: Will shrink/grow to match size in sp_brain_parm(), then die
# [WITHOUT giving any experience...]
# brain 13: Mouse brain (for intro, the pointer)
# (do a set_keep_mouse() to use inside game as well)
# brain 14: Button brain.  (intro buttons, can be used in game as well)
# brain 15: Shadow brain.  Shadows for fireballs, etc.
# brain 16: Smart People brain.  They can walk around, stop and look.
# brain 17: Missile brain, [like 11] but kills itself when SEQ is done.

brains = ['none', 'human', 'bounce', 'duck', 'pig', 'mark', 'repeat', 'play', 'text', 'bisshop', 'rook', 'missile', 'resize', 'pointer', 'button', 'shadow', 'person', 'spark']

the_globals = {
		"exp": 0,
		"strength": 3,
		"defense": 0,
		"cur_weapon": 0,
		"cur_magic": 0,
		"gold": 0,
		"magic": 0,
		"magic_level": 0,
		"vision": 0,
		"result": 0,
		"speed": 1,
		"timing": 0,
		"lifemax": 10,
		"life": 10,
		"level": 1,
		"player_map": 1,
		"last_text": 0,
		"update_status": 0,
		"missile_target": 0,
		"enemy_sprite": 0,
		"magic_cost": 0,
		"missle_source": 0
	}

def readlines (f):
	ret = {}
	while True:
		l = f.readline ()
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

def make_lsb (num, size):
	ret = ''
	for i in range (size):
		ret += '%c' % (num & 0xff)
		num >>= 8
	return ret

def make_string (s, size):
	assert len (s) < size
	return s + '\0' * (size - len (s))

def token (script, allow_comment = False):
	s = lstrip (script)
	if s == '':
		return None, None, False
	while True:
		if s.startswith ('//'):
			p = s.find ('\n', 2)
			if p < 0:
				if not allow_comment:
					continue
				return s, '', False
		if s.startswith ('/*'):
			p = s.find ('*/', 2)
			assert p >= 0
			if not allow_comment:
				continue
			return s[:p + 2], s[p + 2:].lstrip (), False
		break
	l = ['&&', '||', '==', '!=', '>=', '<=', '>', '<', '!', '+=', '-=', '/=', '*=', '+', '-', '*', '/', ',', ';', '{', '}', '?', ':']
	for i in l:
		if s.startswith (i):
			return i, s[len (i):].lstrip (), False
	if s[0] == '"':
		p = s.find ('"', 1)
		assert p >= 0
		n = s.find ('\n', 1)
		assert n == -1 or n > p
		return s[:p + 1], s[p + 1:].lstrip (), False
	is_name = True
	r = re.match ('[a-zA-Z_][a-zA-Z_0-9]*', s)
	if r == None:
		is_name = False
		r = re.match ('[0-9]+', s)
		assert r != None
	key = r.group (0)
	return key, s[len (key):].lstrip (), is_name

def push (ret, operators):
	args = operators[-1][1]
	r = ret[:-args]
	ret = ret[:-args]
	ret += ([operators[-1][0], r],)
	operators = operators[:-1]
	return ret, operators

max_tmp = 0
current_tmp = 0
def build (expr, as_bool):
	"""Build an expression or subexpression. Return before, expr"""
	global current_tmp
	if type (expr) == str:
		assert not as_bool
		if as_bool:
			return expr + ' != 0'
		else:
			return expr, ''
	if len (expr) == 3:
		# function call: name, args, before
		assert not as_bool
		return expr[0] + ' (' + ', '.join (expr[1]) + ')', expr[2]
	if expr[0] in ['==', '!=', '<=', '>=', '<', '>']:
		assert as_bool
		e0, b0 = build (expr[1][0], False)
		e1, b1 = build (expr[1][1], False)
		return e0 + ' ' + expr[0] + ' ' + e1, b0 + b1
	if expr[0] in ['&&', '||']:
		assert as_bool
		e0, b0 = build (expr[1][0], True)
		e1, b1 = build (expr[1][1], True)
		tmp = '&tmp%d' % current_tmp
		current_tmp += 1
		if expr[0] == '&&':
			return tmp + ' == 1', b0 + b1 + tmp + ' = 0;\nif (' + e0 + ')\n{\nif (' + e1 + ')\n' + tmp + ' = 1;\n}\n'
		else:
			return tmp + ' == 1', b0 + b1 + tmp + ' = 0;\nif (' + e0 + ')\n' + tmp + ' = 1;\nif (' + e1 + ')\n' + tmp + ' = 1;\n'
	assert expr[0] in ['*', '/', '+', '-', '!']
	assert not as_bool
	tmp = '&tmp%d' % current_tmp
	current_tmp += 1
	if len (expr[1]) == 2:
		e0, b0 = build (expr[1][0], False)
		e1, b1 = build (expr[1][1], False)
	else:
		e0, b0 = '0', ''
		e1, b1 = build (expr[1][0], False)
	if expr[0] == '+' or expr[0] == '-':
		op = expr[0] + '='
	else:
		op = expr[0]
	return tmp, b0 + b1 + '%s = %s;\n%s %s %s;\n' % (tmp, e0, tmp, op, e1)

def parse_expr (script, allow_cmd = False, restart = True, as_bool = None):
	assert as_bool != None
	global current_tmp, max_tmp
	if restart:
		if current_tmp > max_tmp:
			max_tmp = current_tmp
		current_tmp = 0
	need_operator = False
	ret = []
	operators = []
	while True:
		t, script, isname = token (script, True)
		if need_operator:
			if t == ')' and '(' in operators:
				while operators[-1] != ['(', 0, 100]:
					ret, operators = push (ret, operators)
				continue
			if t == ',' or t == ';' or t == ')':
				assert ['(', 0, 100] not in operators
				while operators != []:
					ret, operators = push (ret, operators)
				assert len (ret) == 1
				if allow_cmd:
					assert ret[0][0] == '='
					e, b = build (ret[0][1][1], as_bool = False)
					return ret[0][1][0] + ' = ' + e, b, script
				e, b = build (ret[0], as_bool)
				return e, b, script
			if allow_cmd and t == '=':
				# assignments are almost never allowed in an expression.
				assert operators == [] and len (ret) == 1 and ret[0] == '&'
				while operators != [] and operators[-1][2] < 6:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 6])
			elif t in ['==', '!=', '>=', '<=', '>', '<']:
				while operators != [] and operators[-1][2] < 5:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 5])
			elif t == '||':
				while operators != [] and operators[-1][2] < 4:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 4])
			elif t == '&&':
				while operators != [] and operators[-1][2] < 3:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 3])
			elif t in ['+', '-']:
				while operators != [] and operators[-1][2] < 2:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 2])
			elif t in ['*', '/']:
				while operators != [] and operators[-1][2] < 1:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 1])
		else:
			if t == '(':
				operators += (['(', 0, 100],)
			elif t in ['+', '-', '!']:
				operators += ([t, 1, 0],)
			else:
				assert t and (isname or (t[0] >= '0' and t[0] <= '9'))
				if isname:
					if script != '' and script[0] == '(':
						# TODO: handle special arguments of:
						# add_item
						# add_magic
						# create_sprite
						# editor_type
						# get_rand_sprite_with_this_brain
						# get_sprite_with_this_brain
						# playmidi
						# playsound
						# preload_seq
						# sp_base_attack
						# sp_base_death
						# sp_base_idle
						# sp_base_walk
						# sp_brain
						# sp_sound
						args = []
						b = ''
						if script[0] == ')':
							script = script[1:]
						else:
							while True:
								if script[0] == '"':
									p = script.find ('"', 1)
									assert p >= 0
									args += script[:p + 1]
									script = script[p + 1:]
								else:
									a, bp, script = parse_expr (script, restart = False, as_bool = False)
									args += (a,)
									b += bp
								t, script, isname = token (script, True)
								if t != ',':
									break
							assert t == ')'
							ret += ([name, args, b],)
							need_operator = True
							continue
					ret += ('&' + t[0],)
				else:
					ret += (t[0],)
				need_operator = True

def preprocess (script, dink):
	the_locals = []
	ret = ''
	indent = []
	numlabels = 0
	atend = ''
	while True:
		i = '\t' * len (indent)
		t, script, isname = token (script, True)
		if t == 'else':
			ret += i + 'else\n'
			# don't do the atend code just yet.
			continue
		if not t:
			break
		if t.startswith ('//') or t.startswith ('/*'):
			ret += i + t
			continue
		if len (indent) == 0:
			assert t == 'void'
			t, script, isname = token (script)
			assert isname
			name = t
			t, script, isname = token (script)
			assert t == '('
			t, script, isname = token (script)
			if t == 'void':
				t, script, isname = token (script)
			assert t == ')'
			t, script, isname = token (script)
			assert t == '{'
			indent += ('',)
			ret += 'void %s ()\n{\n' % name
			continue
		ret += realatend
		realatend = ''
		if t == '{':
			indent += (atend,)
			atend = ''
			continue
		if t == '}':
			assert atend == ''
			ret += i[:-1] + '}\n' + indent[-1]
			indent = indent[:-1]
			continue
		if t == 'while':
			t, script, isname = token (script)
			assert t == '('
			e, before, script = parse_expr (script, as_bool = True)
			t, script, isname = token (script)
			assert t == ')'
			start = 'while%d' % numlabels
			numlabels += 1
			end = 'while%d' % numlabels
			numlabels += 1
			ret += i + start + ':\n' + before + i + 'if (' + e + ') goto ' + end + '\n'
			atend = i + 'goto ' + start + '\n' + i + end + ':\n' + atend
			continue
		elif t == 'for':
			# for (i = 0; i < 4; ++i) foo;
			# i = 0;
			# loop:
			# 	if (!(i < 4))
			#		goto end
			# 	foo;
			#	++i;
			# 	goto loop
			# end:
			t, script, isname = token (script)
			assert t == '('
			if script[0] != ';':
				e1, b1, script = parse_expr (script, allow_cmd = True, as_bool = False)
			else:
				e1, b1 = '', ''
			t, script, isname = token (script)
			assert t == ';'
			e2, b2, script = parse_expr (script, as_bool = True)
			t, script, isname = token (script)
			assert t == ';'
			if script[0] != ')':
				e3, b3, script = parse_expr (script, allow_cmd = True, as_bool = False)
			else:
				e3, b3 = '', ''
			t, script, isname = token (script)
			assert t == ')'
			start = 'for%d' % numlabels
			numlabels += 1
			end = 'for%d' % numlabels
			numlabels += 1
			ret += b1 + i + e1 + ';\n' + i + start + ':\n' + b2 + i + 'if (' + e2 + ') goto ' + end + '\n'
			atend = b3 + i + e3 + ';\n' + i + 'goto ' + start + '\n' + i + end + ':\n' + atend
			continue
		elif t == 'if':
			t, script, isname = token (script)
			assert t == '('
			e, before, script = parse_expr (script, as_bool = True)
			t, script, isname = token (script)
			assert t == ')'
			ret += before + i + 'if (' + e + ')\n'
			# Don't add the atend code here.
			continue
		elif t == 'int':
			t, script, isname = token (script)
			assert isname
			name = t
			if name not in the_locals:
				the_locals += (name,)
			t, script, isname = token (script)
			if t == '=':
				e, before, script = parse_expr (script, as_bool = False)
				ret += before + i + 'int &' + name + ' = ' + e + ';\n'
			else:
				ret += i + 'int &' + name + ';\n'
			t, script, isname = token (script)
			assert t == ';'
		else:
			assert isname
			name = t
			t, script, isname = token (script)
			if t in ['=', '+=', '-=']:
				if name not in the_locals:
					global the_globals
					the_globals[name] = 0
				op = t
				e, before, script = parse_expr (script, as_bool = False)
				t, script, isname = token (script)
				assert t == ';'
				ret += before + i + name + ' ' + op + ' ' + e + ';\n'
			elif t in ['*=', '/=']:
				# Really, the target language is too broken for words...
				op = t[0]
				e, before, script = parse_expr (script, as_bool = False)
				t, script, isname = token (script)
				assert t == ';'
				ret += before + i + name + ' ' + op + ' ' + e + ';\n'
			else:
				assert t == '('
				global current_tmp, max_tmp
				if current_tmp > max_tmp:
					max_tmp = current_tmp
				current_tmp = 0
				if name == 'choice':
					# TODO: title and settings.
					b = ''
					c = i + 'choice_start ();\n'
					while True:
						t, script, isname = token (script)
						if t[0] != '"':
							e, before, script = parse_expr (t + script, restart = False, as_bool = True)
							t, script, isname = token (script)
							assert t[0] == '"'
							b += before
							t = e + ' ' + t
						c += i + t + '\n'
						t, script, isname = token (script)
						if t == ')':
							break
						assert t == ','
					ret += b + c + i + 'choice_end ();\n'
				else:
					b = ''
					f = i + name + ' ('
					if script[0] == ')':
						break
					while True:
						e, before, script = parse_expr (script, restart = False, as_bool = False)
						f += e
						b += before
						t, script, isname = token (script)
						if t == ')':
							break
						assert t == ','
						ret += ', '
					ret += ');\n'
		realatend = atend
		atend = ''
	return ret

class World:
	def __init__ (self, parent):
		self.parent = parent
		self.room = {}
		for y in range (24):
			for x in range (32):
				n = y * 32 + x + 1
				dirname = os.path.join (parent.root, '%03d-%02d-%02d' % (n, x, y))
				if not os.path.exists (dirname):
					continue
				self.room[n].tiles = []
				f = open (os.path.join (dirname, "info" + os.extsep + "txt"))
				for ty in range (8):
					ln = f.readline ()
					self.room[n].tiles += ([(x[0], int (x[1]), int (x[2])) for x in [y.split (',') for y in ln.split ()]],)
					assert len (self.room[n].tiles[-1]) == 12
				info = readlines (f)
				self.room[n].hard = get (info, 'hard', '')
				self.room[n].script = get (info, 'script', '')
				self.room[n].music = get (info, 'music', '')
				self.room[n].indoor = bool (get (info, 'indoor', True))
				assert info == {}
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
					self.room[n].sprite[s].brain = get (info, 'brain', '')
					self.room[n].sprite[s].script = get (info, 'script', '')
					self.room[n].sprite[s].speed = int (get (info, 'speed', 1))
					self.room[n].sprite[s].base_walk = get (info, 'base_walk', '')
					self.room[n].sprite[s].base_idle = get (info, 'base_idle', '')
					self.room[n].sprite[s].base_attack = get (info, 'base_attack', '')
					self.room[n].sprite[s].base_hit = get (info, 'base_hit', '')
					self.room[n].sprite[s].timer = int (get (info, 'timer', 33))
					self.room[n].sprite[s].que = int (get (info, 'que', 0))
					self.room[n].sprite[s].hard = bool (get (info, 'hard', True))
					self.room[n].sprite[s].left = int (get (info, 'left', 0))
					self.room[n].sprite[s].top = int (get (info, 'top', 0))
					self.room[n].sprite[s].right = int (get (info, 'right', 0))
					self.room[n].sprite[s].bottom = int (get (info, 'bottom', 0))
					self.room[n].sprite[s].warp = [int (x) for x in get (info, 'warp', '').split (',')]
					self.room[n].sprite[s].touch_seq = get (info, 'touch_seq', '')
					self.room[n].sprite[s].base_die = get (info, 'base_die', '')
					self.room[n].sprite[s].gold = int (get (info, 'gold', 0))
					self.room[n].sprite[s].hitpoints = int (get (info, 'hitpoints', 0))
					self.room[n].sprite[s].strength = int (get (info, 'strength', 0))
					self.room[n].sprite[s].defense = int (get (info, 'defense', 0))
					self.room[n].sprite[s].exp = int (get (info, 'exp', 0))
					self.room[n].sprite[s].sound = get (info, 'sound', '')
					self.room[n].sprite[s].vision = int (get (info, 'vision', 0))
					self.room[n].sprite[s].nohit = bool (get (info, 'nohit', False))
					self.room[n].sprite[s].touch_damage = int (get (info, 'touch_damage', 0))
					assert info == {}
	def write (self, root):
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink.dat'), "wb")
		ddat.write ('\0' * 24)
		rooms = []
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 2))
				continue
			rooms += (self.room[i],)
			# Note that the write is after the append, because the index must start at 1.
			ddat.write (make_lsb (len (rooms), 2))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 2))
				continue
			ddat.write (make_lsb (self.parent.sound.find_music (self.room[i].music), 2))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.room or not self.room[i].indoor:
				ddat.write (make_lsb (0, 2))
			else:
				ddat.write (make_lsb (1, 2))
		# Write map.dat
		mdat = open (os.path.join (root, 'map.dat'), "wb")
		for s in rooms:
			mdat.write ('\0' * 20)
			# tiles and hardness
			for y in range (8):
				for x in range (12):
					bmp, tx, ty = rooms[s].tiles[y][x]
					mdat.write (make_lsb (self.parent.tile.find_bmp (bmp) * 128 + ty * 12 + tx, 4))
					mdat.write ('\0' * 4)
					mdat.write (make_lsb (self.parent.tile.find_hard (rooms[s].hard, x, y, bmp, tx, ty), 4))
					mdat.write ('\0' * 68)
			mdat.write ('\0' * 320)
			# sprites
			# sprite 0 is never used...
			mdat.write ('\0' * 220)
			for sp in rooms[s].sprite:
				spr = rooms[s].sprite[sp]
				mdat.write (make_lsb (spr.x, 4))
				mdat.write (make_lsb (spr.y, 4))
				mdat.write (make_lsb (spr.seq, 4))
				mdat.write (make_lsb (spr.frame, 4))
				mdat.write (make_lsb (spr.type, 4))
				mdat.write (make_lsb (spr.size, 4))
				mdat.write (make_lsb (int (spr.active), 4))
				mdat.write (make_lsb (0, 4))	# rotation
				mdat.write (make_lsb (0, 4))	# special
				mdat.write (make_lsb (brains.index (spr.brain), 4))
				mdat.write (make_string (spr.script, 14))
				mdat.write ('\0' * 38)
				mdat.write (make_lsb (spr.speed, 4))
				mdat.write (make_lsb (spr.base_walk, 4))
				mdat.write (make_lsb (spr.base_idle, 4))
				mdat.write (make_lsb (spr.base_attack, 4))
				mdat.write (make_lsb (spr.base_hit, 4))
				mdat.write (make_lsb (spr.timer, 4))
				mdat.write (make_lsb (spr.que, 4))
				mdat.write (make_lsb (spr.hard, 4))
				mdat.write (make_lsb (spr.left, 4))
				mdat.write (make_lsb (spr.top, 4))
				mdat.write (make_lsb (spr.right, 4))
				mdat.write (make_lsb (spr.bottom, 4))
				if spr.warp != []:
					mdat.write (make_lsb (0, 4))
					mdat.write (make_lsb (spr.warp[0], 4))
					mdat.write (make_lsb (spr.warp[1], 4))
					mdat.write (make_lsb (spr.warp[2], 4))
				mdat.write (make_lsb (spr.touch_seq, 4))
				mdat.write (make_lsb (spr.base_die, 4))
				mdat.write (make_lsb (spr.gold, 4))
				mdat.write (make_lsb (spr.hitpoints, 4))
				mdat.write (make_lsb (spr.strength, 4))
				mdat.write (make_lsb (spr.defense, 4))
				mdat.write (make_lsb (spr.exp, 4))
				mdat.write (make_lsb (self.parent.sound.find_sound (spr.sound), 4))
				mdat.write (make_lsb (spr.vision, 4))
				mdat.write (make_lsb (int (spr.nohit), 4))
				mdat.write (make_lsb (spr.touch_damage, 4))
				mdat.write ('\0' * 20)
			# base script
			mdat.write (make_string (rooms[s].script, 21))
			mdat.write ('\0' * 1019)

class Tile:
	def __init__ (self, parent):
		self.parent = parent
		self.hard = {}
		self.tile = {}
		for t in os.listdir (os.path.join (parent.root, "tile")):
			ext = os.extsep + 'png'
			h = '-hard' + ext
			if not t.endswith (h):
				continue
			base = t[:-len (h)]
			t = base + '-tile' + os.extsep + 'png'
			if os.path.exists (t):
				self.tile[base] = Image.open (t).convert ('RGBA')
			self.hard[base] = Image.open (h).convert ('RGBA')
	def find_bmp (self, name):
		assert name in self.tile
		return self.tile.keys ().index (name)
	def find_hard (self, hard, x, y, bmp, tx, ty):
		if hard != '':
			assert hard in self.hard
			return self.map[hard][y][x]
		assert bmp in self.hard
		return self.map[bmp][ty][tx]
	def write (self, root):
		# Write tiles/*
		# Write hard.dat
		d = os.path.join (root, 'tiles')
		if not os.path.exists (d):
			os.mkdir (d)
		h = open (os.path.join (root, 'hard.dat'), "wb")
		hmap = []
		self.map = {}
		for t in self.hard:
			if t in self.tile:
				self.tile.save (os.path.join (d, t + os.extsep + 'bmp'))
			self.map[t] = [None] * 8
			for y in range (8):
				self.map[t][y] = [None] * 12
				for x in range (12):
					if i.size[0] < (x + 1) * 50 or i.size[1] < (y + 1) * 50:
						continue
					tile = i.crop ((x * 50, y * 50, 50, 50))
					s = tile.tostring ()
					try:
						m = hmap.index (s)
					except ValueError:
						# Not in map yet; add new tile to file and map.
						m = len (hmap)
						for ty in range (50):
							for tx in range (50):
								p = tile.getpixel ((tx, ty))
								if p == (0, 0, 0):
									h.write ('\0')
								elif p == (255, 255, 255):
									h.write ('\1')
								elif p == (0, 0, 255):
									h.write ('\2')
								else:
									raise ValueError ('invalid pixel in hard tile')
							h.write ('\0')	# junk
						h.write ('\0' * 58)	# junk
						hmap += (s,)
					self.map[t][y][x] = m
		assert len (hmap) <= 800
		h.write ('\0' * (51 * 51 + 1 + 6) * (800 - len (hmap)))
		for t in self.tile:
			m = self.map[t]
			for y in range (8):
				for x in range (12):
					h.write (make_lsb (m[y][x], 4))
		h.write ('\0' * (8000 - len (self.tile) * 8 * 12 * 4))

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
					self.data[base].frames += ((f.info['duration'], f.convert ('RGBA')),)
					try:
						f.seek (len (self.data[base].frames))
					except EOFError:
						break
			f = open (a)
			self.data[base].desc = []
			while True:
				info = readlines (f)
				if len (self.data[base].desc) >= len (self.frames):
					# these are generated frames.
					if info == {}:
						# no more generated frames for this animation.
						break
					self.data[base].desc += (get (info, 'anim', base), int (get (info, 'frame', 0)))
				else:
					# these frames have images with them.
					self.data[base].desc += (None,)
				s = get (info, 'special', False)
				if s != False:
					self.data[base].special = len (self.data[base].desc) - 1
				self.data[base].special = bool (get (info, 'now', False))
				if 'x' in info:
					self.data[base].desc[-1].x = int (get (info, 'x'))
					self.data[base].desc[-1].y = int (get (info, 'y'))
					self.data[base].desc[-1].left = int (get (info, 'left'))
					self.data[base].desc[-1].right = int (get (info, 'right'))
					self.data[base].desc[-1].top = int (get (info, 'top'))
					self.data[base].desc[-1].bottom = int (get (info, 'bottom'))
				self.data[base].type = get (info, 'type', 'normal')
				assert self.data[base].type in ('normal', 'black', 'leftalign', 'noanim')
				assert info == {}
	def find_seq (self, name):
		return self.data.index (name)
	def write (self, root):
		# Write graphics/*
		# Write dink.ini
		d = os.path.join (root, 'graphics')
		if not os.path.exists (d):
			os.mkdir (d)
		ini = open (os.path.join (root, 'dink.ini'), 'w')
		for seq, g in zip (range (len (self.data)), self.data):
			if len (self.data[g].frames) > 0:
				delay = self.data[g].frames[0].delay
				if self.data[g].now:
					now = '_now'
				else:
					now = ''
				if 'x' in dir (self.data[g]):
					ini.write ('load_sequence%s graphics\\%s- %d %d %d %d %d %d %d %d %d\n' % (now, g, seq, delay, self.data[g].desc[0].x, self.data[g].desc[0].y, self.data[g].desc[0].left, self.data[g].desc[0].top, self.data[g].desc[0].right, self.data[g].desc[0].bottom))
				else:
					ini.write ('load_sequence%s graphics\\%s- %d %d\n' % (now, g, seq, delay))
				for n, f in zip (range (len (g.frames)), g.frames):
					f.save (os.path.join (d, g + '-%02d' + os.extsep + 'bmp'))
				for f in range (len (self.data[g].desc)):
					if f >= len (self.data[g].frames):
						ini.write ('set_frame_frame %d %d %d %d\n', (seq, f, self.getseq (self.data[g].desc[f][0]), self.data[g].desc[f][1]))
					if (self.data[g].desc[0].x, self.data[g].desc[0].y, self.data[g].desc[0].left, self.data[g].desc[0].right, self.data[g].desc[0].top, self.data[g].desc[0].bottom) != (self.data[g].desc[f].x, self.data[g].desc[f].y, self.data[g].desc[f].left, self.data[g].desc[f].right, self.data[g].desc[f].top, self.data[g].desc[f].bottom):
						ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\n' % (seq, f, self.data[g].desc[f].x, self.data[g].desc[f].y, self.data[g].desc[f].left, self.data[g].desc[f].top, self.data[g].desc[f].right, self.data[g].desc[f].bottom))
					if self.data[g].frames[f].delay != delay:
						ini.write ('set_frame_delay %d %d %d\n' % (seq, f, self.data[g].frames[f].delay))
					if f != 0 and self.data[g].special == f:
						ini.write ('set_frame_special %d %d\n' % (seq, f))
	def getseq (name):
		for seq, g in zip (range (len (self.data)), self.data):
			if name == g:
				return seq
		raise ValueError ("sequence not found")

class Sound:
	def __init__ (self, parent):
		self.parent = parent
		ext = os.extsep + 'wav'
		self.sound = [s[:-len (ext)] for s in os.listdir (os.path.join (parent.root, "sound")) if s.endswith (ext)]
		ext = os.extsep + 'mid'
		self.music = [s[:-len (ext)] for s in os.listdir (os.path.join (parent.root, "music")) if s.endswith (ext)]
	def find_sound (self, name):
		"""Find wav file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		assert name in self.sound
		return self.sound.index (name) + 1
	def find_music (self, name):
		"""Find midi file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		assert name in self.music
		return self.music.index (name) + 1
	def write (self, root):
		# Write sound/*
		dst = os.path.join (root, 'sound')
		if not os.path.exists (dst):
			os.mkdir (dst)
		src = os.path.join (self.parent.root, 'sound')
		for s in self.sound:
			f = s + os.extsep + 'wav'
			open (os.join (dst, f), 'w').write (open (os.join (src, f)).read ())
		for s in range (len (self.music)):
			f = self.music[s] + os.extsep + 'mid'
			open (os.join (dst, str (s + 1) + os.extsep + 'mid'), 'w').write (open (os.join (src, f)).read ())

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
		f = open (os.path.join (parent.root, "title.txt"))
		self.title_music = f.readline ().strip ()
		self.title = [x.split () for x in f.readlines () if x != '' and x[0] != '#']
	def write (self, root):
		# Write Story/*
		d = os.path.join (root, 'story')
		if not os.path.exists (d):
			os.mkdir (d)
		for name in self.data:
			f = open (os.path.join (d, name + os.extsep + 'c'), 'w')
			f.write (preprocess (self.data[name], self.parent))
		# Write start.c
		s = open (os.path.join (d, 'start' + os.extsep + 'c'), 'w')
		s.write ('void main ()\n{')
		for n, snd in zip (len (self.parent.sound.sound), self.parent.sound.sound):
			s.write ('\tload_sound ("%s.wav", %d);\n' % (snd, n))
		s.write ('''\
set_dink_speed (3);
sp_frame_delay (1,0);
fill_screen (0);
sp_seq (1, 0);
sp_brain (1, 13);
sp_pseq (1,10);
sp_pframe (1,8);
sp_que (1,20000);
sp_noclip (1, 1);
int &crap;
''')
		for t in self.title:
			s.write ('''\
&crap = create_sprite (%d, %d, %d, %d, %d);
sp_script(&crap, "%s");
sp_noclip(&crap, 1);
sp_touch_damage(&crap, -1);
''' % (int (t[0]), int (t[1]), brains.index (t[2]), parent.anim.find_seq (t[3]), int (t[4]), t[5]))
		if self.title_music:
			s.write ('playmidi ("%s.mid");\n' % self.title_music)
		s.write ('}\n')
		# Write main.c
		s = open (os.path.join (d, 'start' + os.extsep + 'c'), 'w')
		s.write ('void main ()\n{')
		global the_globals
		for v in the_globals:
			s.write ('\tmake_global_int ("%s", %d);\n' % (v, the_globals[v]))
		for t in range (max_tmp):
			s.write ('\tmake_global_int ("tmp%s", %d);\n' % (t, 0))
		s.write ('\tkill_this_task ();\n}\n')

class Dink:
	def __init__ (self, root):
		self.root = root
		self.world = World (self)
		self.tile = Tile (self)
		self.anim = Anim (self)
		self.sound = Sound (self)
		self.script = Script (self)
		self.info = open (os.path.join (root, 'info' + os.extsep + 'txt')).read ()
		p = os.path.join (root, 'preview' + os.extsep + 'png')
		if os.path.exists (p):
			self.preview = Image.open (p).convert ('RGBA')
	def write (self, root):
		if not os.path.exists (root):
			os.mkdir (root)
		# Write dink.dat
		# Write hard.dat
		# Write map.dat
		self.world.write (root)
		# Write tiles/*
		self.tile.write (root)
		# Write dink.ini
		# Write graphics/*
		self.anim.write (root)
		# Write sound/*
		self.sound.write (root)
		# Write story/*
		self.script.write (root)
		# Write the rest
		if 'preview' in dir (self):
			self.preview.write (os.path.join (root, preview + os.extsep + 'bmp'))
		open (os.path.join (root, 'dmod' + os.extsep + 'diz'), 'w').write (self.info)

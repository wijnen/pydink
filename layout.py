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
#seq
#	name.gif			sequence
#	name.txt			info about name.gif if it exists, generated sequence otherwise
#sound.txt				list of name filename (number)?
#music.txt				list of name filename (number)?
#script
#	name.c				script to be preprocessed (sound and music names, possibly spacing)

import os
import re
import Image

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

def convert_image (im):
	k = Image.eval (im.convert ('RGBA'), lambda (v): [v, 254][v == 255])
	bg = Image.new ('RGB', k.size, (255, 255, 255))
	bg.paste (k)
	return bg

def readlines (f):
	ret = {}
	while True:
		l = f.readline ()
		if l.strip () == '':
			break
		if l.strip ()[0] == '#':
			continue
		r = re.match (r'(.*)=(.*)', l.strip ())
		assert r != None
		assert r.group (1) not in ret
		ret[r.group (1).strip ()] = r.group (2).strip ()
	return ret

def get (d, member, default = None):
	if member not in d:
		assert default != None and default != int
		return d, default
	if default == None:
		ret = d[member]
	elif type (default) == bool:
		if d[member].lower () in ['true', 'yes', '1']:
			ret = True
		else:
			assert d[member].lower () in ['false', 'no', '0']
			ret = False
	elif default == int:
		ret = int (d[member])
	else:
		ret = type (default)(d[member])
	del d[member]
	return d, ret

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
	s = script.lstrip ()
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
	l = ['&&', '||', '==', '!=', '>=', '<=', '>', '<', '!', '+=', '-=', '/=', '*=', '=', '+', '-', '*', '/', ',', ';', '{', '}', '?', ':', '(', ')']
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

def read_args (script):
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
		t, script, isname = token (script)
	else:
		while True:
			if script[0] == '"':
				p = script.find ('"', 1)
				assert p >= 0
				args += (script[:p + 1],)
				script = script[p + 1:]
			else:
				a, bp, script = parse_expr (script, restart = False, as_bool = False)
				args += (a,)
				b += bp
			t, script, isname = token (script, True)
			if t != ',':
				break
	assert t == ')'
	return b, args, script

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
					return ret[0][1][0] + ' = ' + e, b, t + ' ' + script
				e, b = build (ret[0], as_bool)
				return e, b, t + ' ' + script
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
					if script.startswith ('('):
						# Read away the opening parenthesis.
						t, script, isname = token (script)
						b, args, script = read_args (script)
						ret += ([name, args, b],)
						need_operator = True
						continue
					ret += ('&' + t,)
				else:
					ret += (t,)
				need_operator = True

def preprocess (script, dink):
	the_locals = []
	ret = ''
	indent = []
	numlabels = 0
	atend = ''
	realatend = ''
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
			ret += i[:-1] + '}\n'
			realatend = indent[-1]
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
				ret += before + i + '&' + name + ' ' + op + ' ' + e + ';\n'
			elif t in ['*=', '/=']:
				# Really, the target language is too broken for words...
				op = t[0]
				e, before, script = parse_expr (script, as_bool = False)
				ret += before + i + '&' + name + ' ' + op + ' ' + e + ';\n'
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
					b, args, script = read_args (script)
					ret += b + i + name + '(' + ', '.join (args) + ');\n'
		realatend = atend
		atend = ''
		t, script, isname = token (script)
		assert (t == ';')
	return ret

class Sprite:
	pass

class Room:
	def __init__ (self, parent, root):
		self.parent = parent
		f = open (os.path.join (root, 'info' + os.extsep + 'txt'))
		self.tiles = []
		for ty in range (8):
			ln = f.readline ()
			self.tiles += ([(x[0], int (x[1]), int (x[2])) for x in [y.split (',') for y in ln.split ()]],)
			assert len (self.tiles[-1]) == 12
		info = readlines (f)
		info, self.hard = get (info, 'hard', '')
		info, self.script = get (info, 'script', '')
		info, self.music = get (info, 'music', '')
		info, self.indoor = get (info, 'indoor', False)
		assert info == {}
		self.sprite = {}
		sdir = os.path.join (root, "sprite")
		for s in os.listdir (sdir):
			info = readlines (open (os.path.join (sdir, s)))
			base = re.match ('(.+?)(-[^-]*?)?(\..*)?$', s).group (1)
			self.sprite[s] = Sprite ()
			info, self.sprite[s].x = get (info, 'x', int)
			info, self.sprite[s].y = get (info, 'y', int)
			info, self.sprite[s].seq = get (info, 'seq', base)
			info, self.sprite[s].frame = get (info, 'frame', 0)
			info, self.sprite[s].type = get (info, 'type', 1)	# 0 for background, 1 for person or sprite, 3 for invisible
			info, self.sprite[s].size = get (info, 'size', 100)
			info, self.sprite[s].active = get (info, 'active', True)
			info, self.sprite[s].brain = get (info, 'brain', 'bisshop')
			info, self.sprite[s].script = get (info, 'script', '')
			info, self.sprite[s].speed = get (info, 'speed', 1)
			info, self.sprite[s].base_walk = get (info, 'base_walk', '')
			info, self.sprite[s].base_idle = get (info, 'base_idle', '')
			info, self.sprite[s].base_attack = get (info, 'base_attack', '')
			info, self.sprite[s].base_hit = get (info, 'base_hit', '')
			info, self.sprite[s].timer = get (info, 'timer', 33)
			info, self.sprite[s].que = get (info, 'que', 0)
			info, self.sprite[s].hard = get (info, 'hard', True)
			info, self.sprite[s].left = get (info, 'left', 0)
			info, self.sprite[s].top = get (info, 'top', 0)
			info, self.sprite[s].right = get (info, 'right', 0)
			info, self.sprite[s].bottom = get (info, 'bottom', 0)
			info, w = get (info, 'warp', '')
			if w == '':
				self.sprite[s].warp = None
			else:
				self.sprite[s].warp = [int (x) for x in w.split (',')]
			info, self.sprite[s].touch_seq = get (info, 'touch_seq', '')
			info, self.sprite[s].base_die = get (info, 'base_die', '')
			info, self.sprite[s].gold = get (info, 'gold', 0)
			info, self.sprite[s].hitpoints = get (info, 'hitpoints', 0)
			info, self.sprite[s].strength = get (info, 'strength', 0)
			info, self.sprite[s].defense = get (info, 'defense', 0)
			info, self.sprite[s].exp = get (info, 'exp', 0)
			info, self.sprite[s].sound = get (info, 'sound', '')
			info, self.sprite[s].vision = get (info, 'vision', 0)
			info, self.sprite[s].nohit = get (info, 'nohit', False)
			info, self.sprite[s].touch_damage = get (info, 'touch_damage', 0)
			assert info == {}

class World:
	def __init__ (self, parent):
		self.parent = parent
		d = os.path.join (parent.root, 'world')
		self.room = {}
		for y in range (24):
			for x in range (32):
				n = y * 32 + x + 1
				dirname = os.path.join (d, '%03d-%02d-%02d' % (n, x, y))
				if not os.path.exists (dirname):
					continue
				print 'Adding room %d (%d, %d)' % (n, x, y)
				self.room[n] = Room (parent, dirname)
	def write (self, root):
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink.dat'), "wb")
		ddat.write ('Smallwood' + '\0' * 15)
		rooms = []
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 4))
				continue
			rooms += (self.room[i],)
			# Note that the write is after the append, because the index must start at 1.
			ddat.write (make_lsb (len (rooms), 4))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 4))
				continue
			ddat.write (make_lsb (self.parent.sound.find_music (self.room[i].music), 4))
		ddat.write ('\0' * 4)
		for i in range (1, 32 * 24 + 1):
			if not i in self.room or not self.room[i].indoor:
				ddat.write (make_lsb (0, 4))
			else:
				ddat.write (make_lsb (1, 4))
		# Write map.dat
		mdat = open (os.path.join (root, 'map.dat'), "wb")
		for s in rooms:
			mdat.write ('\0' * 20)
			# tiles and hardness
			for y in range (8):
				for x in range (12):
					bmp, tx, ty = s.tiles[y][x]
					mdat.write (make_lsb (self.parent.tile.find_bmp (bmp) * 128 + ty * 12 + tx, 4))
					mdat.write ('\0' * 4)
					mdat.write (make_lsb (self.parent.tile.find_hard (s.hard, x, y, bmp, tx, ty), 4))
					mdat.write ('\0' * 68)
			mdat.write ('\0' * 320)
			# sprites
			# sprite 0 is never used...
			mdat.write ('\0' * 220)
			for sp in s.sprite:
				spr = s.sprite[sp]
				mdat.write (make_lsb (spr.x, 4))
				mdat.write (make_lsb (spr.y, 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.seq), 4))
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
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_walk), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_idle), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_attack), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_hit), 4))
				mdat.write (make_lsb (spr.timer, 4))
				mdat.write (make_lsb (spr.que, 4))
				mdat.write (make_lsb (spr.hard, 4))
				mdat.write (make_lsb (spr.left, 4))
				mdat.write (make_lsb (spr.top, 4))
				mdat.write (make_lsb (spr.right, 4))
				mdat.write (make_lsb (spr.bottom, 4))
				if spr.warp != None:
					mdat.write (make_lsb (0, 4))
					mdat.write (make_lsb (spr.warp[0], 4))
					mdat.write (make_lsb (spr.warp[1], 4))
					mdat.write (make_lsb (spr.warp[2], 4))
				else:
					mdat.write ('\0' * 16)
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.touch_seq), 4))
				mdat.write (make_lsb (self.parent.seq.find_seq (spr.base_die), 4))
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
			mdat.write ('\0' * 220 * (100 - len (s.sprite)))
			# base script
			mdat.write (make_string (s.script, 21))
			mdat.write ('\0' * 1019)

class Tile:
	def __init__ (self, parent):
		self.parent = parent
		self.hard = {}
		self.tile = {}
		d = os.path.join (parent.root, "tile")
		for t in os.listdir (d):
			ext = os.extsep + 'png'
			h = '-hard' + ext
			if not t.endswith (h):
				continue
			base = t[:-len (h)]
			self.hard[base] = convert_image (Image.open (os.path.join (d, t)))
			t = os.path.join (d, base + '-tile' + os.extsep + 'png')
			if os.path.exists (t):
				self.tile[base] = convert_image (Image.open (t))
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
				self.tile[t].save (os.path.join (d, t + os.extsep + 'bmp'))
			self.map[t] = [None] * 8
			for y in range (8):
				self.map[t][y] = [None] * 12
				for x in range (12):
					if self.hard[t].size[0] < (x + 1) * 50 or self.hard[t].size[1] < (y + 1) * 50:
						continue
					tile = self.hard[t].crop ((x * 50, y * 50, (x + 1) * 50, (y + 1) * 50))
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
					if m[y][x] != None:
						h.write (make_lsb (m[y][x], 4))
					else:
						# fill it with junk
						h.write (make_lsb (0, 4))
		h.write ('\0' * (8000 - len (self.tile) * 8 * 12 * 4))

class Oneseq:
	pass
class Oneframe:
	pass

class Seq:
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		d = os.path.join (parent.root, "seq")
		dinkfile = open (os.path.join (d, 'external' + os.extsep + 'txt'))
		self.dink = {}
		codes = []
		while True:
			info = readlines (dinkfile)
			if info == {}:
				break
			info, dinkdir = get (info, 'dir', 'graphics')
			if dinkdir.endswith ('\\'):
				dinkdir = dinkdir[:-1]
			keys = [x for x in info.keys () if x.find (':') < 0]
			for k in keys:
				v = info[k]
				del info[k]
				v = v.split ()
				if v[0] == '-':
					code = None
				else:
					code = int (v[0])
					assert code not in codes
					codes += (code,)
				f = v[1]
				n = int (v[2])
				v = v[3:]
				assert k not in self.dink
				if len (v) == 1:
					self.dink[k] = [dinkdir + '\\' + f, n, [[None] * 7 for x in range (n + 1)], v[0]]
				else:
					self.dink[k] = [dinkdir + '\\' + f, n, [[None] * 7 for x in range (n)] + [v], 'normal']
				self.dink[k] += (code,)
				for i in range (int (n)):
					key = '%s:%d' % (k, i + 1)
					if key in info:
						box = info[key].split ()
						assert len (box) == 7
						self.dink[k][2][i] = [int (x) for x in box]
						del info[key]
		infofile = open (os.path.join (d, 'info' + os.extsep + 'txt'))
		while True:
			info = readlines (infofile)
			if info == {}:
				break
			if 'external' in info:
				info, base = get (info, 'external')
				assert base not in self.data
				d = self.dink[base][:-1]
				self.data[base] = Oneseq ()
				self.data[base].code = self.dink[base][-1]
				self.data[base].filename = d[0]
				self.data[base].frames = [None] * d[1]
				box = d[2]
				deftype = d[3]
			else:
				code = None
				info, base = get (info, 'name')
				assert base not in self.data
				self.data[base] = Oneseq ()
				self.data[base].frames = []
				gif = os.path.join (d, base + os.extsep + 'gif')
				assert os.path.exists (gif)
				f = Image.open (gif)
				while True:
					self.data[base].frames += ((f.info['duration'], convert_image (f)),)
					try:
						f.seek (len (self.data[base].frames))
					except EOFError:
						break
				w = self.data[base].frames[0][1].size[0]
				h = self.data[base].frames[0][1].size[1]
				box = [[None] * 7] * len (self.data[base].frames) + [[w / 2, h * 8 / 10, -w * 4 / 10, -h / 10, w * 4 / 10, h / 10, self.data[base].frames[0][0]]]
				info, self.data[base].filename = 'graphics\%s-' % base
				deftype = 'normal'
			info, self.data[base].num = get (info, 'frames', len (self.data[base].frames))
			info, self.data[base].special = get (info, 'special', 1)
			info, self.data[base].now = get (info, 'load-now', False)
			info, defbox = get (info, 'box', '')
			if defbox == '':
				defbox = [None] * 6
			else:
				defbox = defbox.split ()
			assert len (defbox) == 6
			info, delay = get (info, 'delay', 0)
			defbox += [delay]
			self.data[base].desc = []
			for f in range (self.data[base].num):
				self.data[base].desc += (Oneframe (),)
				if f >= len (self.data[base].frames):
					# these are generated frames. They need a source.
					info, self.data[base].desc[-1].seq = get (info, 'seq-%d' % (f + 1))
					info, self.data[base].desc[-1].frame = get (info, 'frame-%d' % (f + 1), 1)
				info, self.data[base].desc[-1].frame = get (info, 'frame-%d' % (f + 1), 1)
				info, curbox = get (info, 'box-%d' % f, '')
				if curbox == '':
					curbox = box[f][:6]
					if curbox[0] == None:
						curbox = defbox[:6]
						if curbox[0] == None:
							curbox = box[-1][:6]
				else:
					curbox = [int (x) for x in curbox.split ()]
				assert len (curbox) == 6
				self.data[base].desc[-1].x = curbox[0]
				self.data[base].desc[-1].y = curbox[1]
				self.data[base].desc[-1].left = curbox[2]
				self.data[base].desc[-1].top = curbox[3]
				self.data[base].desc[-1].right = curbox[4]
				self.data[base].desc[-1].bottom = curbox[5]
				info, dl = get (info, 'delay-%d' % f, 0)
				if dl == 0:
					dl = box[f][6]
					if dl == None:
						dl = defbox[6]
						if dl == None:
							dl = box[-1][6]
				self.data[base].desc[-1].delay = dl
			info, self.data[base].type = get (info, 'type', deftype)
			assert self.data[base].type in ('normal', 'black', 'leftalign', 'noanim')
			assert info == {}
		nextseq = 1
		for s in self.data:
			if self.data[s].code == None:
				self.data[s].code = nextseq
				nextseq += 1
				while nextseq in codes:
					nextseq += 1
	def find_seq (self, name):
		if not name:
			return 0
		return self.data[name].code
	def write (self, root):
		# Write graphics/*
		# Write dink.ini
		d = os.path.join (root, 'graphics')
		if not os.path.exists (d):
			os.mkdir (d)
		ini = open (os.path.join (root, 'dink.ini'), 'w')
		for g in self.data:
			delay = self.data[g].desc[0].delay
			if self.data[g].now:
				now = '_now'
			else:
				now = ''
			if self.data[g].type == 'normal':
				ini.write ('load_sequence%s %s %d %d %d %d %d %d %d %d\n' % (now, self.data[g].filename, self.data[g].code, delay, self.data[g].desc[0].x, self.data[g].desc[0].y, self.data[g].desc[0].left, self.data[g].desc[0].top, self.data[g].desc[0].right, self.data[g].desc[0].bottom))
			else:
				ini.write ('load_sequence%s %s %d %s\n' % (now, self.data[g].filename, self.data[g].code, self.data[g].type.upper ()))
			for n, f in zip (range (len (self.data[g].frames)), self.data[g].frames):
				if f != None:
					f[1].save (os.path.join (d, (g + '-%02d' + os.extsep + 'bmp') % (n + 1)))
			for f in range (len (self.data[g].desc)):
				if f >= len (self.data[g].frames):
					ini.write ('set_frame_frame %d %d %d %d\n' % (self.data[g].code, f + 1, self.find_seq (self.data[g].desc[f].seq), self.data[g].desc[f].frame))
				if ((self.data[g].type != 'normal' or self.data[g].desc[0].x, self.data[g].desc[0].y, self.data[g].desc[0].left, self.data[g].desc[0].top, self.data[g].desc[0].right, self.data[g].desc[0].bottom) != (self.data[g].desc[f].x, self.data[g].desc[f].y, self.data[g].desc[f].left, self.data[g].desc[f].top, self.data[g].desc[f].right, self.data[g].desc[f].bottom)) and self.data[g].desc[f].right != None and self.data[g].desc[f].right - self.data[g].desc[f].left != 0:
					ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\n' % (self.data[g].code, f + 1, self.data[g].desc[f].x, self.data[g].desc[f].y, self.data[g].desc[f].left, self.data[g].desc[f].top, self.data[g].desc[f].right, self.data[g].desc[f].bottom))
				if f > 0 and self.data[g].desc[f].delay != self.data[g].desc[0].delay:
					ini.write ('set_frame_delay %d %d %d\n' % (self.data[g].code, f + 1, self.data[g].desc[f].delay))
				if f != 0 and self.data[g].special == f + 1:
					ini.write ('set_frame_special %d %d\n' % (self.data[g].code, f + 1))

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
		d = os.path.join (parent.root, "script")
		for s in os.listdir (d):
			ext = os.extsep + 'c'
			if not s.endswith (ext):
				continue
			base = s[:-len (ext)]
			assert base not in self.data
			self.data[base] = open (os.path.join (d, s)).read ()
		f = open (os.path.join (parent.root, "title" + os.extsep + "txt"))
		info = readlines (f)
		info, self.title_music = get (info, 'music', '')
		info, self.title_color = get (info, 'color', 0)
		info, self.title_bg = get (info, 'background', '')
		info, p = get (info, 'pointer', 'pointer 1')
		p = p.split ()
		self.title_pointer_seq, self.title_pointer_frame = p[0], int (p[1])
		info, self.title_run = get (info, 'run', '')
		info, n = get (info, 'sprites', 0)
		self.title_sprite = []
		for s in range (n):
			info, spr = get (info, 'sprite-%d' % (s + 1))
			spr = spr.split ()
			if len (spr) == 4:
				spr += ('none',)
			if len (spr) == 5:
				spr += ('',)
			assert len (spr) == 6
			self.title_sprite += ((spr[0], int (spr[1]), int (spr[2]), int (spr[3]), spr[4], spr[5]),)
		info, n = get (info, 'buttons', int)
		self.title_button = []
		for s in range (n):
			info, b = get (info, 'button-%d' % (s + 1))
			b = b.split ()
			assert len (b) == 5
			self.title_sprite += ((b[0], int (b[1]), int (b[2]), int (b[3]), 'button', b[4]),)
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
		s.write ('void main ()\n{\n')
		for n, snd in zip (range (len (self.parent.sound.sound)), self.parent.sound.sound):
			s.write ('\tload_sound ("%s.wav", %d);\n' % (snd, n))
		s.write ('set_dink_speed (3);\nsp_frame_delay (1,0);\n')
		if self.title_bg != '':
			s.write ('copy_bmp_to_screen ("%s");\n' % self.title_bg)
		else:
			s.write ('fill_screen (%d);\n' % self.title_color)
		s.write ('''\
sp_seq (1, 0);
sp_brain (1, 13);
sp_pseq (1, %d);
sp_pframe (1, %d);
sp_que (1, 20000);
sp_noclip (1, 1);
int &crap;
''' % (self.parent.seq.find_seq (self.title_pointer_seq), self.title_pointer_frame))
		for t in self.title_sprite:
			if t[4] == 'none':
				assert t[5] == ''
				s.write ('&crap = create_sprite (%d, %d, %d, %d, %d);' % (t[2], t[3], brains.index (t[4]), self.parent.seq.find_seq (t[0]), t[1]))
			else:
				s.write ('''\
&crap = create_sprite (%d, %d, %d, %d, %d);
sp_script(&crap, "%s");
sp_touch_damage (&crap, -1);
''' % (t[2], t[3], brains.index (t[4]), self.parent.seq.find_seq (t[0]), t[1], t[5]))
			s.write ('sp_noclip (&crap, 1);\n')
		if self.title_music != '':
			s.write ('playmidi ("%s.mid");\n' % self.title_music)
		if self.title_run != '':
			s.write ('spawn ("%s");\n' % self.title_run)
		s.write ('kill_this_task ();\n}\n')
		# Write main.c
		s = open (os.path.join (d, 'main' + os.extsep + 'c'), 'w')
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
		self.tile = Tile (self)
		self.world = World (self)
		self.seq = Seq (self)
		self.sound = Sound (self)
		self.script = Script (self)
		self.info = open (os.path.join (root, 'info' + os.extsep + 'txt')).read ()
		im = os.path.join (root, 'image')
		p = os.path.join (im, 'preview' + os.extsep + 'png')
		if os.path.exists (p):
			self.preview = convert_image (Image.open (p))
		p = os.path.join (im, 'splash' + os.extsep + 'png')
		if os.path.exists (p):
			self.splash = convert_image (Image.open (p))
	def write (self, root):
		if not os.path.exists (root):
			os.mkdir (root)
		# Write tiles/*
		self.tile.write (root)
		# Write dink.dat
		# Write hard.dat
		# Write map.dat
		self.world.write (root)
		# Write dink.ini
		# Write graphics/*
		self.seq.write (root)
		# Write sound/*
		self.sound.write (root)
		# Write story/*
		self.script.write (root)
		# Write the rest
		if 'preview' in dir (self):
			self.preview.save (os.path.join (root, 'preview' + os.extsep + 'bmp'))
		if 'splash' in dir (self):
			self.splash.save (os.path.join (os.path.join (root, 'tiles'), 'splash' + os.extsep + 'bmp'))
		open (os.path.join (root, 'dmod' + os.extsep + 'diz'), 'w').write (self.info)

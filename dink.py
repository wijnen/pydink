#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

#world
#	nnn-xx-yy
#		info.txt		script, tiles, hardness
#		sprite
#			id.txt		script, x, y, etc.
#tile
#	name-tile.png			tile map (01-41)
#	name-hard.png			hardness for tile map, or for screen
#seq
#	name.gif			sequence
#	name.txt			info about name.gif if it exists, generated sequence otherwise
#sound.txt				list of name filename (number)?
#music.txt				list of name filename (number)?
#script
#	name.c				script to be preprocessed (sound and music names, possibly spacing)

import sys
import os
import re
import Image
import tempfile
import shutil
import StringIO
import pickle
from config import Sequence
from config import Frame
from config import cachedir
from config import dinkdir
from config import dinkprog

cachedir = os.path.expanduser (cachedir)
tilefiles, collections, sequences, codes = pickle.load (open (os.path.join (cachedir, 'data')))
filename = ''

def error (message):
	sys.stderr.write ('%s: Error: %s\n' % (filename, message))

def nice_assert (test, message):
	if test:
		return
	error (message)

def make_hard_image (path):
	src = Image.open (path).convert ('RGB')
	spix = src.load ()
	ret = Image.new ('RGBA', src.size)
	rpix = ret.load ()
	for y in range (src.size[1]):
		for x in range (src.size[0]):
			if spix[x, y][2] < 150:
				rpix[x, y] = (0, 0, 0, 0)
			elif spix[x, y][1] >= 150:
				rpix[x, y] = (255, 255, 255, 128)
			else:
				rpix[x, y] = (0, 0, 255, 128)
	return ret

#class filepart:
#	def __init__ (self, name, offset, length):
#		self.offset = offset
#		self.length = length
#		self.file = open (name)
#		self.file.seek (offset)
#		self.pos = 0
#	def read (self, size):
#		assert (size > 0)
#		if self.pos + size >= self.length:
#			size = self.length - self.pos
#		self.pos += size
#		return self.file.read (size)
#	def tell (self):
#		return self.pos
#	def seek (self, p, how):
#		if how == 1:
#			p += self.pos
#		elif how == 2:
#			p += self.length
#		else:
#			nice_assert (how == 0, 'invalid seek type')
#		nice_assert (p <= self.length, 'seek beyond end of file')
#		self.file.seek (self.offset + p)
def filepart (name, offset, length):
	f = open (name)
	f.seek (offset)
	return StringIO.StringIO (f.read (length))

# brain 0: no brain -- sprite will not do anything automatically
# brain 1: Human [that is, sprite 1 / Dink] brain.
# brain 2: ["Dumb Sprite Bouncer", per DinkEdit.  See below.]
# brain 3: Duck brain.
# brain 4: Pig brain.
# brain 5: When seq is done, kills but leaves last frame drawn to the background
# brain 6: Repeat brain - does the active SEQ over and over.
# brain 7: Same as brain 5 but does not draw last frame to the background.
# [brain 8: text sprite brain]
# brain 9: Person/monster ([Only] diagonals)
# brain 10: Person/monster ([No] diagonals)
# brain 11: Missile brain - repeats SEQ [compare brain 17].
# brain 12: Will shrink/grow to match size in sp_brain_parm(), then die [WITHOUT giving any experience...]
# brain 13: Mouse brain (for intro, the pointer) (do a set_keep_mouse() to use inside game as well)
# brain 14: Button brain.  (intro buttons, can be used in game as well)
# brain 15: Shadow brain.  Shadows for fireballs, etc.
# brain 16: Smart People brain.  They can walk around, stop and look.
# brain 17: Missile brain, [like 11] but kills itself when SEQ is done.

brains = ['none', 'dink', 'bounce', 'duck', 'pig', 'mark', 'repeat', 'play', 'text', 'bisshop', 'rook', 'missile', 'resize', 'pointer', 'button', 'shadow', 'person', 'flare']

def make_brain (name):
	if name in brains:
		return brains.index (name)
	try:
		ret = int (name)
	except:
		error ('unknown and non-numeric brain %s' % name)
	if ret >= len (brains):
		error ('accessing named brain %s by number (%d)' % (brains[ret], ret))
	return ret

predefined = [
		"current_sprite"
	]
default_globals = {
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
		"missle_source": 0,

		"story": 0,
		"old_womans_duck": 0,
		"nuttree": 0,
		"letter": 0,
		"little_girl": 0,
		"farmer_quest": 0,
		"save_x": 0,
		"save_y": 0,
		"safe": 0,
		"pig_story": 0,
		"wizard_see": 0,
		"mlibby": 0,
		"wizard_again": 0,
		"snowc": 0,
		"duckgame": 0,

		"gossip": 0,
		"robbed": 0,
		"dinklogo": 0,
		"rock_placement": 0,
		"temphold": 0,
		"temp1hold": 0,
		"temp2hold": 0,
		"temp3hold": 0,
		"temp4hold": 0,
		"temp5hold": 0,
		"temp6hold": 0,
		"town1": 0,
		"s2-milder": 0,
		"thief": 0,
		"caveguy": 0,
		"s2-aunt": 0,
		"tombob": 0,
		"mayor": 0,
		"hero": 0,
		"s2-nad": 0,
		"gobpass": 0,
		"bowlore": 0,
		"s4-duck": 0,
		"s5-jop": 0,
		"s7-boat": 0,
		"s2-map": 0
	}
the_globals = {}
for i in default_globals:
	the_globals[i] = default_globals[i]

def convert_image (im):
	k = Image.eval (im.convert ('RGBA'), lambda v: [v, 254][v == 255])
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
		nice_assert (r != None, 'invalid line in input file: %s' % l)
		nice_assert (r.group (1) not in ret, 'duplicate definition of %s' % r.group (1))
		ret[r.group (1).strip ()] = r.group (2).strip ()
	return ret

def get (d, member, default = None):
	if member not in d:
		nice_assert (default != None and default != int, 'member %s has no default, but is missing in file' % member)
		return d, default
	if default == None:
		ret = d[member]
	elif type (default) == bool:
		if d[member].lower () in ['true', 'yes', '1']:
			ret = True
		else:
			nice_assert (d[member].lower () in ['false', 'no', '0'], 'invalid value for boolean setting %s' % member)
			ret = False
	elif default == int:
		ret = int (d[member])
	else:
		ret = type (default)(d[member])
	del d[member]
	return d, ret

def put (f, member, value, default = None):
	nice_assert (value != None, "Writing %s without a value" % member)
	if value == default:
		return
	if type (value) == bool:
		v = '%s' % ['no', 'yes'][value]
	else:
		v = str (value)
	f.write ('%s = %s\n' % (member, v))

def make_lsb (num, size):
	ret = ''
	for i in range (size):
		ret += '%c' % (num & 0xff)
		num >>= 8
	return ret

def make_string (s, size):
	nice_assert (len (s) < size, "String %s of length %d doesn't fit in field of size %d" % (s, len (s), size))
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
			nice_assert (p >= 0, 'unfinished comment')
			if not allow_comment:
				continue
			return s[:p + 2], s[p + 2:].lstrip (), False
		break
	l = ['//', '/*', '&&', '||', '==', '!=', '>=', '<=', '>', '<', '!', '+=', '-=', '/=', '*=', '=', '+', '-', '*', '/', ',', ';', '{', '}', '?', ':', '(', ')']
	for i in l:
		if s.startswith (i):
			return i, s[len (i):].lstrip (), False
	if s[0] == '"':
		p = s.find ('"', 1)
		nice_assert (p >= 0, 'unfinished string')
		n = s.find ('\n', 1)
		nice_assert (n == -1 or n > p, 'unfinished string')
		return s[:p + 1], s[p + 1:].lstrip (), False
	is_name = True
	r = re.match ('[a-zA-Z_][a-zA-Z_0-9]*', s)
	if r == None:
		is_name = False
		r = re.match ('[0-9]+', s)
		nice_assert (r != None, 'unrecognized token %s' % s.split ()[0])
	key = r.group (0)
	return key, s[len (key):].lstrip (), is_name

def push (ret, operators):
	args = operators[-1][1]
	r = ret[-args:]
	ret = ret[:-args]
	ret += ([operators[-1][0], r],)
	operators = operators[:-1]
	return ret, operators

max_tmp = 0
current_tmp = 0
def build (expr, as_bool, invert = False):
	"""Build an expression or subexpression. Return expr, before"""
	global current_tmp
	if type (expr) == str:
		# Simple expression.
		if as_bool:
			if invert:
				return expr + ' == 0', ''
			else:
				return expr + ' != 0', ''
		else:
			if invert:
				tmp = '&tmp%d' % current_tmp
				current_tmp += 1
				return tmp, tmp + ' = 0;\r\nif (' + expr + ' == 0)\r\n' + tmp + ' = 1;\r\n'
			else:
				return expr, ''
	if len (expr) == 3:
		# function call: name, args, before
		f = expr[0] + '(' + ', '.join (expr[1]) + ')'
		if as_bool:
			if invert:
				return f + ' == 0', expr[2]
			else:
				return f + ' != 0', expr[2]
		if invert:
			tmp = '&tmp%d' % current_tmp
			current_tmp += 1
			return tmp, expr[2] + tmp + ' = 0;\r\nif (' + f + ' == 0)\r\n' + tmp + ' = 1;\r\n'
		return f, expr[2]
	tests = ('==', '!=', '<=', '>', '>=', '<')
	if expr[0] in tests:
		e0, b0 = build (expr[1][0], False, False)
		e1, b1 = build (expr[1][1], False, False)
		if invert:
			e = e0 + ' ' + tests[tests.index (expr[0]) ^ 1] + ' ' + e1
		else:
			e = e0 + ' ' + expr[0] + ' ' + e1
		if as_bool:
			return e, b0 + b1
		tmp = '&tmp%d' % current_tmp
		current_tmp += 1
		if invert:
			return tmp + ' == 1', b0 + b1 + tmp + ' = 0;\r\nif (' + e0 + tests[tests.index (expr[0]) ^ 1] + e1 + ')\r\n' + tmp + ' = 1;\r\n}\r\n'
		else:
			return tmp + ' == 1', b0 + b1 + tmp + ' = 0;\r\nif (' + e0 + expr[0] + e1 + ')\r\n' + tmp + ' = 1;\r\n'
	if expr[0] in ['&&', '||']:
		e0, b0 = build (expr[1][0], True, invert)
		e1, b1 = build (expr[1][1], True, invert)
		tmp = '&tmp%d' % current_tmp
		current_tmp += 1
		if as_bool:
			e = tmp + ' == 1'
		else:
			e = tmp
		if (expr[0] == '&&') ^ invert:
			return e, b0 + b1 + tmp + ' = 0;\r\nif (' + e0 + ')\r\n{\r\nif (' + e1 + ')\r\n' + tmp + ' = 1;\r\n}\r\n'
		else:
			return e, b0 + b1 + tmp + ' = 0;\r\nif (' + e0 + ')\r\n' + tmp + ' = 1;\r\nif (' + e1 + ')\r\n' + tmp + ' = 1;\r\n'
	if expr[0] == '!':
		if invert:
			return build (['!=', [expr[1][0], '0']], as_bool, False)
		return build (expr[1][0], as_bool, True)
	nice_assert (expr[0] in ['*', '/', '+', '-'], 'unknown operator %s' % expr[0])
	tmp = '&tmp%d' % current_tmp
	current_tmp += 1
	if len (expr[1]) == 2:
		e0, b0 = build (expr[1][0], False, False)
		e1, b1 = build (expr[1][1], False, False)
	else:
		e0, b0 = '0', ''
		e1, b1 = build (expr[1][0], False, False)
	if expr[0] == '+' or expr[0] == '-':
		op = expr[0] + '='
	else:
		op = expr[0]
	if as_bool:
		if invert:
			return tmp + '== 0', b0 + b1 + '%s = %s;\r\n%s %s %s;\r\n' % (tmp, e0, tmp, op, e1)
		else:
			return tmp + '!= 0', b0 + b1 + '%s = %s;\r\n%s %s %s;\r\n' % (tmp, e0, tmp, op, e1)
	else:
		if invert:
			return tmp, b0 + b1 + '%s = %s;\r\n%s %s %s;\r\nif (%s != 0)\r\n%s = 0;\r\nelse\r\n%s = 1;\r\n' % (tmp, e0, tmp, op, e1, tmp, tmp, tmp)
		else:
			return tmp, b0 + b1 + '%s = %s;\r\n%s %s %s;\r\n' % (tmp, e0, tmp, op, e1)

next_mangled = 0
mangled_names = {}

def mangle (name):
	global next_mangled
	if name in default_globals or name in predefined:
		return name
	if name not in mangled_names:
		mangled_names[name] = next_mangled
		next_mangled += 1
	return 'm%d%s' % (mangled_names[name], name)

def mangle_function (name, args, dink):
	'''\
	Handle special arguments of:
	add_item
	add_magic
	create_sprite
	editor_type
	get_rand_sprite_with_this_brain
	get_sprite_with_this_brain
	playmidi
	playsound
	preload_seq
	sp
	sp_base_attack
	sp_base_death
	sp_base_idle
	sp_base_walk
	sp_brain
	sp_sound

	Change function name of sp_nohard into sp_hard, because of its inverted argument; raise exception on using sp_hard

	return name, args, before.'''
	if name == 'add_item' or name == 'add_magic':
		nice_assert (len (args) == 3, '%s requires 3 arguments (%d given)' % (name, len (args)))
		nice_assert (args[1][0] == '"' and args[1][-1] == '"', 'second argument of %s must be a sequence name' % name)
		return name, [args[0], str (dink.seq.find_seq (args[1][1:-1]).code), args[2]], ''
	elif name == 'create_sprite':
		nice_assert (len (args) == 5, '%s requires 5 arguments (%d given)' % (name, len (args)))
		nice_assert (args[2][0] == '"' and args[2][-1] == '"', 'third argument of %s must be a sequence name' % name)
		return name, [args[0], args[1], str (make_brain (args[2])), str (dink.seq.find_seq (args[3][1:-1]).code), args[4]], ''
	elif name == 'get_rand_sprite_with_this_brain' or name == 'get_sprite_with_this_brain':
		nice_assert (len (args) == 2, '%s requires 2 arguments (%d given)' % (name, len (args)))
		nice_assert (args[0][0] == '"' and args[0][-1] == '"', 'first argument of %s must be a brain name' % name)
		return name, [str (make_brain (args[0][1:-1])), args[1]], ''
	elif name == 'playmidi':
		nice_assert (len (args) == 1, '%s requires 1 argument (%d given)' % (name, len (args)))
		nice_assert (args[0][0] == '"' and args[0][-1] == '"', 'argument of %s must be a music name' % name)
		return name, [str (dink.sound.find_music (args[0][1:-1]))], ''
	elif name == 'playsound':
		nice_assert (len (args) == 4 or len (args) == 5, '%s requires 4 or 5 arguments (%d given)' % (name, len (args)))
		nice_assert (args[0][0] == '"' and args[0][-1] == '"', 'argument of %s must be a sound name' % name)
		return name, [str (dink.sound.find_sound (args[0][1:-1]))] + args[1:], ''
	elif name == 'preload_seq':
		nice_assert (len (args) == 1, '%s requires 1 argument (%d given)' % (name, len (args)))
		nice_assert (args[0][0] == '"' and args[0][-1] == '"', 'argument of %s must be a sequence name' % name)
		return name, [str (dink.seq.find_seq (args[0][1:-1]).code)], ''
	elif name == 'sp':
		nice_assert (len (args) == 1, '%s requires 1 argument (%d given)' % (name, len (args)))
		nice_assert (args[0][0] == '"' and args[0][-1] == '"', 'argument of %s must be a sprite name' % name)
		name = args[0][1:-1]
		sprite = None
		# Sprite names used with sp () must be unique in the entire game, because the script doesn't know from which room it's called.
		for r in dink.world.room:
			if name in dink.world.room[r].sprite:
				nice_assert (sprite == None, 'referenced sprite %s is not unique' % name)
				sprite = dink.world.room[r].sprite[name]
		return 'sp', [str (sprite.editcode)], ''
	elif name == 'sp_base_attack' or name == 'sp_base_death' or name == 'sp_base_idle' or name == 'sp_base_walk':
		nice_assert (len (args) == 2, '%s requires 2 arguments (%d given)' % (name, len (args)))
		nice_assert (args[1][0] == '"' and args[0][-1] == '"', 'second argument of %s must be a sequence collection name' % name)
		return name, [args[0], str (dink.seq.collection_code (args[1][1:-1]))], ''
	elif name == 'sp_brain':
		nice_assert (len (args) == 1 or len (args) == 2, '%s requires 1 or 2 arguments (%d given)' % (name, len (args)))
		if len (args) == 2:
			nice_assert (args[1][0] == '"' and args[0][-1] == '"', 'second argument of %s must be omitted, or a sequence collection name' % name)
			v = make_brain (args[1][1:-1])
		else:
			v = -1
		return name, [args[0], str (v)], ''
	elif name == 'sp_sound':
		nice_assert (len (args) == 2, '%s requires 2 arguments (%d given)' % (name, len (args)))
		nice_assert (args[1][0] == '"' and args[0][-1] == '"', 'second argument of %s must be a sound name' % name)
		return name, [args[0], str (dink.sound.find_sound (args[1][1:-1]))], ''
	elif name == 'sp_nohard':
		nice_assert (len (args) == 2, '%s requires 2 arguments (%d given)' % (name, len (args)))
		return 'sp_hard', args, ''
	else:
		nice_assert (name != 'sp_hard', 'sp_hard must be called sp_nohard because of its argument meaning')
		return name, args, ''

def read_args (dink, script):
	args = []
	b = ''
	if script[0] == ')':
		t, script, isname = token (script)
	else:
		while True:
			if script[0] == '"':
				p = script.find ('"', 1)
				nice_assert (p >= 0, 'unterminated string')
				# mangle variable references.
				s = script[:p + 1]
				pos = 0
				sp = ''
				while True:
					pos = s.find ('&')
					if pos < 0:
						sp += s
						break
					sp += s[:pos]
					s = s[:pos + 1]
					e = s.find (';')
					nice_assert (e >= 0, 'incomplete reference in string')
					var = s[:e]
					s = s[e + 1:]
					if var == '':
						# empty variable is escape for & itself.
						sp += '&'
					else:
						# variable found: mangle.
						sp += mangle (var)
				args += (sp,)
				script = script[p + 1:]
			else:
				a, bp, script = parse_expr (dink, script, restart = False, as_bool = False)
				args += (a,)
				b += bp
			t, script, isname = token (script, True)
			if t != ',':
				break
	nice_assert (t == ')', 'unterminated argument list')
	return b, args, script

def parse_expr (parent, script, allow_cmd = False, restart = True, as_bool = None):
	assert as_bool in (True, False)
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
				nice_assert (['(', 0, 100] not in operators, 'incomplete subexpression')
				while operators != []:
					ret, operators = push (ret, operators)
				assert len (ret) == 1
				if allow_cmd:
					nice_assert (ret[0][0] == '=', 'standalone expressions must be assignments')
					e, b = build (ret[0][1][1], as_bool = False)
					return ret[0][1][0] + ' = ' + e, b, t + ' ' + script
				e, b = build (ret[0], as_bool)
				return e, b, t + ' ' + script
			if allow_cmd and t == '=':
				# assignments are almost never allowed in an expression.
				nice_assert (operators == [] and len (ret) == 1 and ret[0] == '&', 'assignment not allowed here')
				while operators != [] and operators[-1][2] < 6:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 6],)
			elif t in ['==', '!=', '>=', '<=', '>', '<']:
				while operators != [] and operators[-1][2] < 5:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 5],)
			elif t == '||':
				while operators != [] and operators[-1][2] < 4:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 4],)
			elif t == '&&':
				while operators != [] and operators[-1][2] < 3:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 3],)
			elif t in ['+', '-']:
				while operators != [] and operators[-1][2] < 2:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 2],)
			elif t in ['*', '/']:
				while operators != [] and operators[-1][2] < 1:
					ret, operators = push (ret, operators)
				operators += ([t, 2, 1],)
			else:
				raise AssertionError ('no valid operator found in expression')
			need_operator = False
		else:
			if t == '(':
				operators += (['(', 0, 100],)
			elif t in ['+', '-', '!']:
				operators += ([t, 1, 0],)
			else:
				nice_assert (t and (isname or (t[0] >= '0' and t[0] <= '9')), 'syntax error')
				if isname:
					name = t
					if script.startswith ('('):
						# Read away the opening parenthesis.
						t, script, isname = token (script)
						b, args, script = read_args (parent, script)
						f, a, bf = mangle_function (name, args, parent)
						ret += ([f, a, b + bf],)
						need_operator = True
						continue
					ret += ('&' + mangle (t),)
				else:
					ret += (t,)
				need_operator = True

def check_exists (the_locals, name):
	name = mangle (name)
	return name in the_locals or name in the_globals

def preprocess (script, dink, filename):
	the_locals = []
	ret = ''
	indent = []
	numlabels = 0
	atend = ''
	realatend = ''
	indentonce = False
	choice_title = None
	while True:
		i = '\t' * len (indent)
		t, script, isname = token (script, True)
		if t == 'else':
			ret += i + 'else\r\n'
			# don't do the atend code just yet.
			continue
		if not t:
			break
		if indentonce:
			i += '\t'
		if t.startswith ('//'):
			comment = script.split ('\n', 1)[0]
			ret += i + t + comment + '\r\n'
			script = script[len (comment) + 1:]
			continue
		if t.startswith ('/*'):
			comment = script.split ('*/', 1)[0]
			ret += i + t + comment + '*/\r\n'
			script = script[len (comment) + 2:]
			continue
		indentonce = False
		if len (indent) == 0:
			if t == 'extern':
				t, script, isname = token (script)
				if t == 'int':
					t, script, isname = token (script)
				nice_assert (isname, 'invalid argument for extern')
				name = t
				t, script, isname = token (script)
				nice_assert (t == ';', 'junk after extern')
				nice_assert (mangle (name) not in the_locals, 'global variable %s already defined as local' % name)
				name = mangle (name)
				if name not in the_globals:
					the_globals[name] = 0
				continue
			nice_assert (t == 'void', 'invalid token at top level; only extern or void allowed')
			t, script, isname = token (script)
			nice_assert (isname, 'function name required after top level void')
			name = t
			t, script, isname = token (script)
			nice_assert (t == '(', '(empty) argument list required for function definition')
			t, script, isname = token (script)
			if t == 'void':
				t, script, isname = token (script)
			nice_assert (t == ')', 'function argument list must be empty')
			t, script, isname = token (script)
			nice_assert (t == '{', 'function body not defined')
			indent += ('',)
			ret += 'void %s(void)\r\n{\r\n' % name
			continue
		ret += realatend
		realatend = ''
		if t == '{':
			indent += (atend,)
			atend = ''
			ret += i[1:] + '{\r\n'
			continue
		if t == '}':
			nice_assert (atend == '', 'incomplete command at end of block')
			ret += i[:-1] + '}\r\n'
			realatend = indent[-1]
			indent = indent[:-1]
			if len (indent) == 0:
				ret += '\r\n'
			continue
		if t == 'while':
			t, script, isname = token (script)
			nice_assert (t == '(', 'parenthesis required after while')
			e, before, script = parse_expr (dink, script, as_bool = True)
			t, script, isname = token (script)
			nice_assert (t == ')', 'parenthesis for while not closed')
			start = 'while%d' % numlabels
			numlabels += 1
			end = 'while%d' % numlabels
			numlabels += 1
			ret += i + start + ':\r\n' + before + i + 'if (' + e + ') goto ' + end + '\r\n'
			atend = i + 'goto ' + start + '\r\n' + i + end + ':\r\n' + atend
			indentonce = True
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
			nice_assert (t == '(', 'parenthesis required after for')
			if script[0] != ';':
				e1, b1, script = parse_expr (dink, script, allow_cmd = True, as_bool = False)
			else:
				e1, b1 = '', ''
			t, script, isname = token (script)
			nice_assert (t == ';', 'two semicolons required in for argument')
			e2, b2, script = parse_expr (dink, script, as_bool = True)
			t, script, isname = token (script)
			nice_assert (t == ';', 'two semicolons required in for argument')
			if script[0] != ')':
				e3, b3, script = parse_expr (dink, script, allow_cmd = True, as_bool = False)
			else:
				e3, b3 = '', ''
			t, script, isname = token (script)
			nice_assert (t == ')', 'parenthesis for for not closed')
			start = 'for%d' % numlabels
			numlabels += 1
			end = 'for%d' % numlabels
			numlabels += 1
			ret += b1 + i + e1 + ';\r\n' + i + start + ':\r\n' + b2 + i + 'if (' + e2 + ') goto ' + end + '\r\n'
			atend = b3 + i + e3 + ';\r\n' + i + 'goto ' + start + '\r\n' + i + end + ':\r\n' + atend
			indentonce = True
			continue
		elif t == 'if':
			t, script, isname = token (script)
			nice_assert (t == '(', 'parenthesis required after if')
			e, before, script = parse_expr (dink, script, as_bool = True)
			t, script, isname = token (script)
			nice_assert (t == ')', 'parenthesis not closed for if')
			ret += before + i + 'if (' + e + ')\r\n'
			# Don't add the atend code here.
			indentonce = True
			continue
		elif t == 'int':
			t, script, isname = token (script)
			nice_assert (isname, 'local definition without name')
			name = t
			if name not in the_locals:
				the_locals += (name,)
			t, script, isname = token (script)
			if t == '=':
				e, before, script = parse_expr (dink, script, as_bool = False)
				ret += before + i + 'int &' + mangle (name) + ' = ' + e + ';\r\n'
			else:
				ret += i + 'int &' + mangle (name) + ';\r\n'
				script = t + ' ' + script
		elif t == 'goto':
			t, script, isname = token (script)
			nice_assert (isname, 'goto without target')
			print (filename + ": Warning: script is using goto; DON'T DO THAT!")
			ret += i + 'goto ' + t + ';\r\n'
		else:
			nice_assert (isname, 'syntax error')
			name = t
			t, script, isname = token (script)
			if t == ':':
				print (filename + ": Warning: defining a label is only useful for goto; DON'T DO THAT!")
				ret += i + name + ':\r\n'
			elif t in ['=', '+=', '-=']:
				nice_assert (check_exists (the_locals, name), 'use of undefined variable %s' % name)
				op = t
				e, before, script = parse_expr (dink, script, as_bool = False)
				ret += before + i + '&' + mangle (name) + ' ' + op + ' ' + e + ';\r\n'
			elif t in ['*=', '/=']:
				# Really, the target language is too broken for words...
				nice_assert (check_exists (the_locals, name), 'use of undefined variable %s' % name)
				op = t[0]
				e, before, script = parse_expr (dink, script, as_bool = False)
				ret += before + i + '&' + mangle (name) + ' ' + op + ' ' + e + ';\r\n'
			else:
				nice_assert (t == '(', 'syntax error')
				global current_tmp, max_tmp
				if current_tmp > max_tmp:
					max_tmp = current_tmp
				current_tmp = 0
				if name == 'choice_title':
					b, args, script = read_args (dink, script)
					nice_assert (len (args) >= 1 and len (args) <= 3 and args[0][0] == '"', 'invalid argument list for %s' % name)
					choice_title = b, args
				elif name == 'choice':
					b = ''
					c = i + 'choice_start ();\r\n'
					if choice_title != None:
						if len (choice_title) > 1:
							c += i + 'set_y %s\r\n' % choice_title[1]
						if len (choice_title) > 2:
							c += i + 'set_title_color %s\r\n' % choice_title[2]
						c += i + 'title_start();\r\n'
						c += i + '\t' + choice_title[1:-1] + '\r\n'
						c += i + 'title_end();\r\n'
						choice_title = None
					while True:
						t, script, isname = token (script)
						if t[0] != '"':
							e, before, script = parse_expr (dink, t + script, restart = False, as_bool = True)
							t, script, isname = token (script)
							nice_assert (t[0] == '"', 'choice requires a string')
							b += before
							t = e + ' ' + t
						c += i + t + '\r\n'
						t, script, isname = token (script)
						if t == ')':
							break
						nice_assert (t == ',', 'choice requires a comma')
					ret += b + c + i + 'choice_end ();\r\n'
				else:
					b, args, script = read_args (dink, script)
					f, a, bf = mangle_function (name, args, dink)
					ret += b + bf + i + f + '(' + ', '.join (a) + ');\r\n'
		realatend = atend
		atend = ''
		t, script, isname = token (script)
		nice_assert ((t == ';'), 'missing semicolon')
	return ret

class Sprite:
	pass

class Room:
	def __init__ (self, parent, root = None):
		self.parent = parent
		self.sprite = {}
		if root == None:
			self.tiles = [[[0, 0, 0] for x in range (12)] for y in range (8)]
			self.hard = ''
			self.script = ''
			self.music = ''
			self.indoor = False
			self.codes = []
			return
		global filename
		filename = os.path.join (root, 'info' + os.extsep + 'txt')
		f = open (filename)
		self.tiles = []
		for ty in range (8):
			ln = f.readline ()
			self.tiles += ([[int (z) for z in y.split (',')] for y in ln.split ()],)
			nice_assert (len (self.tiles[-1]) == 12, 'invalid line in %s/info.txt: not 12 tiles on a line' % root)
		info = readlines (f)
		info, self.hard = get (info, 'hard', '')
		info, self.script = get (info, 'script', '')
		info, self.music = get (info, 'music', '')
		info, self.indoor = get (info, 'indoor', False)
		nice_assert (info == {}, 'unused data in %s/info.txt' % root)
		sdir = os.path.join (root, "sprite")
		self.codes = []
		for s in os.listdir (sdir):
			filename = os.path.join (sdir, s)
			info = readlines (open (filename))
			r = re.match ('(.+?)(-(\d*?))?(\..*)?$', s)
			base = r.group (1)
			s = base
			i = 0
			while s in self.sprite:
				s = base + '-%d' % i
				i += 1
			self.sprite[s] = Sprite ()
			if r.group (3) != None:
				self.sprite[s].num = int (r.group (3))
				nice_assert (self.sprite[s].num not in self.codes, 'duplicate definition of sprite code %d' % self.sprite[s].num)
				self.codes += (self.sprite[s].num,)
			else:
				self.sprite[s].num = None
			info, self.sprite[s].x = get (info, 'x', int)
			info, self.sprite[s].y = get (info, 'y', int)
			info, seq = get (info, 'seq', base)
			seq = seq.split ()
			if len (seq) == 1:
				self.sprite[s].seq = seq[0]
			elif len (seq) == 2:
				self.sprite[s].seq = (seq[0], int (seq[1]))
			else:
				print 'Warning: strange seq:', seq
				self.sprite[s].seq = None
			info, self.sprite[s].frame = get (info, 'frame', 1)
			info, self.sprite[s].type = get (info, 'type', 1)	# 0 for background, 1 for person or sprite, 3 for invisible
			info, self.sprite[s].size = get (info, 'size', 100)
			info, self.sprite[s].brain = get (info, 'brain', 'none')
			info, self.sprite[s].script = get (info, 'script', '')
			info, self.sprite[s].speed = get (info, 'speed', 1)
			info, self.sprite[s].base_walk = get (info, 'base_walk', '')
			info, self.sprite[s].base_idle = get (info, 'base_idle', '')
			info, self.sprite[s].base_attack = get (info, 'base_attack', '')
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
				self.sprite[s].warp = [int (x) for x in w.split ()]
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
			nice_assert (info == {}, 'unused data for sprite %s' % s)
		code = 0
		for s in self.sprite:
			if self.sprite[s].num != None:
				continue
			while code in self.codes:
				code += 1
			self.sprite[s].num = code
			self.codes += (code,)
	def add_sprite (self, pos, seq, frame):
		if type (seq) == str:
			s = seq
			the_seq = self.parent.seq.find_seq (s)
			if the_seq == None:
				print ('seq %s not found' % s)
				return None
			brain = the_seq.brain
			script = the_seq.script
			walk = ''
			attack = ''
			die = ''
			hard = the_seq.hard
		else:
			s = seq[0]
			the_collection = self.parent.seq.find_collection (s)
			if the_collection == None:
				print ('collection %s not found' % s)
				return None
			if seq[1] not in the_collection:
				print ('direction %d not in collection %s' % (seq[1], seq[0]))
				return None
			the_seq = the_collection[seq[1]]
			brain = the_collection['brain']
			script = the_collection['script']
			walk = seq[0]
			attack = the_collection['attack']
			die = the_collection['die']
			hard = False
		os = s
		i = 0
		while s in self.sprite:
			s = os + '-%d' % i
			i += 1
		self.sprite[s] = Sprite ()
		self.sprite[s].x = pos[0]
		self.sprite[s].y = pos[1]
		self.sprite[s].seq = seq
		self.sprite[s].frame = frame
		self.sprite[s].type = 1
		self.sprite[s].size = 100
		self.sprite[s].brain = brain
		self.sprite[s].script = script
		self.sprite[s].speed = 1
		self.sprite[s].base_walk = walk
		self.sprite[s].base_idle = ''
		self.sprite[s].base_attack = attack
		self.sprite[s].timer = 33
		self.sprite[s].que = 0
		self.sprite[s].hard = hard
		self.sprite[s].left = 0
		self.sprite[s].top = 0
		self.sprite[s].right = 0
		self.sprite[s].bottom = 0
		self.sprite[s].warp = None
		self.sprite[s].touch_seq = ''
		self.sprite[s].base_die = die
		self.sprite[s].gold = 0
		self.sprite[s].hitpoints = 0
		self.sprite[s].strength = 0
		self.sprite[s].defense = 0
		self.sprite[s].exp = 0
		self.sprite[s].sound = ''
		self.sprite[s].vision = 0
		self.sprite[s].nohit = False
		self.sprite[s].touch_damage = 0
		code = 0
		while code in self.codes:
			code += 1
		self.sprite[s].num = code
		self.codes += (code,)
		return s
	def save (self, n):
		y = (n - 1) / 32
		x = n - y * 32 - 1
		d = os.path.join (self.parent.root, 'world', '%03d-%02d-%02d' % (n, x, y))
		if not os.path.isdir (d):
			os.mkdir (d)
		f = open (os.path.join (d, 'info' + os.extsep + 'txt'), 'w')
		for y in range (8):
			f.write (' '.join ([','.join ([str (z) for z in self.tiles[y][x]]) for x in range (12)]) + '\n')
		put (f, 'hard', self.hard, '')
		put (f, 'script', self.script, '')
		put (f, 'music', self.music, '')
		put (f, 'indoor', self.indoor, False)
		sd = os.path.join (d, 'sprite')
		os.mkdir (sd)
		for s in self.sprite:
			r = re.match ('(.+?)(-\d*?)?(\..*)?$', s)
			base = r.group (1)
			f = open (os.path.join (sd, '%s-%d' % (base, self.sprite[s].num)), 'w')
			put (f, 'x', self.sprite[s].x)
			put (f, 'y', self.sprite[s].y)
			if type (self.sprite[s].seq) == str:
				seq = self.sprite[s].seq
			else:
				seq = '%s %d' % self.sprite[s].seq
			put (f, 'seq', seq, base)
			put (f, 'frame', self.sprite[s].frame, 1)
			put (f, 'type', self.sprite[s].type, 1)
			put (f, 'size', self.sprite[s].size, 100)
			put (f, 'brain', self.sprite[s].brain, 'none')
			put (f, 'script', self.sprite[s].script, '')
			put (f, 'speed', self.sprite[s].speed, 1)
			put (f, 'base_walk', self.sprite[s].base_walk, '')
			put (f, 'base_idle', self.sprite[s].base_idle, '')
			put (f, 'base_attack', self.sprite[s].base_attack, '')
			put (f, 'timer', self.sprite[s].timer, 33)
			put (f, 'que', self.sprite[s].que, 0)
			put (f, 'hard', self.sprite[s].hard, True)
			put (f, 'left', self.sprite[s].left, 0)
			put (f, 'top', self.sprite[s].top, 0)
			put (f, 'right', self.sprite[s].right, 0)
			put (f, 'bottom', self.sprite[s].bottom, 0)
			if self.sprite[s].warp != None:
				put (f, 'warp', ' '.join ([str (x) for x in self.sprite[s].warp]))
			put (f, 'touch_seq', self.sprite[s].touch_seq, '')
			put (f, 'base_die', self.sprite[s].base_die, '')
			put (f, 'gold', self.sprite[s].gold, 0)
			put (f, 'hitpoints', self.sprite[s].hitpoints, 0)
			put (f, 'strength', self.sprite[s].strength, 0)
			put (f, 'defense', self.sprite[s].defense, 0)
			put (f, 'exp', self.sprite[s].exp, 0)
			put (f, 'sound', self.sprite[s].sound, '')
			put (f, 'vision', self.sprite[s].vision, 0)
			put (f, 'nohit', self.sprite[s].nohit, False)
			put (f, 'touch_damage', self.sprite[s].touch_damage, 0)

class World:
	def __init__ (self, parent):
		self.parent = parent
		self.room = {}
		if self.parent.root == None:
			return
		d = os.path.join (parent.root, 'world')
		for y in range (24):
			for x in range (32):
				n = y * 32 + x + 1
				dirname = os.path.join (d, '%03d-%02d-%02d' % (n, x, y))
				if not os.path.exists (dirname):
					continue
				self.room[n] = Room (parent, dirname)
		for f in os.listdir (d):
			r = re.match ('(\d{3})-(\d{2})-(\d{2})$', f)
			if r == None:
				if re.match ('\d+-', f) != None:
					sys.stderr.write ("Warning: not using %s as room\n" % f)
				continue
			n, x, y = [int (k) for k in r.groups ()]
			if x >= 32 or y >= 24 or n != y * 32 + x + 1:
				sys.stderr.write ("Warning: not using %s as room (%d != %d * 32 + %d + 1)\n" % (f, n, y, x))
	def save (self):
		os.mkdir (os.path.join (self.parent.root, 'world'))
		for r in self.room:
			self.room[r].save (r)
	def write_sprite (self, spr, mdat, x, y):
		mdat.write (make_lsb (x, 4))
		mdat.write (make_lsb (y, 4))
		sq = self.parent.seq.find_seq (spr.seq)
		if sq == None:
			mdat.write (make_lsb (0, 4))
		else:
			mdat.write (make_lsb (sq.code, 4))
		mdat.write (make_lsb (spr.frame, 4))
		mdat.write (make_lsb (spr.type, 4))
		mdat.write (make_lsb (spr.size, 4))
		mdat.write (make_lsb (1, 4))	# active
		mdat.write (make_lsb (0, 4))	# rotation
		mdat.write (make_lsb (0, 4))	# special
		mdat.write (make_lsb (make_brain (spr.brain), 4))
		mdat.write (make_string (spr.script, 14))
		mdat.write ('\0' * 38)
		mdat.write (make_lsb (spr.speed, 4))
		def coll (which):
			if which == '':
				return 0
			return self.parent.seq.collection_code (which)
		mdat.write (make_lsb (coll (spr.base_walk), 4))
		mdat.write (make_lsb (coll (spr.base_idle), 4))
		mdat.write (make_lsb (coll (spr.base_attack), 4))
		mdat.write (make_lsb (0, 4))	# hit
		mdat.write (make_lsb (spr.timer, 4))
		mdat.write (make_lsb (spr.que, 4))
		mdat.write (make_lsb (not spr.hard, 4))
		mdat.write (make_lsb (spr.left, 4))
		mdat.write (make_lsb (spr.top, 4))
		mdat.write (make_lsb (spr.right, 4))
		mdat.write (make_lsb (spr.bottom, 4))
		if spr.warp != None:
			mdat.write (make_lsb (1, 4))
			mdat.write (make_lsb (spr.warp[0], 4))
			mdat.write (make_lsb (spr.warp[1], 4))
			mdat.write (make_lsb (spr.warp[2], 4))
		else:
			mdat.write ('\0' * 16)
		if spr.touch_seq == '':
			mdat.write (make_lsb (0, 4))
		else:
			mdat.write (make_lsb (self.parent.seq.find_seq (spr.touch_seq).code, 4))
		mdat.write (make_lsb (coll (spr.base_die), 4))
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
	def build (self, root):
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink' + os.extsep + 'dat'), "wb")
		ddat.write ('Smallwood' + '\0' * 15)
		rooms = []
		for i in range (1, 32 * 24 + 1):
			if not i in self.room:
				ddat.write (make_lsb (0, 4))
				continue
			rooms += (i,)
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
					bmp, tx, ty = self.room[s].tiles[y][x]
					mdat.write (make_lsb (bmp * 128 + ty * 12 + tx, 4))
					mdat.write ('\0' * 4)
					mdat.write (make_lsb (self.parent.tile.find_hard (self.room[s].hard, x, y, bmp, tx, ty), 4))
					mdat.write ('\0' * 68)
			mdat.write ('\0' * 320)
			# sprites
			# sprite 0 is never used...
			mdat.write ('\0' * 220)
			editcode = 1
			for sp in self.room[s].sprite:
				spr = self.room[s].sprite[sp]
				spr.editcode = editcode
				editcode += 1
				self.write_sprite (spr, mdat, spr.x, spr.y)
			n = len (self.room[s].sprite)
			extra = [(x, y) for (x, y) in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)) if 0 <= (s - 1) % 32 + x < 32 and 0 <= (s - 1) / 32 + y < 24]
			for ex, ey in extra:
				eroom = ((s - 1) / 32 + ey) * 32 + (s - 1) % 32 + ex + 1
				if eroom not in self.room:
					continue
				for sp in self.room[eroom].sprite:
					spr = self.room[eroom].sprite[sp]
					sq = self.parent.seq.find_seq (spr.seq)
					tx = spr.x + ex * 12 * 50 - 20
					ty = spr.y + ey * 8 * 50
					if tx + sq.boundingbox[2] >= 0 and tx + sq.boundingbox[0] < 12 * 50 and ty + sq.boundingbox[3] >= 0 and ty + sq.boundingbox[1] < 8 * 50:
						self.write_sprite (spr, mdat, spr.x + ex * 12 * 50, spr.y + ey * 8 * 50)
						n += 1
			mdat.write ('\0' * 220 * (100 - n))
			# base script
			mdat.write (make_string (self.room[s].script, 21))
			mdat.write ('\0' * 1019)

class Tile:
	# self.tile is a list of (tiles, hardness, code). Code means:
	# 0: hardness from original, image from original
	# 1: hardness from original, image from dmod
	# 2: hardness from dmod, image from original
	# 3: hardness from dmod, image from dmod
	def __init__ (self, parent):
		self.parent = parent
		self.hard = {}
		self.tile = [None] * 41
		d = os.path.join (parent.root, "tile")
		if os.path.exists (d):
			ext = os.extsep + 'png'
			for t in os.listdir (d):
				h = '-hard' + ext
				if not t.endswith (h):
					continue
				base = t[:-len (h)]
				image = make_hard_image (os.path.join (d, t))
				if re.match ('^\d\d$', base):
					n = int (base) - 1
					nice_assert (n < 41, 'tile screen must be at most 41')
					t = os.path.join (d, base + ext)
					if os.path.exists (t):
						self.tile[n] = (convert_image (Image.open (t)), image, 3)
					else:
						self.tile[n] = (convert_image (Image.open (filepart (*tilefiles[n]))), image, 2)
				else:
					self.hard[base] = image
		for n in range (41):
			if self.tile[n] == None:
				t = os.path.join (d, str (n) + ext)
				if os.path.exists (t):
					tilefile = (convert_image (Image.open (t)), 1)
				else:
					tilefile = (convert_image (Image.open (filepart (*tilefiles[n]))), 0)
				image = make_hard_image (os.path.join (cachedir, 'hard-%02d' % (n + 1) + os.extsep + 'png'))
				self.tile[n] = (tilefile[0], image, tilefile[1])
	def find_hard (self, hard, x, y, bmp, tx, ty):
		if hard != '':
			nice_assert (hard in self.hard, 'reference to undefined hardness screen %s' % hard)
			ret = self.hardmap[hard][y][x]
			if ret != self.tilemap[bmp][ty][tx]:
				return ret
		return 0
	def save (self):
		if len (self.hard) == 0:
			for i in range (41):
				if self.tile[i] != 0:
					break
			else:
				return
		d = os.path.join (self.parent.root, 'tile')
		os.mkdir (d)
		for h in self.hard:
			self.hard[h].save (os.path.join (d, h + '-hard' + os.extsep + 'png'))
		for n in range (41):
			if self.tile[n][2] == 1 or self.tile[n][2] == 3:
				self.tile[n][0].save (os.path.join (d, '%02d' % n + os.extsep + 'png'))
			if self.tile[n][2] == 2 or self.tile[n][2] == 3:
				self.tile[n][1].save (os.path.join (d, '%02d-hard' % n + os.extsep + 'png'))
	def write_hard (self, image, h):
		'''Write hardness of all tiles in a given screen to hard.dat (opened as h). Return map of indices used.'''
		ret = [None] * 8
		for y in range (8):
			ret[y] = [None] * 12
			for x in range (12):
				if image.size[0] < (x + 1) * 50 or image.size[1] < (y + 1) * 50:
					# Don't try to read out of bounds.
					continue
				# Get the tile.
				tile = image.crop ((x * 50, y * 50, (x + 1) * 50, (y + 1) * 50))
				s = tile.tostring ()
				try:
					# Check if it's already in the file.
					m = self.hmap.index (s)
				except ValueError:
					# Not in map yet; add new tile to file and map.
					m = len (self.hmap)
					# Note that x and y are reversed. Why? Because Seth liked it that way...
					for tx in range (50):
						for ty in range (50):
							p = tile.getpixel ((tx, ty))
							if p == (0, 0, 0, 0):
								h.write ('\0')
							elif p == (255, 255, 255, 128):
								h.write ('\1')
							elif p == (0, 0, 255, 128):
								h.write ('\2')
							else:
								error ('invalid pixel in hard tile: %s' % str (p))
						h.write ('\0')	# junk
					h.write ('\0' * 58)	# junk
					self.hmap += (s,)
				ret[y][x] = m
		return ret
	def build (self, root):
		# Write tiles/*
		# Write hard.dat
		d = os.path.join (root, 'tiles')
		if not os.path.exists (d):
			os.mkdir (d)
		h = open (os.path.join (root, 'hard.dat'), "wb")
		self.hmap = []
		self.hardmap = {}
		self.tilemap = [None] * 41
		for t in self.hard:
			# Write hardness for custom hard screens.
			self.hardmap[t] = self.write_hard (self.hard[t], h)
		for n in range (41):
			if self.tile[n][2] == 1 or self.tile[n][2] == 3:
				# Write custom tile screens.
				self.tile[n][0].save (os.path.join (d, str (t) + os.extsep + 'bmp'))
			# Write hardness for standard tiles.
			self.tilemap[n] = self.write_hard (self.tile[n][1], h)
		nice_assert (len (self.hmap) <= 800, 'More than 800 hardness tiles defined (%d)' % len (self.hmap))
		h.write ('\0' * (51 * 51 + 1 + 6) * (800 - len (self.hmap)))
		# Write hardness index for tile screens.
		for t in range (41):
			m = self.tilemap[t]
			for y in range (8):
				for x in range (12):
					if m[y][x] != None:
						h.write (make_lsb (m[y][x], 4))
					else:
						# fill it with junk.
						h.write (make_lsb (0, 4))
			# Fill up with junk.
			h.write ('\0' * 32 * 4)
		# Fill the rest with junk.
		h.write ('\0' * (8000 - len (self.tile) * 8 * 12 * 4))

# A sequence has members:
#       frames, list with members:
#               position        Hotspot position.
#               hardbox		Hardbox: left, top, right, bottom.
#               boundingbox      Bounding box: left, top, right, bottom.
#               delay           Delay value for this frame.
#               source          For copied frames, source; None otherwise.
#               cache           Tuple of filename, offset, length of location of file
#       boundingbox      Bounding box: left, top, right, bottom.
#       delay           default delay.
#       hardbox         default hardbox
#       position        default position
#       filepath        name for use in dink.ini
#       repeat          bool, whether the sequence is set for repeating
#       special         int, special frame
#       now             bool, whether to load now
#       code            int
#       preload         string, name of sequence to preload into this code
#       type            normal, notanim, black, or leftalign
class Seq:
	def __init__ (self, parent):
		"""Load all sequence and collection declarations from dink.ini, seq-names.txt (both internal) and seq/info.txt"""
		# General setup
		self.parent = parent
		self.seq = sequences
		self.collection = collections
		self.current_collection = None
		if self.parent.root == None:
			return
		d = os.path.join (parent.root, "seq")
		# Read info specific to this dmod.
		global filename
		filename = os.path.join (d, 'info' + os.extsep + 'txt')
		infofile = open (filename)
		while True:
			info = readlines (infofile)
			if info == {}:
				break
			if 'collection' in info:
				# The next blocks with a direction are a collection.
				info, self.current_collection = get (info, "collection")
				nice_assert (info == {}, 'unused data in %s' % infofile)
				if self.current_collection not in self.collection:
					self.collection[self.current_collection] = {code: -1}
				continue
			elif 'append' in info:
				# This block is about a sequence which was declared in dink.ini.
				self.current_collection = None
				info, base = get (info, 'append')
				nice_assert (base in self.seq, 'append to undefined sequence %s' % base)
			else:
				if 'name' in info:
					# This block defines a new sequence.
					self.current_collection = None
					info, base = get (info, 'name')
					nice_assert (base not in self.seq, 'sequence %s already exists' % base)
					self.seq[base] = Sequence ()
					is_new = True
				else:
					# This block is part of a collection.
					nice_assert (self.current_collection != None, 'collection definition required')
					base = None
					self.seq[None] = Sequence ()
					info, self.direction = get (info, 'direction', int)
					nice_assert (self.direction >= 1 and self.direction <= 9 and self.direction != 5, 'invalid direction %d' % self.direction)
					info, is_new = get (info, 'new', True)
				if is_new:
					self.seq[base].code = -1
					self.seq[base].frames = []
					self.seq[base].repeat = False
					if base == None:
						name = '%s-%d' % (self.current_collection, self.seq[None].direction)
					else:
						name = base
					self.seq[base].filepath = 'graphics\\custom\\%s-' % name
					self.seq[base].type = 'normal'
					self.seq[base].special = None
					self.seq[base].preload = ''
					self.seq[base].delay = 1
					self.seq[base].hardbox = (0, 0, 0, 0)
					self.seq[base].position = (0, 0)
					self.seq[base].now = False
				else:
					# The collection part should be changed. Remove it now, reinsert it at the end.
					self.seq[base] = self.collections[self.current_collection].seq[self.seq[base].direction]
					del self.collections[self.current_collection].seq[self.seq[base].direction]
			info, self.seq[base].repeat = get (info, 'repeat', self.seq[base].repeat)
			info, self.seq[base].special = get (info, 'special', self.seq[base].special)
			info, self.seq[base].now = get (info, 'load-now', self.seq[base].now)
			info, self.seq[base].preload = get (info, 'preload', self.seq[base].preload)
			info, self.seq[base].type = get (info, 'type', self.seq[base].type)
			nice_assert (self.seq[base].type in ('normal', 'black', 'leftalign', 'notanim'), 'invalid special type %s' % self.seq[base].type)
			info, num = get (info, 'frames', len (self.seq[base].frames))
			if len (self.seq[base].frames) < num:
				self.seq[base].frames += [None] * (num - len (self.seq[base].frames))
			else:
				self.seq[base].frames = self.seq[base].frames[:num]
			for f in range (num):
				info, seq = get (info, 'seq-%d', '')
				if seq != '':
					if self.seq[base].frames[f] == None:
						self.seq[base].frames[f] = Frame ()
					info, frame = get (info, 'frame-%d', int)
					self.seq[base].frames[f].source = (seq, frame)
				else:
					nice_assert (self.seq[base].frames[f] != None, 'frame %d of sequence %s not defined' % (f, base))
				# TODO: fill frame members.
			info, box = get (info, 'hardbox', '')
			if box != '':
				box = [int (x) for x in box.split ()]
				nice_assert (len (box) == 4, 'hardbox must have 4 members')
				self.seq[base].hardbox = box
				for f in range (1, len (self.seq[base].frames)):
					self.seq[base].frames[f].hardbox = box
			info, delay = get (info, 'delay', 0)
			if delay > 0:
				self.seq[base].delay = delay
				for f in range (1, len (self.seq[base].frames)):
					self.seq[base].frames[f].delay = delay
			nice_assert (info == {}, 'unused data in %s' % infofile)
			if self.current_collection != None:
				nice_assert (base == None, 'cannot define name (%s) for collection member (%s)' % (base, self.current_collection))
				nice_assert (self.direction not in self.collection[self.current_collection], 'duplicate definition of direction %d for collection %s' % (self.direction, self.current_collection))
				self.collection[self.current_collection].seq[self.direction] = self.seq[base]
				del self.seq[base]
		# Give codes to all unassigned collections and sequences.
		nextseq = 1
		for s in self.seq:
			if self.seq[s].code == -1:
				while nextseq in codes:
					nextseq += 1
				self.seq[s].code = nextseq
				codes += (nextseq,)
				nextseq += 1
	def find_seq (self, name):
		if not name:
			return None
		if type (name) == int:
			for i in self.seq:
				if self.seq[i].code == name:
					return self.seq[i]
			for c in self.collection:
				for i in self.collection[c]:
					if i not in (1,2,3,4,6,7,8,9):
						continue
					if self.collection[c][i].code == name:
						return self.collection[c][i]
			print (name)
			raise AssertionError ('undefined numerical code for find_seq')
		elif type (name) == str:
			if name not in self.seq:
				return None
			return self.seq[name]
		else:
			if name[0] not in self.collection or int (name[1]) not in self.collection[name[0]]:
				return None
			return self.collection[name[0]][int (name[1])]
	def find_collection (self, name):
		if name not in self.collection:
			return None
		return self.collection[name]
	def collection_code (self, name):
		if type (name) == str and name.startswith ('*'):
			seq = self.find_seq (name[1:])
			if seq == None:
				return 0
			return seq.code
		coll = self.find_collection (name)
		if coll == None:
			return 0
		return coll['code']
	def save (self):
		d = os.path.join (self.parent.root, 'seq')
		os.mkdir (d)
		f = open (os.path.join (d, 'info' + os.extsep + 'txt'), 'w')
		# TODO
	def build_seq (self, ini, seq):
		if seq.preload:
			ini.write ('// Preload\r\n')
			ini.write ('load_sequence_now %s %d\r\n' % (seq.preload, seq.code))
		if seq.now:
			now = '_now'
		else:
			now = ''
		if seq.type == 'normal':
			if seq.position == None:
				if seq.delay != None:
					ini.write ('load_sequence%s %s %d %d\r\n' % (now, seq.filepath, seq.code, seq.delay))
				else:
					ini.write ('load_sequence%s %s %d\r\n' % (now, seq.filepath, seq.code))
			else:
				if seq.delay != None:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d %d\r\n' % (now, seq.filepath, seq.code, seq.delay, seq.position[0], seq.position[1], seq.hardbox[0], seq.hardbox[1], seq.hardbox[2], seq.hardbox[3]))
				else:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d\r\n' % (now, seq.filepath, seq.code, seq.position[0], seq.position[1], seq.hardbox[0], seq.hardbox[1], seq.hardbox[2], seq.hardbox[3]))
		else:
			ini.write ('load_sequence%s %s %d %s\r\n' % (now, seq.filepath, seq.code, seq.type.upper ()))
		for f in range (1, len (seq.frames)):
			# TODO: save images.
			if seq.frames[f].source != None:
				ini.write ('set_frame_frame %d %d %d %d\r\n' % (seq.code, f, self.find_seq (seq.frames[f].source[0]).code, seq.frames[f].source[1]))
			if (len (seq.frames[f].hardbox) == 4 and seq.frames[f].hardbox != seq.hardbox) or (len (seq.frames[f].position) == 2 and seq.frames[f].position != seq.position):
				ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\r\n' % (seq.code, f, seq.frames[f].position[0], seq.frames[f].position[1], seq.frames[f].hardbox[0], seq.frames[f].hardbox[1], seq.frames[f].hardbox[2], seq.frames[f].hardbox[3]))
			if seq.frames[f].source != None or seq.frames[f].delay != seq.delay:
				ini.write ('set_frame_delay %d %d %d\r\n' % (seq.code, f, int (seq.frames[f].delay)))
			if seq.special == f:
				ini.write ('set_frame_special %d %d 1\r\n' % (seq.code, f))
		if seq.repeat:
			ini.write ('set_frame_frame %d %d -1\r\n' % (seq.code, len (seq.frames)))
	def build (self, root):
		# Write graphics/*
		# Write dink.ini
		d = os.path.join (root, 'graphics')
		if not os.path.exists (d):
			os.mkdir (d)
		ini = open (os.path.join (root, 'dink' + os.extsep + 'ini'), 'w')
		for c in self.collection:
			for s in self.collection[c]:
				if s not in (1,2,3,4,6,7,8,9):
					continue
				self.build_seq (ini, self.collection[c][s])
		for g in self.seq:
			self.build_seq (ini, self.seq[g])

class Sound:
	def __init__ (self, parent):
		self.parent = parent
		ext = os.extsep + 'wav'
		self.sound = {}
		self.music = {}
		other = []
		codes = []
		if self.parent.root == None:
			return
		d = os.path.join (parent.root, "sound")
		for s in os.listdir (d):
			global filename
			filename = os.path.join (d, s)
			data = open (filename).read ()
			if not s.endswith (ext):
				continue
			r = re.match ('(\d+)-', s)
			if not r:
				other += ((s[:-len (ext)], data),)
			else:
				code = int (r.group (1))
				self.sound[s[len (r.group (0)):]] = (code, data)
				nice_assert (code not in codes, 'duplicate definition of sound %d' % code)
				codes += (code,)
		i = 1
		for s in other:
			while i in codes:
				i += 1
			self.sound[s[0]] = (i, s[1])
			i += 1
		ext = os.extsep + 'mid'
		d = os.path.join (parent.root, "music")
		code = 1
		for s in os.listdir (d):
			if not s.endswith (ext):
				continue
			self.music[s[:-len (ext)]] = (code, data)
			code += 1
	def find_sound (self, name):
		"""Find wav file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		return self.sound[name][0]
	def find_music (self, name):
		"""Find midi file with given name. Return 0 for empty string, raise exception for not found"""
		if name == '':
			return 0
		nice_assert (name in self.music, 'reference to undefined music %s' % name)
		return self.music[name][0]
	def save (self):
		d = os.path.join (self.parent.root, "sound")
		os.mkdir (d)
		for i in self.sound:
			open (os.path.join (d, '%s-%d' % (i, self.sound[i][0]) + os.extsep + 'wav'), 'w').write (self.sound[i][1])
		d = os.path.join (self.parent.root, "music")
		os.mkdir (d)
		for i in self.music:
			open (os.path.join (d, '%d' % self.music[i][0] + os.extsep + 'mid'), 'w').write (self.music[i][1])
	def build (self, root):
		# Write sound/*
		dst = os.path.join (root, 'sound')
		if not os.path.exists (dst):
			os.mkdir (dst)
		src = os.path.join (self.parent.root, 'sound')
		for s in self.sound:
			if self.sound[s][1] == '':
				continue
			open (os.join (dst, s + os.extsep + 'wav'), 'w').write (self.sound[s][1])
		for s in self.music:
			if self.music[s][1] == '':
				continue
			open (os.join (dst, str (self.music[s][0]) + os.extsep + 'mid'), 'w').write (self.music[s][1])

class Script:
	def __init__ (self, parent):
		self.parent = parent
		self.data = {}
		if self.parent.root == None:
			self.title_music = ''
			self.title_color = 0
			self.title_bg = ''
			self.start_map = 400
			self.start_x = 320
			self.start_y = 200
			self.title_pointer_seq = 'special'
			self.title_pointer_frame = 8
			self.title_script = ''
			self.start_script = ''
			self.title_sprite = []
			self.title_button = []
			return
		d = os.path.join (parent.root, "script")
		for s in os.listdir (d):
			ext = os.extsep + 'c'
			if not s.endswith (ext):
				continue
			base = s[:-len (ext)]
			nice_assert (base not in self.data, 'duplicate definition of script %s' % base)
			self.data[base] = open (os.path.join (d, s)).read ()
		global filename
		filename = os.path.join (parent.root, "title" + os.extsep + "txt")
		f = open (filename)
		info = readlines (f)
		info, self.title_music = get (info, 'music', '')
		info, self.title_color = get (info, 'color', 0)
		info, self.title_bg = get (info, 'background', '')
		info, s = get (info, 'start')
		self.start_map, self.start_x, self.start_y = [int (x) for x in s.split ()]
		info, p = get (info, 'pointer', 'special 8')
		p = p.split ()
		self.title_pointer_seq, self.title_pointer_frame = p[0], int (p[1])
		info, self.title_script = get (info, 'title-script', '')
		info, self.start_script = get (info, 'start-script', '')
		info, n = get (info, 'sprites', 0)
		self.title_sprite = []
		for s in range (n):
			info, spr = get (info, 'sprite-%d' % (s + 1))
			spr = spr.split ()
			if len (spr) == 4:
				spr += ('repeat',)
			if len (spr) == 5:
				spr += ('',)
			nice_assert (len (spr) == 6, 'sprite-* must have 4, 5 or 6 arguments (%d given)' % len (spr))
			self.title_sprite += ((spr[0], int (spr[1]), int (spr[2]), int (spr[3]), spr[4], spr[5]),)
		info, n = get (info, 'buttons', int)
		self.title_button = []
		for s in range (n):
			info, b = get (info, 'button-%d' % (s + 1))
			b = b.split ()
			nice_assert (len (b) == 5, 'button-* must have 5 arguments (%d given)' % len (b))
			self.title_sprite += ((b[0], int (b[1]), int (b[2]), int (b[3]), 'button', b[4]),)
		nice_assert (info == {}, 'unused data in title definition')
	def save (self):
		d = os.path.join (self.parent.root, "script")
		os.mkdir (d)
		for s in self.data:
			open (os.path.join (d, s + os.extsep + 'c'), 'w').write (self.data[s])
		f = open (os.path.join (self.parent.root, "title" + os.extsep + "txt"), 'w')
		put (f, 'music', self.title_music, '')
		put (f, 'color', self.title_color, 0)
		put (f, 'background', self.title_bg, '')
		put (f, 'start', '%d %d %d' % (self.start_map, self.start_x, self.start_y))
		put (f, 'pointer', '%s %d' % (self.title_pointer_seq, self.title_pointer_frame), 'special 8')
		buttons = [x for x in self.title_sprite if x[4] == 'button']
		sprites = [x for x in self.title_sprite if x[4] != 'button']
		put (f, 'buttons', len (buttons))
		for i in range (len (buttons)):
			buttons[i] = buttons[i][:4] + buttons[i][5:]
			put (f, 'button-%d' % (i + 1), ' '.join ([str (x) for x in buttons[i]]))
		put (f, 'sprites', len (sprites))
		for i in range (len (sprites)):
			if sprites[i][5] == '':
				sprites[i][5:] = []
				if sprites[i][4] == 'repeat':
					sprites[i][4:] = []
			put (f, 'sprite-%d' % (i + 1), ' '.join (sprites[i]))
		put (f, 'title-script', self.title_script, '')
		put (f, 'start-script', self.start_script, '')
	def build (self, root):
		# Write Story/*
		d = os.path.join (root, 'story')
		if not os.path.exists (d):
			os.mkdir (d)
		for name in self.data:
			f = open (os.path.join (d, name + os.extsep + 'c'), 'w')
			f.write (preprocess (self.data[name], self.parent, name))
		# Write start.c
		s = open (os.path.join (d, 'start' + os.extsep + 'c'), 'w')
		s.write ('void main ()\r\n{\r\n')
		for n, snd in zip (range (len (self.parent.sound.sound)), self.parent.sound.sound):
			s.write ('\tload_sound ("%s.wav", %d);\r\n' % (snd, n))
		s.write ('\tset_dink_speed (3);\r\n\tsp_frame_delay (1,0);\r\n')
		if self.title_bg != '':
			s.write ('\tcopy_bmp_to_screen ("%s");\r\n' % self.title_bg)
		else:
			s.write ('\tfill_screen (%d);\r\n' % self.title_color)
		if self.title_script != '':
			s.write ('\tspawn ("%s");\r\n' % self.title_script)
		s.write ('''\
	load_sound("QUACK.WAV", 1);\r
	load_sound("PIG1.WAV", 2);\r
	load_sound("PIG2.WAV", 3);\r
	load_sound("PIG3.WAV", 4);\r
	load_sound("PIG4.WAV", 5);\r
	load_sound("BURN.WAV", 6);\r
	load_sound("OPEN.WAV", 7);\r
	load_sound("SWING.WAV", 8);\r
	load_sound("PUNCH.WAV", 9);\r
	load_sound("SWORD2.WAV", 10);\r
	load_sound("SELECT.WAV", 11);\r
	load_sound("WSCREAM.WAV", 12);\r
	load_sound("PICKER.WAV", 13);\r
	load_sound("GOLD.WAV", 14);\r
	load_sound("GRUNT1.WAV", 15);\r
	load_sound("GRUNT2.WAV", 16);\r
	load_sound("SEL1.WAV", 17);\r
	load_sound("ESCAPE.WAV", 18);\r
	load_sound("NONO.WAV", 19);\r
	load_sound("SEL2.WAV", 20);\r
	load_sound("SEL3.WAV", 21);\r
	load_sound("HIGH2.WAV", 22);\r
	load_sound("FIRE.WAV", 23);\r
	load_sound("SPELL1.WAV", 24);\r
	load_sound("CAVEENT.WAV", 25);\r
	load_sound("SNARL1.WAV", 26);\r
	load_sound("SNARL2.WAV", 27);\r
	load_sound("SNARL3.WAV", 28);\r
	load_sound("HURT1.WAV", 29);\r
	load_sound("HURT2.WAV", 30);\r
	load_sound("ATTACK1.WAV", 31);\r
	load_sound("CAVEENT.WAV", 32);\r
	load_sound("LEVEL.WAV", 33);\r
	load_sound("SAVE.WAV", 34);\r
	load_sound("SPLASH.WAV", 35);\r
	load_sound("SWORD1.WAV", 36);\r
	load_sound("BHIT.WAV", 37);\r
	load_sound("SQUISH.WAV", 38);\r
	load_sound("STAIRS.WAV", 39);\r
	load_sound("STEPS.WAV", 40);\r
	load_sound("ARROW.WAV", 41);\r
	load_sound("FLYBY.WAV", 42);\r
	load_sound("SECRET.WAV", 43);\r
	load_sound("BOW1.WAV", 44);\r
	load_sound("KNOCK.WAV", 45);\r
	load_sound("DRAG1.WAV", 46);\r
	load_sound("DRAG2.WAV", 47);\r
	load_sound("AXE.WAV", 48);\r
	load_sound("BIRD1.WAV", 49);\r
	sp_seq (1, 0);\r
	sp_brain (1, 13);\r
	sp_pseq (1, %d);\r
	sp_pframe (1, %d);\r
	sp_que (1, 20000);\r
	sp_noclip (1, 1);\r
	int &crap;\r
''' % (self.parent.seq.find_seq (self.title_pointer_seq).code, self.title_pointer_frame))
		for t in self.title_sprite:
			s.write ('\t&crap = create_sprite (%d, %d, %d, %d, %d);\r\n' % (t[2], t[3], make_brain (t[4]), self.parent.seq.find_seq (t[0]).code, t[1]))
			if t[5] != '':
				s.write ('\tsp_script(&crap, "%s");\r\n' % t[5])
				s.write ('\tsp_touch_damage (&crap, -1);\r\n')
			s.write ('\tsp_noclip (&crap, 1);\r\n')
		if self.title_music != '':
			s.write ('\tplaymidi ("%s.mid");\r\n' % self.title_music)
		s.write ('\tkill_this_task ();\r\n}\r\n')
		# Write main.c
		s = open (os.path.join (d, 'main' + os.extsep + 'c'), 'w')
		s.write ('void main ()\r\n{\r\n')
		global the_globals
		for v in the_globals:
			s.write ('\tmake_global_int ("&%s", %d);\r\n' % (v, the_globals[v]))
		for t in range (max_tmp):
			s.write ('\tmake_global_int ("&tmp%s", %d);\r\n' % (t, 0))
		s.write ('\tkill_this_task ();\r\n}\r\n')
		# Write start-game.c
		s = open (os.path.join (d, 'start-game' + os.extsep + 'c'), 'wb')
		s.write ('''\
void main ()\r
{\r
%s	wait (1);\r
	&player_map = %d;\r
	sp_x (1, %d);\r
	sp_y (1, %d);\r
	sp_base_walk (1, %d);\r
	sp_base_attack (1, %d);\r
	set_dink_speed (3);\r
	set_mode (2);\r
	reset_timer ();\r
	sp_dir (1, 4);\r
	sp_brain (1, %d);\r
	sp_que (1, 0);\r
	sp_noclip (1, 0);\r
	load_screen ();\r
	draw_screen ();\r
	&update_status = 1;\r
	draw_status ();\r
	kill_this_task ();\r
}\r
''' % (('\tspawn ("' + self.start_script + '");\r\n' if self.start_script != '' else ''), self.start_map, self.start_x, self.start_y, self.parent.seq.collection_code ('walk'), self.parent.seq.collection_code ('hit'), make_brain ('dink')))

class Dink:
	def __init__ (self, root):
		if root == None:
			self.root = None
		else:
			self.root = os.path.abspath (os.path.normpath (root))
		self.tile = Tile (self)
		self.world = World (self)
		self.seq = Seq (self)
		self.sound = Sound (self)
		self.script = Script (self)
		if root == None:
			self.info = ''
			self.preview = None
			self.splash = None
			return
		global filename
		filename = os.path.join (self.root, 'info' + os.extsep + 'txt')
		self.info = open (filename).read ()
		im = os.path.join (self.root, 'image')
		p = os.path.join (im, 'preview' + os.extsep + 'png')
		if os.path.exists (p):
			self.preview = convert_image (Image.open (p))
		else:
			self.preview = None
		p = os.path.join (im, 'splash' + os.extsep + 'png')
		if os.path.exists (p):
			self.splash = convert_image (Image.open (p))
		else:
			self.splash = None
	def save (self, root = None):
		if root != None:
			self.root = os.path.abspath (os.path.normpath (root))
		if os.path.exists (self.root):
			d = os.path.dirname (self.root)
			b = os.path.basename (self.root)
			l = os.listdir (d)
			src = [x for x in l if x.startswith (b + '.') and re.match ('^\d+$', x[len (b) + 1:])]
			if src == []:
				backup = self.root + '.0'
			else:
				src.sort (key = lambda x: int (x[len (b) + 1:]))
				backup = self.root + ('.%d' % (int (src[-1][len (b) + 1:]) + 1))
			os.mkdir (backup)
			for f in os.listdir (self.root):
				if not f.startswith ('.'):
					os.rename (os.path.join (self.root, f), os.path.join (backup, f))
		else:
			os.mkdir (self.root)
		self.tile.save ()
		self.world.save ()
		self.seq.save ()
		self.sound.save ()
		self.script.save ()
		open (os.path.join (self.root, 'info' + os.extsep + 'txt'), 'w').write (self.info)
		im = os.path.join (self.root, 'image')
		os.mkdir (im)
		if self.preview != None:
			p = os.path.join (im, 'preview' + os.extsep + 'png')
			self.preview.save (p)
		if self.splash != None:
			p = os.path.join (im, 'splash' + os.extsep + 'png')
			self.splash.save (p)
	def build (self, root):
		if not os.path.exists (root):
			os.mkdir (root)
		# Write tiles/*
		self.tile.build (root)
		# Write dink.dat
		# Write hard.dat
		# Write map.dat
		self.world.build (root)
		# Write dink.ini
		# Write graphics/*
		self.seq.build (root)
		# Write sound/*
		self.sound.build (root)
		# Write story/* This must be last, because preprocess needs all kinds of things to be initialized.
		self.script.build (root)
		# Write the rest
		if self.preview != None:
			self.preview.save (os.path.join (root, 'preview' + os.extsep + 'bmp'))
		if self.splash != None:
			self.splash.save (os.path.join (root, 'tiles', 'splash' + os.extsep + 'bmp'))
		open (os.path.join (root, 'dmod' + os.extsep + 'diz'), 'w').write (self.info)
	def play (self, map = None, x = None, y = None):
		if y != None:
			tmp = self.script.start_map, self.script.start_x, self.script.start_y, self.script.title_script
			self.script.start_map = map
			self.script.start_x = x
			self.script.start_y = y
			self.script.title_script = 'start-game'
		builddir = tempfile.mkdtemp ()
		try:
			self.build (builddir)
			os.spawnl (os.P_WAIT, dinkprog, dinkprog, '-g', builddir, '-r', dinkdir, '-w')
		finally:
			shutil.rmtree (builddir)
		if y != None:
			self.script.start_map, self.script.start_x, self.script.start_y, self.script.title_script = tmp

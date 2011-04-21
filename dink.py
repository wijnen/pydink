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

dink_ini_path = '/usr/share/games/dink/dink/Dink.ini'
dink_ini = open (dink_ini_path).readlines ()
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

seq_names = r'''#
idle 10
duck 20
pig 40
walk 70
hit 100
duckbloody 110
duckhead 120
pillbug 130
pillbugdie 140
dragon 200
dragondie 210
redmaiden 220
oldman 230
brownmaiden 240
bluemaiden 250
fairy 260
redknight 270
blueknight 280
silverknight 290
goldknight 300
push 310
shoot 320
girl 330
merchant 340
mom 350
brownmom 360
bluemerchant 370
greenmerchant 380
purplemerchant 390
soldier 400
peasant 410
comet 500
fireball 510
seeding 520
bonca 530
boncaattack 540
boncadie 550
purplegnome 560
bluegnome 570
greengnome 580
grayboncaattack 590
graybonca 600
purplebonca 610
purpleboncaattack 620
slayerattack 630
slayer 640
bluepuddle 650
bluepuddledie 660
greenpuddle 670
greenpuddledie 680
redpuddle 690
redpuddledie 700
redknightattack 710
silverknightattack 720
blueknightattack 730
goldknightattack 740
hammergoblinattack 750
hammergoblin 760
horngoblinattack 770
horngoblin 780
goblinattack 790
goblin 800
giantattack 810
giant 820
spikeidle 830
spike 840

special 10
treefire 20
arrow 25
textbox 30
innwalls 31
tree 32
outinn 33
doorleft 50
doorright 51
heart 52
goldheart 53
smallheart 54
bluebottle 55
redbottle 56
purplebottle 57
bridge 58
cabin 59
church 60
doorout1 61
doorout2 62
home 63
inacc 64
grass 65
garden 66
castle 67
doorcastle 68
gatecastle 69
explode 70
crazybottle 75
wallstone 80
snakeb 81
snakec 82
snakem 83
teleport 84
axe 85
fire 86
table 87
crack 89
grave 90
forest 91
beach 92
fence 93
spray 94
rock 95
building 96
rocks 97
castle-l 150
castle-la 151
castle-r 152
castle-ra 153
damage 154
fire2 155
fire3 156
fire4 157
hole 158
monument 159
atomc 161
circle 162
star2 163
magic1 164
shiny 165
spark 166
shock 167
whirl 168
star2-slow 169
star1 170
blast 171
barrel 173
redbarrel 174
chest1 175
chest2 176
chest3 177
coin 178
bush 179
status 180
nums 181
numr 182
numb 183
nump 184
numy 185
landmark 186
spurt 187
spurtl 188
spurtr 189
health-w 190
health-g 191
button-ordering 192
button-quit 193
button-start 194
button-continue 195
title 196
startme1 197
startme3 198
startme7 199
startme9 200
redmaidendie 225
brownmaidendie 245
bluemaidendie 255
redknightdie 275
blueknightdie 285
silverknightdie 295
goldknightdie 305
girldie 335
merchantdie 345
momdie 355
brownmomdie 365
bluemerchantdie 375
greenmerchantdie 385
purplemerchantdie 395
soldierdie 405
peasantdie 415
bomb 420
food 421
paper 422
menu 423
island 424
torch 425
boatman3 426
fire1 427
stairs 428
catapult 429
seed4 430
seed6 431
shadow 432
splash 433
fish1 434
fish2 435
die 436
item-m 437
item-w 438
fishx 439
flop1 440
flop2 441
level 442
box1 443
box3 444
box 445
tomb 446
tool 447
cup 448
save 449
health-br 450
health-r 451
crawl 452
arrow-l 456
arrow-r 457
sign 458
shelf 459
lab 460
chair 461
poster 462
grain 463
horngoblinattackswing 780
slayerdie 645
hammergoblindie 765
horngoblindie 785
goblindie 805
giantdie 825
'''.split ('\n')

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

def put (f, member, value, default = None):
	assert value != None
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
	l = ['//', '/*', '&&', '||', '==', '!=', '>=', '<=', '>', '<', '!', '+=', '-=', '/=', '*=', '=', '+', '-', '*', '/', ',', ';', '{', '}', '?', ':', '(', ')']
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
	sp_base_attack
	sp_base_death
	sp_base_idle
	sp_base_walk
	sp_brain
	sp_sound

	return name, args, before.'''
	if name == 'add_item' or name == 'add_magic':
		assert len (args) == 3
		assert args[1][0] == '"'
		return name, [args[0], str (dink.seq.find_seq (args[1][1:-1])), args[2]], ''
	elif name == 'create_sprite':
		assert len (args) == 5
		assert args[2][0] == '"'
		return name, [args[0], args[1], str (brains.index[args[2]]), str (dink.seq.find_seq (args[3][1:-1])), args[4]], ''
	elif name == 'get_rand_sprite_with_this_brain' or name == 'get_sprite_with_this_brain':
		assert len (args) == 2
		assert args[0][0] == '"'
		return name, [str (brains.index[args[0][1:-1]]), args[1]], ''
	elif name == 'playmidi':
		assert len (args) == 1
		assert args[0][0] == '"'
		return name, [str (dink.sound.find_music (args[0][1:-1]))], ''
	elif name == 'playsound':
		assert len (args) == 4 or len (args) == 5
		assert args[0][0] == '"'
		return name, [str (dink.sound.find_sound (args[0][1:-1]))] + args[1:], ''
	elif name == 'preload_seq':
		assert len (args) == 1
		assert args[0][0] == '"'
		return name, [str (dink.seq.find_seq (args[0][1:-1]))], ''
	elif name == 'sp_base_attack' or name == 'sp_base_death' or name == 'sp_base_idle' or name == 'sp_base_walk':
		assert len (args) == 2
		assert args[1][0] == '"'
		return name, [args[0], str (dink.seq.find_collection (args[1][1:-1]))], ''
	elif name == 'sp_brain':
		assert len (args) == 1 or len (args) == 2
		if len (args) == 2:
			v = brains.index (args[1][1:-1])
		else:
			v = -1
		return name, [args[0], str (v)], ''
	elif name == 'sp_sound':
		assert len (args) == 2
		assert args[1][0] == '"'
		return name, [args[0], str (dink.sound.find_sound (args[1][1:-1]))], ''
	else:
		return name, args, ''

def read_args (script):
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
						f, a, bf = mangle_function (name, args, parent)
						ret += ([f, a, b + bf],)
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
		if t.startswith ('//'):
			comment = script.split ('\n', 1)[0]
			ret += i + t + comment + '\n'
			script = script[len (comment) + 1:]
			continue
		if t.startswith ('/*'):
			comment = script.split ('*/', 1)[0]
			ret += i + t + comment + '*/\n'
			script = script[len (comment) + 2:]
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
					f, a, bf = mangle_function (name, args, dink)
					ret += b + bf + i + f + '(' + ', '.join (a) + ');\n'
		realatend = atend
		atend = ''
		t, script, isname = token (script)
		assert (t == ';')
	return ret

class Sprite:
	pass

class Room:
	def __init__ (self, parent, root = None):
		self.parent = parent
		self.sprite = {}
		if root == None:
			self.tiles = [[[0, 0, 0] for x in range (12)] for y in range (8)]
			return
		f = open (os.path.join (root, 'info' + os.extsep + 'txt'))
		self.tiles = []
		for ty in range (8):
			ln = f.readline ()
			self.tiles += ([[int (z) for z in y.split (',')] for y in ln.split ()],)
			assert len (self.tiles[-1]) == 12
		info = readlines (f)
		info, self.hard = get (info, 'hard', '')
		info, self.script = get (info, 'script', '')
		info, self.music = get (info, 'music', '')
		info, self.indoor = get (info, 'indoor', False)
		assert info == {}
		sdir = os.path.join (root, "sprite")
		codes = []
		for s in os.listdir (sdir):
			info = readlines (open (os.path.join (sdir, s)))
			r = re.match ('(.+?)(-\d*?)?(\..*)?$', s)
			base = r.group (1)
			self.sprite[s] = Sprite ()
			if r.group (2) != None:
				self.sprite[s].num = int (r.group (2))
				assert self.sprite[s].num not in codes
				codes += (self.sprite[s].num,)
			else:
				self.sprite[s].num = None
			info, self.sprite[s].x = get (info, 'x', int)
			info, self.sprite[s].y = get (info, 'y', int)
			info, self.sprite[s].seq = get (info, 'seq', base)
			info, self.sprite[s].frame = get (info, 'frame', 1)
			info, self.sprite[s].type = get (info, 'type', 1)	# 0 for background, 1 for person or sprite, 3 for invisible
			info, self.sprite[s].size = get (info, 'size', 100)
			info, self.sprite[s].active = get (info, 'active', True)
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
			assert info == {}
		code = 0
		for s in self.sprite:
			if self.sprite[s].num != None:
				continue
			while code in codes:
				code += 1
			self.sprite[s].num = code
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
			f = open (os.path.join (sd, '%s-%d' % (s, self.sprite[s].num)), 'w')
			put (f, 'x', self.sprite[s].x)
			put (f, 'y', self.sprite[s].y)
			put (f, 'seq', self.sprite[s].seq, base)
			put (f, 'frame', self.sprite[s].frame, 1)
			put (f, 'type', self.sprite[s].type, 1)
			put (f, 'size', self.sprite[s].size, 100)
			put (f, 'active', self.sprite[s].active, True)
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
		d = os.path.join (parent.root, 'world')
		self.room = {}
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
	def build (self, root):
		# Write dink.dat
		ddat = open (os.path.join (root, 'dink' + os.extsep + 'dat'), "wb")
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
					mdat.write (make_lsb (bmp * 128 + ty * 12 + tx, 4))
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
				mdat.write (make_lsb (0, 4))	# hit
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
	def find_hard (self, hard, x, y, bmp, tx, ty):
		if hard != '':
			assert hard in self.hard
			return self.map[hard][y][x]
		if bmp in self.hard:
			return self.map[bmp][ty][tx]
		bmp = int (bmp)
		return 0	# TODO
	def save (self):
		d = os.path.join (self.parent.root, 'tile')
		os.mkdir (d)
		# TODO
	def build (self, root):
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
	'''\
A sequence is either an animation (optionally single-frame, so not animated).  It has the following members:
	frames		- list of frames, for local images. These frames are created from a gif file.
	filename	- name of the file to write to dink.ini, including dos-style directory separators (\\)
	num		- total number of frames in the sequence.
	repeat		- whether this sequence should be marked as repeating.
	special		- which frame hits during an attack.
	now		- boolean value. When true, use load_sequence_now to load it.
	code		- Sequence code. If 0, auto-generate.
	preload		- Name of file to preload into this sequence number before the real one.
	desc		- Information about the frames. List of size num, each element is a 7-value list: x, y, left, top, right, bottom, delay.
	type		- normal, notanim, black, or leftalign.
'''
	def __init__ (self):
		self.internal = False
class Oneframe:
	pass
class Collection:
	pass
class Dinkframe:
	'''\
This class contains information about one frame from dink.ini. Members:
	target: [seq,frame] for copied frame
	info: box for non-copied frame
	delay: int
'''
	def __init__ (self):
		self.target = None
		self.info = None
		self.delay = None
	def mkbox (self):
		if self.target:
			return self.target + [self.delay]
		elif self.info:
			return self.info + [self.delay]
		else:
			return [None] * 6 + [self.delay]

class Dinkseq:
	'''\
This class holds a sequence as defined in dink.ini. Its members are:
	file: filename
	special: int special frame
	now = bool load_now
	type = str
	repeat = bool
	frames = list of Dinkframe
	defaults = Dinkframe
	num = int max frame (only certainly valid if used)
	preload = None or str (filename)
'''
	def __init__ (self):
		self.file = None
		self.special = 1
		self.now = False
		self.type = 'normal'
		self.repeat = False
		self.preload = ''
		self.num = 1
		self.frames = {}
		self.defaults = Dinkframe ()
	def use (self, s):
		if s in self.frames:
			return
		self.frames[s] = Dinkframe ()
		if s > self.num:
			self.num = s
	def mkseq (self, code):
		ret = Oneseq ()
		ret.internal = True
		ret.code = code
		ret.frames = []
		ret.filename = self.file
		ret.num = self.num
		ret.repeat = self.repeat
		ret.special = self.special
		ret.now = self.now
		ret.type = self.type
		ret.preload = self.preload
		ret.box = []
		for f in range (self.num):
			if f + 1 in self.frames:
				ret.box += (self.frames[f + 1].mkbox (),)
			else:
				ret.box += (Dinkframe ().mkbox (),)
		ret.box += (self.defaults.mkbox (),)
		return ret

class Seq:
	def use (self, s):
		if s in self.seqs:
			return
		self.seqs[s] = Dinkseq ()
	def prepare (self, info, base, box):
		info, self.seq[base].num = get (info, 'frames', self.seq[base].num)
		info, self.seq[base].repeat = get (info, 'repeat', self.seq[base].repeat)
		info, self.seq[base].special = get (info, 'special', self.seq[base].special)
		info, self.seq[base].now = get (info, 'load-now', False)
		if self.current_collection == None:
			info, self.seq[base].code = get (info, 'code', self.seq[base].code)
			assert self.seq[base].code not in self.codes
			if self.seq[base].code >= 0:
				self.codes += (self.seq[base].code,)
		info, self.seq[base].preload = get (info, 'preload', self.seq[base].preload)
		info, defbox = get (info, 'box', '')
		if defbox == '':
			defbox = [None] * 6
		else:
			defbox = defbox.split ()
		assert len (defbox) == 6
		info, delay = get (info, 'delay', 0)
		defbox += [delay]
		self.seq[base].desc = []
		for f in range (self.seq[base].num):
			self.seq[base].desc += (Oneframe (),)
			if len (box[f]) == 3:
				# These are internal frames with a target. Num is not valid, so just use the target without checking.
				info, self.seq[base].desc[-1].seq = get (info, 'seq-%d' % (f + 1), box[f][0])
				info, self.seq[base].desc[-1].frame = get (info, 'frame-%d' % (f + 1), box[f][1])
			elif not self.seq[base].internal and f >= len (self.seq[base].frames):
				# these are generated frames. They need a target.
				info, self.seq[base].desc[-1].seq = get (info, 'seq-%d' % (f + 1))
				info, self.seq[base].desc[-1].frame = get (info, 'frame-%d' % (f + 1), 1)
			info, curbox = get (info, 'box-%d' % (f + 1), '')
			if curbox == '':
				curbox = box[f][:6]
				if len (curbox) != 6 or curbox[0] == None:
					curbox = defbox[:6]
					if curbox[0] == None:
						curbox = box[-1][:6]
			else:
				curbox = [int (x) for x in curbox.split ()]
			assert len (curbox) == 6
			if curbox[0] != None:
				self.seq[base].desc[-1].x = curbox[0]
				self.seq[base].desc[-1].y = curbox[1]
				self.seq[base].desc[-1].left = curbox[2]
				self.seq[base].desc[-1].top = curbox[3]
				self.seq[base].desc[-1].right = curbox[4]
				self.seq[base].desc[-1].bottom = curbox[5]
			info, dl = get (info, 'delay-%d' % (f + 1), 0)
			if not dl:
				dl = box[f][-1]
				if not dl:
					dl = defbox[-1]
					if not dl:
						dl = box[-1][-1]
						if not dl:
							dl = None
			self.seq[base].desc[-1].delay = dl
		info, self.seq[base].type = get (info, 'type', self.seq[base].type)
		assert self.seq[base].type in ('normal', 'black', 'leftalign', 'notanim')
		assert info == {}
		if self.current_collection != None:
			assert base == None
			assert self.collection[self.current_collection].seq[self.direction] == None
			self.collection[self.current_collection].seq[self.direction] = self.seq[base]
			del self.seq[base]
		return info
	def __init__ (self, parent):
		"""Load all sequence and collection declarations from dink.ini, seq-names.txt (both internal) and seq/info.txt"""
		# General setup
		self.parent = parent
		self.seq = {}
		self.codes = []
		self.seq = {}
		self.collection = {}
		self.seqs = {}
		d = os.path.join (parent.root, "seq")
		# Read dink.ini.
		for l in [y.lower ().split () for y in dink_ini]:
			if l == [] or l[0].startswith ('//') or l[0].startswith (';') or l[0] == 'starting_dink_x' or l[0] == 'starting_dink_y' or l[0] == 'starting_dink_map':
				pass
			elif l[0] == 'load_sequence' or l[0] == 'load_sequence_now':
				s = int (l[2])
				self.use (s)
				if self.seqs[s].file:
					assert not self.seqs[s].preload
					assert self.seqs[s].file
					preload = self.seqs[s].file
					self.seqs[s] = Dinkseq ()
					self.seqs[s].preload = preload
				self.seqs[s].file = l[1]
				self.seqs[s].now = l[0] == 'load_sequence_now'
				if len (l) == 3:
					pass
				elif len (l) == 4:
					# Ignore bug in original source.
					if l[3] == 'notanin':
						l[3] = 'notanim'
					if l[3] == 'black' or l[3] == 'notanim' or l[3] == 'leftalign':
						self.seqs[s].type = l[3]
					else:
						self.seqs[s].defaults.delay = int (l[3])
				elif len (l) == 5:
					self.seqs[s].defaults.delay = int (l[3])
					self.seqs[s].type = l[4]
				elif len (l) == 9:
					self.seqs[s].defaults.info = [int (x) for x in l[3:]]
				elif len (l) == 10:
					self.seqs[s].defaults.delay = int (l[3])
					self.seqs[s].defaults.info = [int (x) for x in l[4:]]
				else:
					raise AssertionError ('invalid line for load_sequence')
			elif l[0] == 'set_sprite_info':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				self.seqs[s].use (f)
				self.seqs[s].frames[f].info =  [int (x) for x in l[3:]]
			elif l[0] == 'set_frame_delay':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				self.seqs[s].use (f)
				self.seqs[s].frames[f].delay =  int (l[3])
			elif l[0] == 'set_frame_frame':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				if len (l) == 5:
					self.seqs[s].use (f)
					self.seqs[s].frames[f].target =  [int (l[3]), int (l[4])]
				else:
					self.seqs[s].repeat = True
			elif l[0] == 'set_frame_special':
				s = int (l[1])
				f = int (l[2])
				self.use (s)
				self.seqs[s].special = int (l[3])
			else:
				print l
				raise AssertionError ('invalid line in dink.ini')
		# Link names to sequences from dink.ini.
		n = 0
		# Read collections.
		while n < len (seq_names):
			l = seq_names[n].strip ()
			n += 1
			if l.startswith ('#'):
				continue
			if not l:
				break
			nm, c = l.split ()
			c = int (c)
			assert nm not in self.collection
			self.collection[nm] = Collection ()
			self.collection[nm].code = c
			self.collection[nm].seq = [None] * 10
			for i in range (1, 10):
				if i == 5:
					continue
				if c + i in self.seqs:
					self.collection[nm].seq[i] = self.seqs[c + i].mkseq (c + i)
					del self.seqs[c + i]
			assert self.collection[nm].seq != [None] * 10
		# Read sequences.
		while n < len (seq_names):
			l = seq_names[n].strip ()
			n += 1
			if not l:
				break
			if l[0] == '#':
				continue
			nm, c = l.split ()
			c = int (c)
			assert nm not in self.seq
			assert c in self.seqs
			self.seq[nm] = self.seqs[c].mkseq (c)
			del self.seqs[c]
		assert self.seqs == {}
		del self.seqs
		# Read info specific to this dmod.
		infofile = open (os.path.join (d, 'info' + os.extsep + 'txt'))
		self.current_collection = None
		while True:
			info = readlines (infofile)
			if info == {}:
				break
			if 'collection' in info:
				# The next blocks with a direction are a collection.
				info, self.current_collection = get (info, "collection")
				assert info == {}
				continue
			elif 'append' in info:
				# This block is about a sequence which was declared in dink.ini.
				self.current_collection = None
				info, base = get (info, 'append')
				assert base in self.seq
				assert self.seq[base].internal
				box = self.seq[base].box
				del self.seq[base].box
			else:
				if 'name' in info:
					# This block defines a new sequence.
					self.current_collection = None
					info, base = get (info, 'name')
					assert base not in self.seq
					self.seq[base] = Oneseq ()
					is_new = True
				else:
					# This block is part of a collection.
					assert self.current_collection != None
					base = None
					self.seq[None] = Oneseq ()
					info, self.seq[None].direction = get (info, 'direction', int)
					assert self.seq[None].direction >= 1 and self.seq[None].direction <= 9 and self.seq[None].direction != 5
					info, is_new = get (info, 'new', True)
				if is_new:
					self.seq[base].code = -1
					self.seq[base].frames = []
					self.seq[base].repeat = False
					gif = os.path.join (d, base + os.extsep + 'gif')
					assert os.path.exists (gif)
					f = Image.open (gif)
					while True:
						self.seq[base].frames += ((f.info['duration'], convert_image (f)),)
						try:
							f.seek (len (self.seq[base].frames))
						except EOFError:
							break
					w = self.seq[base].frames[0][1].size[0]
					h = self.seq[base].frames[0][1].size[1]
					box = [[None] * 7] * len (self.seq[base].frames) + [w / 2, h * 8 / 10, -w * 4 / 10, -h / 10, w * 4 / 10, h / 10, self.seq[base].frames[0][0]]
					info, self.seq[base].filename = 'graphics\\%s-' % base
					self.seq[base].type = 'normal'
					self.seq[base].special = 1
					self.seq[base].preload = ''
					self.seq[base].num = len (self.seq[base].frames)
				else:
					self.seq[base] = self.collections[self.current_collection].seq[self.seq[base].direction]
					del self.collections[self.current_collection].seq[self.seq[base].direction]
					box = self.seq[base].box
					del self.seq[base].box
			# Now the sequence is prepared for use. The box is created from info if present, from box[f] otherwise, or from default_box otherwise.
			info = self.prepare (info, base, box)
		# Also prepare all sequences which have not been changed by info.txt.
		for base in self.seq:
			if 'box' in dir (self.seq[base]):
				box = self.seq[base].box
				del self.seq[base].box
				self.prepare ({}, base, box)
		# Reserve all codes which fit in a collection.
		for c in self.collection:
			for s in range (len (self.collection[c].seq)):
				if not self.collection[c].seq[s]:
					continue
				if 'box' in dir (self.collection[c].seq[s]):
					self.seq[None] = self.collection[c].seq[s]
					box = self.seq[None].box
					del self.seq[None].box
					self.prepare ({}, None, box)
					self.collection[c].seq[s] = self.seq[None]
					del self.seq[None]
			for s in [1, 2, 3, 4, 6, 7, 8, 9]:
				if self.collection[c].code + s not in self.codes:
					self.codes += [self.collection[c].code + s]
		nextseq = 1
		for s in self.seq:
			if self.seq[s].code == -1:
				self.seq[s].code = nextseq
				nextseq += 1
				while nextseq in self.codes:
					nextseq += 1
	def find_seq (self, name):
		if not name:
			return 0
		if type (name) == int:
			return name
		return self.seq[name].code
	def find_collection (self, name):
		return self.collection[name].code
	def build_seq (self, ini, seq):
		if seq.preload:
			ini.write ('// Preload\n')
			ini.write ('load_sequence_now %s %d\n' % (seq.preload, seq.code))
		if len (seq.desc) > 0:
			delay = seq.desc[0].delay
		else:
			delay = None
		if seq.now:
			now = '_now'
		else:
			now = ''
		if seq.type == 'normal':
			if len (seq.desc) == 0 or 'x' not in dir (seq.desc[0]):
				if delay != None:
					ini.write ('load_sequence%s %s %d %d\n' % (now, seq.filename, seq.code, delay))
				else:
					ini.write ('load_sequence%s %s %d\n' % (now, seq.filename, seq.code))
			else:
				if delay != None:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d %d\n' % (now, seq.filename, seq.code, delay, seq.desc[0].x, seq.desc[0].y, seq.desc[0].left, seq.desc[0].top, seq.desc[0].right, seq.desc[0].bottom))
				else:
					ini.write ('load_sequence%s %s %d %d %d %d %d %d %d\n' % (now, seq.filename, seq.code, seq.desc[0].x, seq.desc[0].y, seq.desc[0].left, seq.desc[0].top, seq.desc[0].right, seq.desc[0].bottom))
		else:
			ini.write ('load_sequence%s %s %d %s\n' % (now, seq.filename, seq.code, seq.type.upper ()))
		for n, f in zip (range (len (seq.frames)), seq.frames):
			if f != None:
				f[1].save (os.path.join (d, (g + '-%02d' + os.extsep + 'bmp') % (n + 1)))
		for f in range (len (seq.desc)):
			if 'seq' in dir (seq.desc[f]):
				ini.write ('set_frame_frame %d %d %d %d\n' % (seq.code, f + 1, self.find_seq (seq.desc[f].seq), seq.desc[f].frame))
			if 'x' in dir (seq.desc[f]):
				if 'x' not in dir (seq.desc[0]) or (((seq.type != 'normal' or seq.desc[0].x, seq.desc[0].y, seq.desc[0].left, seq.desc[0].top, seq.desc[0].right, seq.desc[0].bottom) != (seq.desc[f].x, seq.desc[f].y, seq.desc[f].left, seq.desc[f].top, seq.desc[f].right, seq.desc[f].bottom)) and seq.desc[f].right != None and seq.desc[f].right - seq.desc[f].left != 0):
					ini.write ('set_sprite_info %d %d %d %d %d %d %d %d\n' % (seq.code, f + 1, seq.desc[f].x, seq.desc[f].y, seq.desc[f].left, seq.desc[f].top, seq.desc[f].right, seq.desc[f].bottom))
			if 'seq' in dir (seq.desc[f]) or (f > 0 and seq.desc[f].delay != seq.desc[0].delay):
				ini.write ('set_frame_delay %d %d %d\n' % (seq.code, f + 1, int (seq.desc[f].delay)))
			if f != 0 and seq.special == f + 1:
				ini.write ('set_frame_special %d %d\n' % (seq.code, f + 1))
		if seq.repeat:
			ini.write ('set_frame_frame %d %d -1\n' % (seq.code, len (seq.desc) + 1))
	def save (self):
		d = os.path.join (self.parent.root, 'seq')
		os.mkdir (d)
		f = open (os.path.join (d, 'info' + os.extsep + 'txt'), 'w')
		# TODO
	def build (self, root):
		# Write graphics/*
		# Write dink.ini
		d = os.path.join (root, 'graphics')
		if not os.path.exists (d):
			os.mkdir (d)
		ini = open (os.path.join (root, 'dink.ini'), 'w')
		for c in self.collection:
			for s in self.collection[c].seq:
				if s:
					self.build_seq (ini, s)
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
		d = os.path.join (parent.root, "sound")
		for s in os.listdir (d):
			data = open (os.path.join (d, s)).read ()
			if not s.endswith (ext):
				continue
			r = re.match ('(\d+)-', s)
			if not r:
				other += ((s[:-len (ext)], data),)
			else:
				code = int (r.group (1))
				self.sound[s[len (r.group (0)):]] = (code, data)
				assert code not in codes
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
		assert name in self.music
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
		info, p = get (info, 'pointer', 'special 8')
		p = p.split ()
		self.title_pointer_seq, self.title_pointer_frame = p[0], int (p[1])
		info, self.title_run = get (info, 'run', '')
		info, n = get (info, 'sprites', 0)
		self.title_sprite = []
		for s in range (n):
			info, spr = get (info, 'sprite-%d' % (s + 1))
			spr = spr.split ()
			if len (spr) == 4:
				spr += ('repeat',)
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
		assert info == {}
	def save (self):
		d = os.path.join (self.parent.root, "script")
		os.mkdir (d)
		for s in self.data:
			open (os.path.join (d, s + os.extsep + 'c'), 'w').write (self.data[s])
		f = open (os.path.join (self.parent.root, "title" + os.extsep + "txt"), 'w')
		put (f, 'music', self.title_music, '')
		put (f, 'color', self.title_color, 0)
		put (f, 'background', self.title_bg, '')
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
	def build (self, root):
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
			s.write ('&crap = create_sprite (%d, %d, %d, %d, %d);\n' % (t[2], t[3], brains.index (t[4]), self.parent.seq.find_seq (t[0]), t[1]))
			if t[5] != '':
				s.write ('sp_script(&crap, "%s");\n' % t[5])
				s.write ('sp_touch_damage (&crap, -1);\n')
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
			s.write ('\tmake_global_int ("&%s", %d);\n' % (v, the_globals[v]))
		for t in range (max_tmp):
			s.write ('\tmake_global_int ("&tmp%s", %d);\n' % (t, 0))
		s.write ('\tkill_this_task ();\n}\n')

class Dink:
	def __init__ (self, root):
		self.root = os.path.normpath (root)
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
		else:
			self.preview = None
		p = os.path.join (im, 'splash' + os.extsep + 'png')
		if os.path.exists (p):
			self.splash = convert_image (Image.open (p))
		else:
			self.splash = None
	def save (self, root = None):
		if root != None:
			self.root = os.path.normpath (root)
		p = self.root
		if os.path.exists (p):
			i = 0
			while os.path.exists (p):
				p = self.root + os.extsep + str (i)
				i += 1
			os.rename (self.root, p)
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
		# Write story/*
		self.script.build (root)
		# Write the rest
		if self.preview != None:
			self.preview.save (os.path.join (root, 'preview' + os.extsep + 'bmp'))
		if self.splash != None:
			self.splash.save (os.path.join (os.path.join (root, 'tiles'), 'splash' + os.extsep + 'bmp'))
		open (os.path.join (root, 'dmod' + os.extsep + 'diz'), 'w').write (self.info)

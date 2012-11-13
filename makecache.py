#!/usr/bin/env python
# vim: set fileencoding=utf-8 foldmethod=marker :

# makecache - set up cache for pydink programs.
# Copyright 2011 Bas Wijnen {{{
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

# {{{ Remaining imports
import argparse
import sys
import os
import glib
import Image
import pickle
import readini
# }}}

# Prepare things. {{{
p = os.path.join (glib.get_user_config_dir (), 'pydink')
if not os.path.exists (p):
	os.makedirs (p)
configfilename = os.path.join (p, 'config.txt')

savedir = os.path.join (glib.get_user_cache_dir (), 'pydink')
if not os.path.isdir (savedir):
	os.makedirs (savedir)
# }}}

def write_config (data): # {{{
	open (configfilename, 'w').write (''.join (['%s\t%s\n' % (x, data[x]) for x in data]))
# }}}

# Argument parsing. {{{
a = argparse.ArgumentParser ()
a.add_argument ('--dinkdir', default = None, help = 'location of dink data', type = str)
a.add_argument ('--dmoddir', default = None, help = 'location of built DMods', type = str)
a.add_argument ('--editdir', default = None, help = 'location of edited DMods', type = str)
a.add_argument ('--freedink', default = None, help = 'location of freedink executable', type = str)
args = a.parse_args ()
# }}}

# Setup gui. {{{
if args.dinkdir is None or args.dmoddir is None or args.editdir is None or args.freedink is None:
	import gui
	with_gui = True
	the_gui = gui.Gui ()
	the_gui.dinkdir = '/usr/share/games/dink/dink' if args.dinkdir is None else args.dinkdir
	the_gui.dmoddir = os.path.join (os.path.expanduser ('~'), 'dmods') if args.dmoddir is None else args.dmoddir
	the_gui.editdir = os.path.join (os.path.expanduser ('~'), 'pydink') if args.editdir is None else args.editdir
	the_gui.freedink = '/usr/games/freedink' if args.freedink is None else args.freedink
	the_gui.run = lambda: the_gui (False, True)
	the_gui.done = lambda: the_gui (False)
else:
	with_gui = False
	dinkdir = args.dinkdir
	dmoddir = args.dmoddir
	editdir = args.editdir
	freedink = args.freedink
# }}}

while True:
	# {{{ Run gui stuff.
	if with_gui:
		if the_gui () is None:
			# The window was closed.
			sys.exit (0)
		dinkdir = the_gui.dinkdir
		dmoddir = the_gui.dmoddir
		editdir = the_gui.editdir
		freedink = the_gui.freedink
	# }}}

	# {{{ Create config file.
	f = open (configfilename, 'w')
	f.write ('''\
dinkdir		%s
dmoddir		%s
editdir		%s
dinkprog	%s
''' % (dinkdir, dmoddir, editdir, freedink))
	f.close ()
	# }}}
	readini.setup (dinkdir)

	# Create data to be cached. {{{
	err = ''
	try:
		harddata, harddefaults, tilefiles = readini.read_hard ()
		collections, sequences, codes = readini.read_ini ()
		musics, sounds = readini.read_sound ()
	except:
		err += 'Error creating cache: %s\n' % str (sys.exc_value)
		if with_gui:
			the_gui.error = err
			continue
		else:
			sys.stderr.write (err)
			sys.exit (1)
	err += readini.err
	# }}}

	# Error reporting. {{{
	if with_gui:
		the_gui.error = err
		the_gui (1)
	else:
		sys.stderr.write (err)
	# }}}

	# {{{ Create cache of hardness tiles.
	for n in range (41):
		tilef = Image.open (tilefiles[n][0]).convert ('RGBA')
		image = Image.new ('RGBA', (tilef.size[0] / 50 * 50, tilef.size[1] / 50 * 50))
		image.paste ((0, 0, 0, 0))
		for y in range (8):
			for x in range (12):
				if tilef.size[0] < (x + 1) * 50 or tilef.size[1] < (y + 1) * 50:
					continue
				if harddefaults[n][y * 12 + x] >= 800:
					sys.stderr.write ('Warning: invalid hardness in default hard.dat %d:%d,%d (%d,%d) = %d\n' % (n, x, y, tilef.size[0], tilef.size[1], harddefaults[n][y * 12 + x]))
					continue
				i = harddata[harddefaults[n][y * 12 + x]]
				image.paste (i, (50 * x, 50 * y), i)
		image.save (os.path.join (savedir, 'hard-%02d' % (n + 1) + os.extsep + 'png'))
	# }}}

	pickle.dump ((tilefiles, collections, sequences, codes, musics, sounds), open (os.path.join (savedir, 'data'), 'wb'))

	if not with_gui:
		break

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

# Imports
import sys
import os
import Image
import pickle
import readini
import fhs

# Config.
config = fhs.init({'dinkdir': '/usr/share/games/dink/dink', 'dmoddir': os.path.join(fhs.HOME, 'dmods'), 'editdir': None, 'freedink': '/usr/bin/freedink'}, packagename = 'pydink')
dinkdir = os.path.realpath(config['dinkdir'])
dmoddir = os.path.realpath(config['dmoddir'])
editdir = os.path.realpath(config['editdir'])
freedink = os.path.realpath(config['freedink'])

fhs.save_config(config)
readini.setup(dinkdir)
savedir = fhs.write_cache(dir = True)

# Create data to be cached.
err = ''
try:
	harddata, harddefaults, tilefiles = readini.read_hard()
	tilefiles = [t[0] for t in tilefiles]
	collections, sequences, codes = readini.read_ini()
	musics, sounds = readini.read_sound()
except:
	err += 'Error creating cache: %s\n' % str(sys.exc_value)
	sys.stderr.write(err)
	sys.exit(1)

sys.stderr.write(readini.err)

# Create cache of hardness tiles.
for n in range(41):
	tilef = Image.open(tilefiles[n][0]).convert('RGBA')
	image = Image.new('RGBA', (tilef.size[0] / 50 * 50, tilef.size[1] / 50 * 50))
	image.paste((0, 0, 0, 0))
	for y in range(8):
		for x in range(12):
			if tilef.size[0] < (x + 1) * 50 or tilef.size[1] < (y + 1) * 50:
				continue
			if harddefaults[n][y * 12 + x] >= 800:
				sys.stderr.write('Warning: invalid hardness in default hard.dat %d:%d,%d(%d,%d) = %d\n' % (n, x, y, tilef.size[0], tilef.size[1], harddefaults[n][y * 12 + x]))
				continue
			i = harddata[harddefaults[n][y * 12 + x]]
			image.paste(i, (50 * x, 50 * y), i)
	image.save(os.path.join(savedir, 'hard-%02d' % (n + 1) + os.extsep + 'png'))

pickle.dump((tilefiles, collections, sequences, codes, musics, sounds), open(os.path.join(savedir, 'data'), 'wb'))

#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

# editconfig.py - graphical configuration setup for pydink.
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

import sys
import os
import glib
import gui

p = os.path.join (glib.get_user_config_dir (), 'pydink')
if not os.path.exists (p):
	os.makedirs (p)
name = os.path.join (p, 'dinkconfig.py')
if not os.path.exists (name):
	f = open (name, 'w')
	f.write ('''lowmem = False
nobackingstore = False
dinkdir = '/usr/share/games/dink'
dinkprog = '/usr/games/freedink'
class Sequence:
	pass
class Frame:
	pass
''')
	f.close ()
sys.path += (p,)
import dinkconfig

abort = True
def done ():
	global abort
	abort = False
	gui.quit ()

the_gui = gui.gui ()
the_gui.done = done
the_gui.set_lowmem = dinkconfig.lowmem
the_gui.set_nobackingstore = dinkconfig.nobackingstore
the_gui.set_dinkdir = dinkconfig.dinkdir
the_gui.set_dinkprog = dinkconfig.dinkprog
the_gui ()

if abort:
	sys.exit (1)

f = open (name)
f.write ('lowmem = ' + repr (the_gui.lowmem) + '\n')
f.write ('nobackingstore = ' + repr (the_gui.nobackingstore) + '\n')
f.write ('dinkdir = ' + repr (the_gui.dinkdir if the_gui.dinkdir != None else dinkconfig.dinkdir) + '\n')
f.write ('dinkprog = ' + repr (the_gui.dinkprog if the_gui.dinkprog != None else dinkconfig.dinkprog) + '\n')
f.write ('class Sequence:' + '\n')
f.write ('\tpass' + '\n')
f.write ('class Frame:' + '\n')
f.write ('\tpass' + '\n')

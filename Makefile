# Makefile - pydink build rules
# Copyright 2011-2014 Bas Wijnen <wijnen@debian.org>
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

all: all-dep
	./pde.py

all-dep: pde.gui makecache.gui

%.dmod: pde.py pde.gui
	./pde.py $(subst .dmod,,$@)

%.world: pdw.py pdw.gui
	./pdw.py $(subst .dmod,,$@)

cache: makecache.py makecache.gui
	./makecache.py

%: %.in
	xmlgen <$< >$@

clean:
	rm -f *.pyc *.pyo

release: clean all-dep
	rm -f release.zip
	zip -r release.zip $(wildcard *[^p])

.PHONY: release all all-dep clean

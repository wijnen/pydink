test: pde pde.gui
	./pde

%: %.in
	../xmlgen/xmlgen <$< >$@

test: pde pde.gui
	./pde test

%: %.in
	../xmlgen/xmlgen <$< >$@

.PHONY: test

karel.dmod:

%.dmod: pde pde.gui
	./pde $(subst .dmod,,$@)

%: %.in
	../xmlgen/xmlgen <$< >$@

.PHONY: current

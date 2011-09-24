karel: pde pde.gui
	./pde $@

%: %.in
	../xmlgen/xmlgen <$< >$@

.PHONY: current

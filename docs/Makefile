SPHINXOPTS          =
SPHINXBUILD         = poetry run sphinx-build
SPHINXAUTOBUILD     ?= poetry run sphinx-autobuild
SPHINXAUTOBUILDPORT = 9997
SOURCEDIR           = source
BUILDDIR            = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: clean docs open help Makefile

clean:
	@rm -rf build/html/*
	@echo "Removed HTML files from previous build"
	@rm -rf source/apidocs/*
	@echo "Removed apidocs from previous build"

docs: clean html

preview:
	@$(SPHINXAUTOBUILD) --port $(SPHINXAUTOBUILDPORT) "$(SOURCEDIR)" "$(BUILDDIR)" $(O)

open:
	@open build/html/index.html

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O) -j auto --show-traceback

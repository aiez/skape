# vim: ts=2 sw=2 sts=2 et :
# knobs only; shared targets live in $(KONFIG)/Makefile
KONFIG ?= ../konfig
DOOT   ?= $(abspath $(KONFIG)/..)
APP    := skape
MAIN   := skape.py
EXT    := py
LANG   := python
SRC    := *.py
LINT   := ruff check skape.py
TOOLS  := python3:run ruff:lint
PKG    := python3 gawk ruff neovim tmux

$(KONFIG)/Makefile:
	@test -f $@ || { echo "missing konfig: git clone https://github.com/aiez/konfig $(KONFIG)"; exit 1; }
include $(KONFIG)/Makefile

test: ## smoke-test (needs the optimiz sibling gist)
	@python3 -B test_skape.py && echo "ok skape"

push2pypi: ## build + upload to PyPI (needs ~/.pypirc account token)
	@python3 -m build && python3 -m twine upload dist/*
	@rm -rf dist build *.egg-info

P ?= 8                      # xargs workers

~/tmp/konfig/skateper :
	@mkdir -p $(@D)
	@ls $(DOOT)/optimiz/*.csv | sort -R | xargs -P$(P) -I{} \
	  python3 -B skape.py --file {} --data | tee $@
	@gawk -v c=3 -f per.awk $@


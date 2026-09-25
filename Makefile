PYTHON ?= python3

.PHONY: setup voices voice clean

setup:
	bash scripts/bootstrap.sh

voices:
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset all

voice:
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset default

clean:
	rm -rf outputs

PYTHON ?= python3

.PHONY: setup voices voice reference shunri install-cli uninstall-cli clean

setup:
	bash scripts/bootstrap.sh

voices:
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset all

voice:
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset default

reference:
	@test -n "$(FILE)" || (echo '使い方: make reference FILE="/path/to/sample.mp4"' && exit 1)
	$(PYTHON) scripts/import_reference.py "$(FILE)"

shunri:
	@test -f references/shunri.wav || (echo 'references/shunri.wav がありません。先に make reference FILE="..." を実行してください。' && exit 1)
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset clone --reference references/shunri.wav

install-cli:
	bash scripts/install_cli.sh

uninstall-cli:
	rm -f "$(HOME)/.local/bin/shunri"

clean:
	rm -rf outputs

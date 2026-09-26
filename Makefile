PYTHON ?= python3

.PHONY: setup voices voice reference shunri install-cli uninstall-cli worker-once install-reel-worker uninstall-reel-worker reel-renderer-setup motion-bank reel-poc clean

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

worker-once:
	$(PYTHON) scripts/process_reel_jobs.py

install-reel-worker:
	bash scripts/install_reel_worker.sh

uninstall-reel-worker:
	bash scripts/uninstall_reel_worker.sh

reel-renderer-setup:
	docker build -t shunri-reel-renderer:local docker/reel-renderer

motion-bank:
	$(PYTHON) scripts/prepare_motion_bank.py

reel-poc:
	@test -n "$(FILE)" || (echo '使い方: make reel-poc FILE="/path/to/script.txt"' && exit 1)
	$(PYTHON) scripts/reel_poc.py --file "$(FILE)"

clean:
	rm -rf outputs

PYTHON ?= python3

.PHONY: setup voices voice reference shunri install-cli uninstall-cli worker-once install-reel-worker uninstall-reel-worker reel-renderer-setup motion-bank import-motion-bank reel-poc reel-poc-lipsync clean

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

import-motion-bank:
	@test -n "$(DIR)" || (echo '使い方: make import-motion-bank DIR="/path/to/clips"' && exit 1)
	$(PYTHON) scripts/import_motion_bank.py "$(DIR)"

reel-poc:
	@test -n "$(FILE)" || (echo '使い方: make reel-poc FILE="/path/to/script.txt"' && exit 1)
	$(PYTHON) scripts/reel_poc.py --file "$(FILE)"

reel-poc-lipsync:
	@test -n "$(FILE)" || (echo '使い方: make reel-poc-lipsync FILE="/path/to/script.txt"' && exit 1)
	@test -n "$SHUNRI_LIPSYNC_COMMAND" || (echo 'SHUNRI_LIPSYNC_COMMAND が未設定です' && exit 1)
	$(PYTHON) scripts/reel_poc.py --file "$(FILE)" --lipsync-backend external

clean:
	rm -rf outputs

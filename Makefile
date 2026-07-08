.PHONY: install uninstall run clean

install:
	bash install.sh

uninstall:
	rm -f ~/.local/share/applications/xorriso-gui.desktop
	rm -f ~/.local/share/icons/xorriso-gui.svg
	@echo "Uninstalled."

run:
	python3 main.py

clean:
	rm -rf build_appimage/ dist/ build/ __pycache__/ xorriso_gui/__pycache__/ xorriso_gui/*/__pycache__/ *.spec

appimage:
	bash build_appimage.sh
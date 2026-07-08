.PHONY: install uninstall run clean deps appimage

deps:
	python3 -m pip install -r requirements.txt

install: deps
	mkdir -p ~/.local/share/applications ~/.local/share/icons
	sed "s|__PROJECT_DIR__|$(CURDIR)|g" xorriso-gui.desktop.in > ~/.local/share/applications/xorriso-gui.desktop
	cp xorriso_gui/assets/icon.svg ~/.local/share/icons/xorriso-gui.svg
	@echo "Installed. You can now launch xorriso-gui from the application menu."

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
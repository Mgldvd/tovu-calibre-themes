"""Invoked by verify.py in a separate Calibre process and isolated profile."""
import json
import importlib.util
import os
import sys
from pathlib import Path

from calibre.constants import config_dir
from calibre.gui2 import icon_resource_manager
from qt.core import QIcon, QImage, QApplication

ROOT = Path(__file__).resolve().parents[1]
theme_id = os.environ.get('TOVU_TEST_THEME', 'line')
spec = importlib.util.spec_from_file_location('tovu_installer', ROOT/'installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
theme_root = installer.THEMES[theme_id]['root']
title = installer.THEMES[theme_id]['title']
app = QApplication([])
icon_resource_manager.initialize()
QIcon.setThemeName('calibre-user-any-light')
if icon_resource_manager.user_theme_title != title:
    raise AssertionError((title, icon_resource_manager.user_theme_title))
inventory = json.loads((ROOT/'tools/inventory.json').read_text())
for mode in ('light','dark'):
    # Calibre 9.18's C++ icon engine has its own palette selection. Follow the
    # same set_theme path as the application, instead of setting only Qt's name.
    app.is_dark_theme = mode == 'dark'
    icon_resource_manager.set_theme()
    QIcon.setThemeName('calibre-user-any-'+mode)
    for name in inventory:
        icon = QIcon.ic(name)
        if icon.isNull():
            raise AssertionError((mode,name,'missing icon'))
        actual = icon.pixmap(128,128).toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        source = theme_root/'theme'/(str(Path(name).with_suffix(''))+f'-for-{mode}-theme.png')
        expected = QImage(str(source)).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        if actual != expected:
            raise AssertionError((mode,name,'unexpected pixels / fallback'))
print(f'{title}: {len(inventory)} native icons × 2 modes match source pixels. Profile: {config_dir}')

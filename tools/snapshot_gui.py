"""Save README screenshots of the real Qt installer in light and dark mode.

QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 calibre-debug -e tovu-calibre-themes/tools/snapshot_gui.py

Uses a throwaway profile, so your Calibre configuration is never read or changed.
"""
import importlib.util
import os
import tempfile
from pathlib import Path

from qt.core import QDialog, QLabel, QPushButton

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'previews'
spec = importlib.util.spec_from_file_location('tovu_installer', ROOT/'installer.py')
installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

# (file name, colour scheme, selected card, preview mode, theme shown as active)
SHOTS = (
    ('installer-light.png', 'light', 'stickers', 'light', 'clay'),
    ('installer-dark.png', 'dark', 'sky', 'dark', 'clay'),
)


def fake_status(active):
    def status(config, state=None):
        theme = installer.THEMES[active]
        return {'kind':'tovu', 'theme_id':active, 'title':theme['title'],
            'archive_sha256':installer.theme_manifest(active)['archive_sha256']}
    return status


def snapshot(name, theme_id, mode):
    def capture(dialog):
        buttons = dialog.findChildren(QPushButton)
        next(b for b in buttons if b.property('themeId') == theme_id).click()
        next(b for b in buttons if b.property('mode') == mode).click()
        for label in dialog.findChildren(QLabel):
            if label.text().startswith('Profile:'):
                label.setText('Profile: ~/.config/calibre')
        dialog.adjustSize()
        if not dialog.grab().save(str(OUT/name)):
            raise OSError(f'Could not save {name}')
        print(f'Saved previews/{name}')
        return 0
    return capture


with tempfile.TemporaryDirectory(prefix='tovu-shot-') as profile:
    for name, scheme, theme_id, mode, active in SHOTS:
        os.environ['TOVU_GUI_SCHEME'] = scheme
        installer.icon_status = fake_status(active)
        installer.load_state = lambda config: {'phase':'installed', 'previous':[]}
        QDialog.exec = snapshot(name, theme_id, mode)
        installer.gui(Path(profile), theme_id)

"""Exercise the theme cards and palette switch, and optionally save the real Qt UI."""
import importlib.util
import os
from pathlib import Path

from calibre.constants import config_dir
from qt.core import QDialog, QLabel, QPushButton

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tovu_installer',ROOT/'installer.py')
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)


def inspect(dialog):
    buttons=dialog.findChildren(QPushButton)
    cards={b.property('themeId'):b for b in buttons if b.objectName()=='themeCard'}
    modes={b.property('mode'):b for b in buttons if b.objectName()=='segButton'}
    actions={b.text():b for b in buttons if b.objectName()=='action'}
    preview=next(l for l in dialog.findChildren(QLabel) if l.objectName()=='preview')
    title=next(l for l in dialog.findChildren(QLabel) if l.objectName()=='previewTitle')
    if set(cards)!=set(installer.THEMES) or set(modes)!={'light','dark'}:
        raise AssertionError('Theme cards or palette switch missing')
    for name in ('Restore previous','Restore default','Close'):
        if name not in actions:
            raise AssertionError(('Missing action button',name))
    if len({(b.width(),b.height()) for b in actions.values()})!=1:
        raise AssertionError(('Action buttons differ in size',[(t,b.size()) for t,b in actions.items()]))
    for theme_id,card in cards.items():
        card.click()
        if title.text()!=installer.THEMES[theme_id]['title']:
            raise AssertionError(('Theme selection did not update the preview',theme_id))
        for mode in ('light','dark'):
            modes[mode].click()
            if preview.pixmap().isNull():
                raise AssertionError(('Missing preview',theme_id,mode))
    cards[installer.DEFAULT_THEME].click()
    modes[os.environ.get('TOVU_GUI_SCHEME','light')].click()
    dialog.adjustSize()
    snapshot=os.environ.get('TOVU_GUI_SNAPSHOT')
    if snapshot and not dialog.grab().save(snapshot):
        raise OSError('Could not save the installer screenshot')
    print(f'English Qt assistant: {len(cards)} theme cards, both palette previews and equal action buttons passed.')
    return 0


QDialog.exec=inspect
installer.gui(Path(os.environ.get('TOVU_GUI_PROFILE') or config_dir),installer.DEFAULT_THEME)

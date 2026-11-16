#!/usr/bin/env python3
"""Tovu Calibre Themes installer. Run with calibre-debug, never needs root or internet."""
import argparse
import hashlib
import io
import json
import lzma
import os
import shutil
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
STATE_NAME = 'tovu-state.json'
# Earlier releases were named Calibra. Their state file and backups stay valid,
# so "Restore previous" keeps working after upgrading.
LEGACY_STATE_NAME = 'calibra-state.json'
BACKUP_DIRS = ('tovu-backups/', 'calibra-backups/')
DEFAULT_THEME = 'stickers'
USER_THEME_FILES = ('icons-any.rcc', 'icons-light.rcc', 'icons-dark.rcc')
THEMES = {
    'line': {'tagline':'Clean outlines in teal and slate', 'title':'Tovu Line', 'root':ROOT, 'archive':'tovu-line-theme.zip', 'prefix':'tovu_line',
        'description':'Clean, rounded line icons in teal and slate. Automatically adapts to light and dark mode.'},
    'clay': {'tagline':'Soft 3D plasticine in pastels', 'title':'Tovu Clay', 'root':ROOT/'themes/clay', 'archive':'tovu-clay-theme.zip', 'prefix':'tovu_clay',
        'description':'Soft tactile 3D plasticine, rounded shapes and warm pastels. Transparent icons with consistent lighting and floating shadows.'},
    'sky': {'tagline':'Colorful outlines with gradients', 'title':'Tovu Sky', 'root':ROOT/'themes/sky', 'archive':'tovu-sky-theme.zip', 'prefix':'tovu_sky',
        'description':'Colorful clean outlines in mint, teal, coral, rose, violet, amber and indigo. Soft gradients, minimal fills and equal padding, with light and dark variants.'},
    'pencil': {'tagline':'Hand-drawn graphite sketches', 'title':'Tovu Pencil', 'root':ROOT/'themes/pencil', 'archive':'tovu-pencil-theme.zip', 'prefix':'tovu_pencil',
        'description':'Hand-drawn graphite icons with softly repeated contours, visible pencil grain and cross-hatched shading. Transparent artwork in light and dark variants.'},
    'pencil-color': {'tagline':'Colored-pencil sketches', 'title':'Tovu Pencil Color', 'root':ROOT/'themes/pencil-color', 'archive':'tovu-pencil-color-theme.zip', 'prefix':'tovu_pencil_color',
        'description':'A colored-pencil edition of Pencil in teal, coral, green, ochre, blue and violet. The same hand-drawn pictograms, pencil grain and cross-hatched shading, with transparent light and dark variants.'},
    'stickers': {'tagline':'Die-cut vinyl stickers', 'title':'Tovu Stickers', 'root':ROOT/'themes/stickers', 'archive':'tovu-stickers-theme.zip', 'prefix':'tovu_stickers',
        'description':'Colorful die-cut stickers with rounded illustrations, bold outlines, thick white edges and soft shadows. Transparent artwork for light and dark backgrounds.'},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2)+'\n'
    fd, tmp = tempfile.mkstemp(prefix='.tovu-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def load_state(config):
    for name in (STATE_NAME, LEGACY_STATE_NAME):
        p = config/name
        if p.exists():
            state = json.loads(p.read_text())
            if state.get('theme_id') in THEMES:
                state['title'] = THEMES[state['theme_id']]['title']
            return state
    return None


def migrate_legacy_state(config):
    """Move a Calibra-era state file to the current name before changing anything."""
    legacy = config/LEGACY_STATE_NAME
    if not legacy.is_file():
        return
    if not (config/STATE_NAME).exists():
        atomic_json(config/STATE_NAME, load_state(config))
    legacy.unlink()


def package(theme_id):
    theme = THEMES[theme_id]
    manifest = json.loads((theme['root']/'manifest.json').read_text())
    archive = theme['root']/theme['archive']
    if digest(archive) != manifest['archive_sha256']:
        raise RuntimeError('The theme package is damaged. Extract Tovu Calibre Themes again.')
    with zipfile.ZipFile(archive) as z:
        metadata = json.loads(z.read(theme['prefix']+'/metadata.json'))
        data = lzma.decompress(z.read(theme['prefix']+'/icons.zip.xz'), memlimit=128*1024*1024)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in info.filename or not info.filename.endswith('.png'):
                raise RuntimeError('The package contains an invalid icon path.')
            if info.filename not in manifest['files'] or hashlib.sha256(z.read(info)).hexdigest() != manifest['files'][info.filename]:
                raise RuntimeError(f'Damaged icon: {info.filename}')
        expected = {n for n in manifest['files'] if n.endswith('.png')}
        if set(z.namelist()) != expected:
            raise RuntimeError('The icon package is incomplete.')
    return manifest, metadata, data


def safe_destination(config, rel):
    candidate = config/rel
    if not candidate.resolve().is_relative_to(config.resolve()):
        raise RuntimeError(f'The path is outside the Calibre profile: {rel}')
    return candidate


def validate_state(config, state):
    rel = PurePosixPath(state['backup'])
    if rel.is_absolute() or '..' in rel.parts or not str(rel).startswith(BACKUP_DIRS):
        raise RuntimeError('The backup path is invalid.')
    backup = safe_destination(config, str(rel))
    for name, expected in state['previous'].items():
        safe_destination(config, name)
        saved = safe_destination(backup, name)
        if not saved.is_file() or digest(saved) != expected:
            raise RuntimeError(f'The previous backup is missing or damaged: {name}')
    return backup


def install(config, theme_id):
    from calibre.constants import numeric_version
    from calibre.utils.rcc import compile_icon_dir_as_themes
    if numeric_version < (6, 0, 0):
        raise RuntimeError('Tovu Calibre Themes requires Calibre 6 or later.')
    manifest, metadata, data = package(theme_id)
    title = THEMES[theme_id]['title']
    config.mkdir(parents=True, exist_ok=True)
    old_state = load_state(config)
    if old_state:
        if old_state.get('phase') != 'installed':
            raise RuntimeError('An interrupted installation was found. Restore the previous theme first.')
        backup = validate_state(config, old_state)
        if old_state.get('archive_sha256') == manifest['archive_sha256'] and (config/'icons-any.rcc').is_file() and digest(config/'icons-any.rcc') == old_state['installed_sha256']:
            return f'{title} is already installed. Reopen Calibre to see the icons.'
    else:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
        backup = config/'tovu-backups'/stamp

    # Compile completely before modifying the active profile. The compiler is
    # Calibre's own, without loading its GUI preferences or legacy migration.
    with tempfile.TemporaryDirectory(prefix='.tovu-build-', dir=config) as work:
        work = Path(work)
        compiled = work/'icons-any.rcc'
        sources = work/'sources'; sources.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(sources)
        (sources/'metadata.json').write_text(json.dumps(metadata),encoding='utf-8')
        compile_icon_dir_as_themes(str(sources),str(compiled),
            theme_name='calibre-user-any',inherits='calibre-default',for_theme='any')
        if not compiled.is_file() or compiled.stat().st_size == 0:
            raise RuntimeError('Calibre could not compile the theme.')
        candidates = ['icons-any.rcc','icons-light.rcc','icons-dark.rcc']
        candidates += ['resources/images/'+n for n in manifest['files'] if n.endswith('.png')]
        candidates += ['resources/images/icon-theme.json']
        current = {}
        for name in candidates:
            p = safe_destination(config,name)
            if p.is_symlink():
                raise RuntimeError(f'There is a symbolic link at {name}. Check that resource before installing.')
            if p.exists():
                if not p.is_file():
                    raise RuntimeError(f'Expected a file at {name}.')
                current[name] = digest(p)
        previous = dict(old_state['previous']) if old_state else {}
        backup.mkdir(parents=True,exist_ok=True)
        changes = None
        for name,checksum in current.items():
            snapshot = work/'rollback'/name
            snapshot.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(config/name,snapshot)
            # The currently installed Tovu RCC is a replaceable resource,
            # never the original theme to restore after switching packs.
            if old_state and name == 'icons-any.rcc' and checksum == old_state['installed_sha256']:
                continue
            if name not in previous:
                saved=backup/name; saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(config/name,saved); previous[name]=checksum
            elif old_state and checksum != previous[name]:
                changes=changes or backup/'changed-after-install'/uuid.uuid4().hex[:8]
                saved=changes/name; saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(config/name,saved)
        state = {'version':1,'theme_id':theme_id,'title':title,
            'backup':backup.relative_to(config).as_posix(),'previous':previous,
            'installed_sha256':digest(compiled),'archive_sha256':manifest['archive_sha256'],'phase':'prepared'}
        atomic_json(config/STATE_NAME,state)
        try:
            for name in current:
                (config/name).unlink()
            os.replace(compiled,config/'icons-any.rcc')
            state['phase']='installed'
            atomic_json(config/STATE_NAME,state)
        except BaseException:
            (config/'icons-any.rcc').unlink(missing_ok=True)
            for name in current:
                dst=config/name; dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(work/'rollback'/name,dst)
            if old_state:
                atomic_json(config/STATE_NAME,old_state)
            else:
                (config/STATE_NAME).unlink(missing_ok=True)
            raise
    message=f'{title} installed: {manifest["icons"]} icons, with light and dark modes.\nReopen Calibre to apply the theme.'
    if changes:
        message+=f'\nChanges made after installation were also saved to: {changes}'
    return message


def uninstall(config):
    state = load_state(config)
    if not state:
        return 'Tovu Calibre Themes is not installed in this profile.'
    backup = validate_state(config,state)
    # Preserve subsequent user changes separately; original backup stays intact.
    conflicts = []
    for name in set(state['previous']) | {'icons-any.rcc','icons-light.rcc','icons-dark.rcc'}:
        p = safe_destination(config,name)
        if p.is_symlink():
            raise RuntimeError(f'There is a symbolic link at {name}. No files have been restored.')
        if p.exists() and not p.is_file():
            raise RuntimeError(f'Unexpected folder at {name}. No files have been restored.')
        if p.exists() and (name != 'icons-any.rcc' or digest(p) != state['installed_sha256']):
            conflicts.append(name)
    # Stage every restore first. If a file cannot be read/copied, change nothing.
    with tempfile.TemporaryDirectory(prefix='.tovu-restore-',dir=config) as work:
        for name in state['previous']:
            p = Path(work)/name; p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(backup/name,p)
        if conflicts:
            newer = backup/'changed-after-install'/uuid.uuid4().hex[:8]
            for name in conflicts:
                p = newer/name; p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(config/name,p)
        for name in ('icons-any.rcc','icons-light.rcc','icons-dark.rcc'):
            (config/name).unlink(missing_ok=True)
        for name in state['previous']:
            dst = config/name; dst.parent.mkdir(parents=True,exist_ok=True)
            os.replace(Path(work)/name,dst)
    (config/STATE_NAME).unlink()
    message = 'Previous theme restored. Reopen Calibre to see the change.'
    if conflicts:
        message += f'\nChanges made after installation were also saved to: {newer}'
    return message


@lru_cache(maxsize=None)
def theme_manifest(theme_id):
    return json.loads((THEMES[theme_id]['root']/'manifest.json').read_text())


@lru_cache(maxsize=1)
def icon_resource_names():
    """Profile files that change Calibre's icons: theme RCCs and icon overrides."""
    names = set(USER_THEME_FILES) | {'resources/images/icon-theme.json'}
    for theme_id in THEMES:
        names |= {'resources/images/'+n for n in theme_manifest(theme_id)['files'] if n.endswith('.png')}
    return tuple(sorted(names))


def present_icon_resources(config):
    return [n for n in icon_resource_names() if (config/n).exists() or (config/n).is_symlink()]


def icon_status(config, state=None):
    """What Calibre will show: a Tovu theme, its default icons, or another theme."""
    rcc = config/'icons-any.rcc'
    if (state and state.get('phase') == 'installed' and rcc.is_file() and not rcc.is_symlink()
            and digest(rcc) == state.get('installed_sha256')):
        return {'kind':'tovu', 'theme_id':state.get('theme_id', 'line'),
            'title':state.get('title', 'Tovu Line'), 'archive_sha256':state.get('archive_sha256')}
    if present_icon_resources(config):
        return {'kind':'custom', 'title':'Custom icon theme'}
    return {'kind':'default', 'title':'Calibre default icons'}


def restore_default(config):
    """Return to the icons bundled with Calibre, backing up every removed file."""
    found = []
    for name in icon_resource_names():
        p = safe_destination(config, name)
        if p.is_symlink():
            raise RuntimeError(f'There is a symbolic link at {name}. No files have been changed.')
        if p.exists():
            if not p.is_file():
                raise RuntimeError(f'Unexpected folder at {name}. No files have been changed.')
            found.append(name)
    state = load_state(config)
    # With an empty "previous" set, the pre-Tovu theme was already Calibre's
    # default, so there is nothing left for "Restore previous" to bring back.
    keep_state = bool(state and state.get('previous'))
    if not found:
        if state and not keep_state:
            (config/STATE_NAME).unlink()
        return 'Calibre is already using its default icons.'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    backup = config/'tovu-backups'/(stamp+'-before-default')
    # Copy everything first; if any copy fails, nothing is removed.
    for name in found:
        saved = backup/name; saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config/name, saved)
        if digest(saved) != digest(config/name):
            raise RuntimeError(f'Could not back up {name}. No files have been changed.')
    for name in found:
        (config/name).unlink()
    if state and not keep_state:
        (config/STATE_NAME).unlink()
    return ('Calibre default icons restored. Reopen Calibre to see the change.\n'
        f'The removed icon files were saved to: {backup}')



def perform(config, action, theme_id=DEFAULT_THEME):
    from calibre.utils.lock import SingleInstance
    # Same lock as Calibre itself: no fragile process-name guessing.
    with SingleInstance('GUI') as available:
        if not available:
            raise RuntimeError('Close Calibre before installing or restoring the theme, then try again.')
        with SingleInstance('tovu-installer') as installer_available:
            if not installer_available:
                raise RuntimeError('Another Tovu Calibre Themes installer is already running.')
            migrate_legacy_state(config)
            if action == 'install':
                return install(config,theme_id)
            if action == 'default':
                return restore_default(config)
            return uninstall(config)


PALETTES = {
    'light': {
        'bg':'#f3f5f8', 'surface':'#ffffff', 'raised':'#f7f9fb', 'border':'#e3e8ef', 'strong':'#cbd3de',
        'text':'#0f172a', 'muted':'#5f6b7c', 'accent':'#0f766e', 'accent_hover':'#115e59', 'accent_press':'#134e4a',
        'accent_text':'#ffffff', 'accent_soft':'#e8f5f3', 'ring':'#0f766e', 'warn':'#d97706', 'idle':'#94a3b8',
        'disabled_bg':'#eef1f5', 'disabled_text':'#9aa5b4',
    },
    'dark': {
        'bg':'#0e1217', 'surface':'#161b22', 'raised':'#1c232c', 'border':'#262e39', 'strong':'#38424f',
        'text':'#e6edf3', 'muted':'#94a1b2', 'accent':'#0f766e', 'accent_hover':'#128277', 'accent_press':'#0b5e57',
        'accent_text':'#ffffff', 'accent_soft':'#11292a', 'ring':'#2dd4bf', 'warn':'#f59e0b', 'idle':'#6b7787',
        'disabled_bg':'#1a2028', 'disabled_text':'#5c6776',
    },
}

STYLESHEET = '''
QDialog#tovu, QMessageBox {{ background: {bg}; }}
QWidget {{ color: {text}; font-size: 13px; }}
QLabel {{ background: transparent; }}
QToolTip {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 6px 8px; }}
QLabel#title {{ font-size: 22px; font-weight: 700; }}
QLabel#subtitle, QLabel#muted {{ color: {muted}; }}
QLabel#section {{ color: {muted}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
QLabel#previewTitle {{ font-size: 16px; font-weight: 700; }}
QLabel#description {{ color: {muted}; font-size: 13px; }}
QFrame#panel {{ background: {surface}; border: 1px solid {border}; border-radius: 16px; }}
QFrame#divider {{ background: {border}; border: none; }}
QFrame#chip {{ background: {surface}; border: 1px solid {border}; border-radius: 16px; }}
QLabel#chipText {{ font-weight: 600; }}

QPushButton#themeCard {{ background: {surface}; border: 2px solid {border}; border-radius: 14px; padding: 0; }}
QPushButton#themeCard:hover {{ background: {raised}; border-color: {strong}; }}
QPushButton#themeCard:checked {{ background: {accent_soft}; border-color: {ring}; }}
QPushButton#themeCard:focus {{ outline: none; }}
QLabel#cardTitle {{ font-size: 14px; font-weight: 700; }}
QLabel#cardTag {{ color: {muted}; font-size: 12px; }}
QLabel#badge {{ background: {accent}; color: {accent_text}; border-radius: 10px; padding: 0 10px; font-size: 10px; font-weight: 700; }}

QFrame#segment {{ background: {raised}; border: 1px solid {border}; border-radius: 10px; }}
QPushButton#segButton {{ background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 4px 14px; color: {muted}; font-weight: 600; }}
QPushButton#segButton:hover {{ color: {text}; }}
QPushButton#segButton:checked {{ background: {surface}; color: {text}; border-color: {border}; }}

QPushButton#action, QMessageBox QPushButton {{
    background: {surface}; color: {text}; border: 1px solid {strong}; border-radius: 10px;
    padding: 0 16px; font-weight: 600; }}
QMessageBox QPushButton {{ min-height: 36px; min-width: 96px; }}
QPushButton#action:hover, QMessageBox QPushButton:hover {{ background: {raised}; border-color: {muted}; }}
QPushButton#action:pressed, QMessageBox QPushButton:pressed {{ background: {border}; }}
QPushButton#action:focus, QMessageBox QPushButton:focus {{ border: 2px solid {ring}; outline: none; }}
QPushButton#action:disabled {{ background: {disabled_bg}; color: {disabled_text}; border-color: {border}; }}
QPushButton#action[primary="true"] {{ background: {accent}; color: {accent_text}; border-color: {accent}; }}
QPushButton#action[primary="true"]:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#action[primary="true"]:pressed {{ background: {accent_press}; }}
QPushButton#action[primary="true"]:focus {{ border: 2px solid {ring}; }}
QPushButton#action[primary="true"]:disabled {{ background: {disabled_bg}; color: {disabled_text}; border-color: {disabled_bg}; }}
'''


def system_scheme(app):
    forced = os.environ.get('TOVU_GUI_SCHEME')
    if forced in PALETTES:
        return forced
    from qt.core import Qt, QPalette
    try:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return 'dark'
        if scheme == Qt.ColorScheme.Light:
            return 'light'
    except AttributeError:
        pass
    return 'dark' if app.palette().color(QPalette.ColorRole.Window).lightness() < 128 else 'light'


def gui(config, selected_theme=DEFAULT_THEME):
    from qt.core import (
        QApplication, QButtonGroup, QDialog, QFontMetrics, QFrame, QGridLayout, QHBoxLayout, QIcon,
        QLabel, QMessageBox, QPainter, QPainterPath, QPixmap, QPushButton, QRectF, QSizePolicy, Qt,
        QTimer, QVBoxLayout, QWidget,
    )
    # A plain Qt app avoids Calibre's automatic legacy-theme migration before
    # we have backed up the user's existing resources.
    app = QApplication.instance() or QApplication([])
    app.setApplicationName('Tovu Calibre Themes')
    app.setStyle('Fusion')
    scheme = system_scheme(app)
    colors = PALETTES[scheme]
    app.setStyleSheet(STYLESHEET.format(**colors))

    dialog = QDialog()
    dialog.setObjectName('tovu')
    dialog.setWindowTitle('Tovu Calibre Themes')
    dialog.setWindowIcon(QIcon(str(THEMES[selected_theme]['root']/'theme/library.png')))
    dpr = max(1.0, dialog.devicePixelRatioF())

    def pixmap(path, width, radius=0):
        src = QPixmap(str(path))
        if src.isNull():
            return src
        pix = src.scaledToWidth(int(width*dpr), Qt.TransformationMode.SmoothTransformation)
        if radius:
            out = QPixmap(pix.size()); out.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            clip = QPainterPath(); clip.addRoundedRect(QRectF(0, 0, pix.width(), pix.height()), radius*dpr, radius*dpr)
            painter.setClipPath(clip); painter.drawPixmap(0, 0, pix); painter.end()
            pix = out
        pix.setDevicePixelRatio(dpr)
        return pix

    def label(text='', name=None, wrap=False):
        w = QLabel(text)
        if name:
            w.setObjectName(name)
        w.setWordWrap(wrap)
        return w

    def passive(widget):
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return widget

    root = QVBoxLayout(dialog); root.setContentsMargins(28, 24, 28, 22); root.setSpacing(18)

    # Header: brand on the left, what Calibre currently shows on the right.
    header = QHBoxLayout(); header.setSpacing(14)
    logo = QLabel(); logo.setFixedSize(48, 48)
    brand = QVBoxLayout(); brand.setSpacing(0)
    brand.addWidget(label('Tovu Calibre Themes', 'title')); brand.addWidget(label('Six icon themes for Calibre', 'subtitle'))
    chip = QFrame(); chip.setObjectName('chip')
    chip_row = QHBoxLayout(chip); chip_row.setContentsMargins(12, 6, 14, 6); chip_row.setSpacing(8)
    chip_dot = QLabel(); chip_dot.setFixedSize(9, 9)
    chip_text = label('', 'chipText')
    chip_row.addWidget(chip_dot); chip_row.addWidget(label('Active:', 'muted')); chip_row.addWidget(chip_text)
    header.addWidget(logo); header.addLayout(brand); header.addStretch(); header.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
    root.addLayout(header)

    body = QHBoxLayout(); body.setSpacing(22)

    # Theme cards instead of a drop-down: every option is visible at once.
    left = QVBoxLayout(); left.setSpacing(10)
    left.addWidget(label('CHOOSE A THEME', 'section'))
    grid = QGridLayout(); grid.setSpacing(12)
    group = QButtonGroup(dialog); group.setExclusive(True)
    cards, badges = {}, {}
    variant = '-for-dark-theme' if scheme == 'dark' else ''
    for index, (key, theme) in enumerate(THEMES.items()):
        card = QPushButton(); card.setObjectName('themeCard'); card.setCheckable(True)
        card.setProperty('themeId', key); card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setToolTip(theme['description']); card.setAccessibleName(theme['title'])
        card.setMinimumSize(212, 118); card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box = QVBoxLayout(card); box.setContentsMargins(16, 14, 16, 14); box.setSpacing(4)
        box.addStretch()
        icons = QHBoxLayout(); icons.setSpacing(6)
        for name in ('library', 'add_book', 'edit_input', 'search'):
            path = theme['root']/'theme'/f'{name}{variant}.png'
            icon = passive(QLabel()); icon.setPixmap(pixmap(path if path.exists() else theme['root']/'theme'/f'{name}.png', 36))
            icons.addWidget(icon)
        icons.addStretch()
        box.addLayout(icons); box.addSpacing(10)
        title_row = QHBoxLayout(); title_row.setSpacing(8)
        title_row.addWidget(passive(label(theme['title'], 'cardTitle')))
        badge = passive(label('ACTIVE', 'badge')); badge.setFixedHeight(20); badge.hide(); badges[key] = badge
        title_row.addWidget(badge); title_row.addStretch()
        box.addLayout(title_row)
        box.addWidget(passive(label(theme['tagline'], 'cardTag', wrap=True)))
        box.addStretch()
        group.addButton(card); cards[key] = card
        grid.addWidget(card, index // 2, index % 2)
    left.addLayout(grid, 1)
    body.addLayout(left, 5)

    # Preview panel with a segmented light/dark switch.
    panel = QFrame(); panel.setObjectName('panel')
    right = QVBoxLayout(panel); right.setContentsMargins(20, 18, 20, 20); right.setSpacing(12)
    top = QHBoxLayout()
    preview_title = label('', 'previewTitle')
    segment = QFrame(); segment.setObjectName('segment')
    seg_row = QHBoxLayout(segment); seg_row.setContentsMargins(3, 3, 3, 3); seg_row.setSpacing(2)
    modes = QButtonGroup(dialog); modes.setExclusive(True)
    mode_buttons = {}
    for mode, text in (('light', 'Light'), ('dark', 'Dark')):
        b = QPushButton(text); b.setObjectName('segButton'); b.setCheckable(True)
        b.setProperty('mode', mode); b.setCursor(Qt.CursorShape.PointingHandCursor)
        modes.addButton(b); seg_row.addWidget(b); mode_buttons[mode] = b
    mode_buttons[scheme].setChecked(True)
    top.addWidget(preview_title); top.addStretch(); top.addWidget(segment)
    right.addLayout(top)
    preview_width = 560
    preview = QLabel(); preview.setObjectName('preview')
    preview.setAlignment(Qt.AlignmentFlag.AlignCenter); preview.setMinimumSize(preview_width, int(preview_width*890/1200))
    right.addWidget(preview)
    description = label('', 'description', wrap=True)
    right.addWidget(description); right.addStretch()
    body.addWidget(panel, 6)
    root.addLayout(body, 1)

    divider = QFrame(); divider.setObjectName('divider'); divider.setFixedHeight(1)
    root.addWidget(divider)

    # Footer: notice on the left, four identical action buttons on the right.
    footer = QHBoxLayout(); footer.setSpacing(10)
    notes = QVBoxLayout(); notes.setSpacing(2)
    notes.addWidget(label('Close Calibre before continuing. Your icons are always backed up first.', 'muted'))
    profile = label('', 'muted')
    profile.setText('Profile: '+QFontMetrics(profile.font()).elidedText(str(config), Qt.TextElideMode.ElideMiddle, 380))
    profile.setToolTip(str(config)); profile.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    notes.addWidget(profile)
    footer.addLayout(notes, 1)

    def action_button(text, tooltip, primary=False):
        b = QPushButton(text); b.setObjectName('action'); b.setToolTip(tooltip)
        b.setProperty('primary', primary); b.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.addWidget(b)
        return b
    restore = action_button('Restore previous', 'Bring back the icon theme you had before installing Tovu Calibre Themes.')
    default = action_button('Restore default', 'Remove every custom icon theme and use the icons that come with Calibre.')
    close = action_button('Close', 'Close the installer without changes.')
    apply = action_button('Install theme', 'Install the selected theme.', primary=True)
    apply.setDefault(True)
    root.addLayout(footer)

    # Same size for every action button, wide enough for any label they show.
    buttons = (restore, default, close, apply)
    labels = ('Restore previous', 'Restore default', 'Close', 'Install theme', 'Installed', 'Working…')
    for b in buttons:
        b.ensurePolished()  # measure with the stylesheet's semibold font
    widest = max(QFontMetrics(b.font()).horizontalAdvance(t) for b in buttons for t in labels)
    for b in buttons:
        b.setFixedSize(widest+44, 40)

    current = {'state':None, 'status':{'kind':'default', 'title':'Calibre default icons'}}

    def selected():
        b = group.checkedButton()
        return b.property('themeId') if b else selected_theme

    def show_selection():
        key = selected(); theme = THEMES[key]
        mode = modes.checkedButton().property('mode')
        preview_title.setText(theme['title'])
        preview.setPixmap(pixmap(theme['root']/'previews'/f'{mode}.png', preview_width, radius=10))
        description.setText(theme['description'])
        logo.setPixmap(pixmap(theme['root']/'theme'/f'library{variant}.png', 48))
        dialog.setWindowIcon(QIcon(str(theme['root']/'theme/library.png')))
        status = current['status']
        active = status['kind'] == 'tovu' and status['theme_id'] == key and \
            status.get('archive_sha256') == theme_manifest(key)['archive_sha256']
        apply.setEnabled(not active)
        apply.setText('Installed' if active else 'Install theme')
        apply.setToolTip(f'{theme["title"]} is already installed.' if active else f'Install {theme["title"]}.')

    def refresh():
        try:
            state = load_state(config)
            status = icon_status(config, state)
        except Exception as err:
            QMessageBox.critical(dialog, 'Could not read the profile', str(err))
            for b in (apply, restore, default):
                b.setEnabled(False)
            return
        current.update(state=state, status=status)
        dot = {'tovu':colors['accent'] if scheme == 'light' else colors['ring'],
            'custom':colors['warn'], 'default':colors['idle']}[status['kind']]
        chip_dot.setStyleSheet(f'background: {dot}; border-radius: 4px;')
        chip_text.setText(status['title'])
        for key, badge in badges.items():
            badge.setVisible(status['kind'] == 'tovu' and status['theme_id'] == key)
        restore.setEnabled(bool(state))
        default.setEnabled(status['kind'] != 'default')
        show_selection()

    def run(action):
        key = selected()
        if action == 'default':
            answer = QMessageBox.question(dialog, 'Restore Calibre default icons',
                'Remove every custom icon theme from this profile and go back to the icons that come with Calibre?\n\n'
                'The removed files are saved to tovu-backups in your Calibre profile.')
            if answer != QMessageBox.StandardButton.Yes:
                return
        for b in buttons:
            b.setEnabled(False)
        apply.setText('Working…')
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        app.processEvents()
        try:
            message = perform(config, action, key)
        except Exception as err:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(dialog, 'Could not complete the change', str(err))
        else:
            QApplication.restoreOverrideCursor()
            QMessageBox.information(dialog, 'Tovu Calibre Themes', message)
        finally:
            close.setEnabled(True)
            refresh()

    apply.clicked.connect(lambda: run('install'))
    restore.clicked.connect(lambda: run('uninstall'))
    default.clicked.connect(lambda: run('default'))
    close.clicked.connect(dialog.reject)
    group.buttonToggled.connect(lambda button, checked: checked and show_selection())
    modes.buttonToggled.connect(lambda button, checked: checked and show_selection())

    cards[selected_theme].setChecked(True)
    refresh()
    dialog.adjustSize()
    dialog.show()
    # Used by the isolated integration check, with a real Qt event loop.
    if os.environ.get('TOVU_GUI_SMOKE_TEST') == '1':
        QTimer.singleShot(100, dialog.accept)
    dialog.exec()
    return 0


def main():
    parser=argparse.ArgumentParser(description='Install or restore the Tovu icon theme. No sudo or Internet connection required.')
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--install',action='store_true',help='Install without opening the assistant')
    actions.add_argument('--uninstall',action='store_true',help='Restore the theme you had before installing Tovu Calibre Themes')
    actions.add_argument('--restore-default',action='store_true',help="Remove all custom icon themes and use Calibre's default icons")
    actions.add_argument('--status',action='store_true',help='Show installation status')
    parser.add_argument('--theme',choices=tuple(THEMES),default=DEFAULT_THEME,help=f'Icon theme to install or preview (default: {DEFAULT_THEME})')
    parser.add_argument('--config-dir',type=Path,help='Alternative Calibre profile (for testing)')
    args=parser.parse_args()
    if args.config_dir:
        os.environ['CALIBRE_CONFIG_DIRECTORY']=str(args.config_dir.expanduser().resolve())
    from calibre.constants import config_dir
    config=args.config_dir.expanduser().resolve() if args.config_dir else Path(config_dir).resolve()
    if args.status:
        state=load_state(config)
        print(json.dumps({'profile':str(config),'installed':bool(state),'icons':icon_status(config,state)['title'],'state':state},ensure_ascii=False,indent=2))
        return 0
    if args.install or args.uninstall or args.restore_default:
        # Compile icons headlessly; this also works in a terminal without X11.
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from qt.core import QApplication
        app=QApplication.instance() or QApplication([])
        action='install' if args.install else 'default' if args.restore_default else 'uninstall'
        print(perform(config,action,args.theme))
        return 0
    return gui(config,args.theme)

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'Tovu Line: {error}',file=sys.stderr)
        raise SystemExit(1)

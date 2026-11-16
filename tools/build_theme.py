#!/usr/bin/env python3
"""Rebuild Tovu Line offline: calibre-debug -e tools/build_theme.py."""
import hashlib
import html
import io
import json
import lzma
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Explicit semantic mapping, rather than one placeholder for unrelated actions.
GROUPS = {
    'accessibility': 'accessibility', 'add_book': 'book-plus', 'ai': 'sparkles',
    'apple-touch-icon': 'library-big', 'arrow-down': 'arrow-down', 'arrow-up': 'arrow-up',
    'auto-reload': 'refresh-cw', 'auto-scroll': 'arrow-down-circle',
    'auto_author_sort': 'list-ordered', 'back': 'arrow-left', 'beautify': 'sparkles',
    'book': 'book', 'bookmarks': 'bookmark', 'books_in_series': 'book-copy',
    'bookshelf': 'library-big', 'bullhorn': 'megaphone', 'calibre': 'library-big',
    'catalog': 'notebook-tabs', 'chapters': 'list-tree', 'character-set': 'case-sensitive',
    'clear_left': 'delete', 'close': 'x', 'code': 'code-xml', 'column': 'columns-3',
    'compress-image': 'image-down', 'config': 'settings-2', 'connect_share': 'share-2',
    'connect_share_on': 'radio', 'context_menu': 'list', 'convert': 'refresh-cw',
    'copy-to-library': 'book-copy', 'cover_flow': 'gallery-horizontal-end',
    'cyoa': 'route', 'debug': 'bug', 'default_cover': 'book-open',
    'dialog_error': 'circle-x', 'dialog_information': 'info',
    'dialog_question': 'circle-help', 'dialog_warning': 'triangle-alert',
    'dictionary': 'book-a', 'diff': 'file-diff', 'document-encrypt': 'file-lock-2',
    'document-import': 'file-input', 'document-new': 'file-plus-2',
    'document-split': 'split', 'document_open': 'folder-open', 'donate': 'heart',
    'dot_green': 'circle', 'dot_red': 'circle', 'download-metadata': 'cloud-download',
    'drm-locked': 'lock-keyhole', 'drm-unlocked': 'lock-keyhole-open',
    'edit-clear': 'eraser', 'edit-copy': 'copy', 'edit-cut': 'scissors',
    'edit-paste': 'clipboard-paste', 'edit-redo': 'redo-2',
    'edit-select-all': 'square-dashed-mouse-pointer', 'edit-undo': 'undo-2',
    'edit_book': 'book-open-check', 'edit_input': 'square-pen', 'eject': 'eject',
    'embed-fonts': 'type-outline', 'exec': 'terminal', 'external-link': 'external-link',
    'favicon-192': 'library-big', 'favicon-512': 'library-big', 'filter': 'list-filter',
    'folder_saved_search': 'folder-search', 'font': 'type',
    'font_size_larger': 'a-large-small', 'font_size_smaller': 'a-large-small',
    'format-fill-color': 'paint-bucket', 'format-indent-less': 'indent-decrease',
    'format-indent-more': 'indent-increase', 'format-justify-center': 'text-align-center',
    'format-justify-fill': 'text-align-justify', 'format-justify-left': 'text-align-start',
    'format-justify-right': 'text-align-end', 'format-list-ordered': 'list-ordered',
    'format-list-unordered': 'list', 'format-text-bold': 'bold',
    'format-text-color': 'baseline', 'format-text-heading': 'heading',
    'format-text-hr': 'separator-horizontal', 'format-text-italic': 'italic',
    'format-text-strikethrough': 'strikethrough', 'format-text-subscript': 'subscript',
    'format-text-superscript': 'superscript', 'format-text-underline': 'underline',
    'forward': 'arrow-right', 'fts': 'text-search', 'gear': 'settings',
    'generic-library': 'library', 'gmail_logo': 'mail', 'grid': 'grid-2x2',
    'h-ellipsis': 'ellipsis', 'help': 'circle-help', 'heuristics': 'wand-sparkles',
    'highlight': 'highlighter', 'highlight_only_off': 'eye-off',
    'highlight_only_on': 'eye', 'hotmail': 'mails', 'html-fix': 'file-code-2',
    'icon_choose': 'shapes', 'identifiers': 'fingerprint', 'insert-link': 'link',
    'jobs': 'activity', 'keyboard-prefs': 'keyboard', 'languages': 'languages',
    'layout': 'panels-top-left', 'library': 'library-big', 'list_remove': 'list-minus',
    'lookfeel': 'palette', 'lt': 'arrow-left-to-line', 'mail': 'mail',
    'marked': 'bookmark-check', 'merge': 'merge', 'merge_books': 'combine',
    'metadata': 'file-pen-line', 'minus': 'minus', 'minusminus': 'chevrons-left',
    'modified': 'pencil', 'network-server': 'server', 'news': 'newspaper',
    'next': 'chevron-right', 'notes': 'sticky-note', 'ok': 'check',
    'page': 'file', 'plugboard': 'cable', 'plugins': 'puzzle', 'plus': 'plus',
    'plusplus': 'chevrons-right', 'polish': 'sparkles', 'previous': 'chevron-left',
    'print': 'printer', 'publisher': 'building-2', 'quickview': 'scan-eye',
    'random': 'shuffle', 'rating': 'star', 'reader': 'tablet',
    'reference': 'quote', 'remove_books': 'trash-2', 'reports': 'chart-no-axes-combined',
    'resize': 'expand', 'restart': 'rotate-cw', 'rotate-right': 'rotate-cw',
    'save': 'save', 'scene-divider': 'separator-horizontal', 'scheduler': 'calendar-clock',
    'scroll': 'scroll-text', 'sd': 'card-sim', 'search': 'search',
    'search_add_saved': 'bookmark-plus', 'search_copy_saved': 'copy-plus',
    'search_delete_saved': 'bookmark-minus', 'send': 'send', 'series': 'layers',
    'similar': 'git-compare-arrows', 'smarten-punctuation': 'quote',
    'snippets': 'braces', 'sort': 'arrow-down-a-z', 'spell-check': 'spell-check',
    'split': 'split', 'store': 'shopping-bag', 'subset-fonts': 'remove-formatting',
    'swap': 'arrow-left-right', 'sync-right': 'arrow-right-left', 'sync': 'refresh-cw',
    'tags': 'tags', 'tb_folder': 'folder', 'template_funcs': 'function-square',
    'toc': 'list-tree', 'trash': 'trash-2', 'trim': 'crop', 'tweak': 'sliders-horizontal',
    'tweaks': 'sliders-horizontal', 'unpack-book': 'package-open',
    'user_profile': 'user-round', 'v-ellipsis': 'ellipsis-vertical',
    'view-image': 'image', 'view-refresh': 'refresh-cw', 'view': 'book-open-text',
    'viewer': 'book-open-text', 'vl': 'folders', 'width': 'arrow-left-right',
    'window-close': 'x', 'wizard': 'wand-sparkles',
}
DEVICE_MAP = {
    'bambook':'tablet', 'boox':'tablet', 'folder':'folder', 'ipad':'tablet',
    'italica':'tablet', 'itunes':'music-2', 'kindle':'tablet-smartphone',
    'nook':'tablet', 'tablet':'tablet',
}
PALETTES = {
    'light': {'ink':'#475569', 'accent':'#0f766e', 'danger':'#be4153', 'warning':'#a16207', 'muted':'#94a3b8'},
    'dark': {'ink':'#cbd5e1', 'accent':'#5eead4', 'danger':'#fda4af', 'warning':'#fcd34d', 'muted':'#64748b'},
}
ACCENT = set('add_book book book­shelf library library-big metadata convert view viewer reader save send connect_share news catalog edit_book polish lookfeel download-metadata search user_profile plugins series tags books_in_series book­marks generic-library cover_flow'.replace('\u00ad','').split())
DANGER = set('remove_books trash dialog_error dot_red search_delete_saved plugin_disabled_invalid plugin_new_invalid plugin_upgrade_invalid'.split())
WARNING = {'dialog_warning', 'drm-locked', 'plugin_deprecated'}


def svg_icon(name, mode):
    from xml.etree import ElementTree as ET
    palette = PALETTES[mode]
    base = Path(name).stem
    stem = re.sub(r'-for-(light|dark)-theme$', '', base)
    parent = str(Path(name).parent)
    role = 'danger' if stem in DANGER else 'warning' if stem in WARNING else 'accent' if stem in ACCENT or stem in {'ok','dot_green'} else 'ink'
    color = palette[role]
    if stem == 'blank':
        return '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 24 24"/>'
    if parent == 'mimetypes' and stem not in {'computer', 'dir'}:
        label = {'unknown':'?', 'zero':'0','jpeg':'JPG','azw2':'AZW','azw3':'AZW3','computer':'PC'}.get(stem, stem.upper())
        # Each format stays recognizable; all use the same document geometry.
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 24 24">
        <g fill="none" stroke="{palette['ink']}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></g>
        <rect x="1.5" y="12" width="21" height="7.5" rx="2" fill="{palette['accent']}"/>
        <text x="12" y="17.3" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="4.6" font-weight="bold" fill="{'#ffffff' if mode=='light' else '#0f2926'}">{html.escape(label)}</text></svg>'''
    if parent == 'devices':
        icon = DEVICE_MAP[stem]
    elif parent == 'plugins':
        icon = 'message-circle' if stem=='mobileread' else 'package-x' if 'invalid' in stem else 'package-check' if stem.endswith(('valid','ok')) else 'package-plus' if 'new' in stem else 'package-open' if 'deprecated' in stem else 'package'
    elif parent == 'mimetypes':
        icon = {'computer':'monitor','dir':'folder'}[stem]
    else:
        icon = GROUPS[stem]
    source = ROOT/'vendor/lucide'/f'{icon}.svg'
    if not source.is_file():
        raise ValueError(f'Missing Lucide icon: {icon} ({name})')
    node = ET.fromstring(source.read_text())
    node.set('width','128'); node.set('height','128')
    node.set('stroke',color); node.set('stroke-width','1.7')
    if stem in {'dot_green','dot_red'}:
        node.set('fill',color)
    if stem == 'font_size_smaller':
        # Distinguish the two font controls even at toolbar sizes.
        children = list(node)
        for child in children:
            node.remove(child)
        group = ET.SubElement(node, '{http://www.w3.org/2000/svg}g', {'transform':'translate(3 3) scale(.75)'})
        for child in children:
            group.append(child)
    return ET.tostring(node,encoding='unicode')


def build():
    from qt.core import QImage, QPainter, QRectF, Qt, QSvgRenderer, QApplication
    app = QApplication.instance() or QApplication([])
    inventory = json.loads((ROOT/'tools/inventory.json').read_text())
    dest = ROOT/'theme'
    dest.mkdir(exist_ok=True)
    hashes = {}
    for name in inventory:
        for mode in ('light','dark'):
            svg = svg_icon(name, mode)
            vector = ROOT/'svg'/mode/Path(name).with_suffix('.svg')
            vector.parent.mkdir(parents=True,exist_ok=True)
            vector.write_text(svg)
            rel = str(Path(name).with_suffix(''))+f'-for-{mode}-theme.png'
            target = dest/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            image = QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer = QSvgRenderer(svg.encode())
            if not renderer.isValid():
                raise ValueError(f'Invalid SVG: {name}')
            renderer.render(painter,QRectF(0,0,128,128)); painter.end()
            if not image.save(str(target)):
                raise OSError(f'Cannot save {target}')
            hashes[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
            if mode == 'light':
                # Base fallback also makes the source folder usable with the GUI theme creator.
                normal = dest/Path(name).with_suffix('.png')
                normal.write_bytes(target.read_bytes())
                hashes[normal.relative_to(dest).as_posix()] = hashes[rel]
    metadata = {'name':'tovu_line','title':'Tovu Line','author':'Tovu Calibre Themes · Lucide contributors',
        'version':1,'description':'Rounded line icons in teal and slate. Automatically adapts to light and dark modes.',
        'license':'ISC / MIT','color_palette':'any','number':len(inventory)}
    (dest/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    hashes['metadata.json'] = hashlib.sha256((dest/'metadata.json').read_bytes()).hexdigest()
    make_preview(inventory)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
        for name in sorted(hashes):
            if name.endswith('.png'):
                z.writestr(name,(dest/name).read_bytes())
    compressed = lzma.compress(buf.getvalue())
    with zipfile.ZipFile(ROOT/'tovu-line-theme.zip','w',zipfile.ZIP_STORED) as z:
        z.write(dest/'metadata.json','tovu_line/metadata.json')
        z.write(ROOT/'previews/cover.jpg','tovu_line/icon-theme-cover.jpg')
        z.writestr('tovu_line/icons.zip.xz',compressed)
    manifest = {'version':1,'icons':len(inventory),'files':hashes,
        'archive_sha256':hashlib.sha256((ROOT/'tovu-line-theme.zip').read_bytes()).hexdigest()}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Tovu Line: {len(inventory)} icon names, {len(hashes)-1} PNGs, native ZIP built.')


def make_preview(inventory):
    from PIL import Image, ImageDraw, ImageFont
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    regular = ImageFont.truetype(font,16)
    small = ImageFont.truetype(font,12)
    title = ImageFont.truetype(font,40)
    names = [('add_book','Add books'),('metadata','Metadata'),('convert','Convert'),
        ('view','Read'),('send','Send'),('save','Save'),('news','News'),
        ('connect_share','Share'),('remove_books','Remove'),('config','Preferences'),
        ('edit_book','Edit book'),('polish','Polish'),('library','Library'),
        ('search','Search'),('tags','Tags'),('series','Series'),('catalog','Catalog'),
        ('store','Store'),('user_profile','Authors'),('plugins','Plugins')]
    subtitle = 'A calmer library.  /  Icons for Calibre'
    footer = 'Consistent strokes · Slate and teal palette · Light and dark modes'
    for mode,bg,fg,panel in [('light','#f8fafc','#172b3a','#ffffff'),('dark','#111c28','#e6eff4','#1a2938')]:
        image = Image.new('RGB',(1200,760),bg); d=ImageDraw.Draw(image)
        d.text((48,32),'Tovu Line',font=title,fill=fg)
        d.text((50,91),subtitle,font=regular,fill=PALETTES[mode]['ink'])
        d.rounded_rectangle((48,138,1152,690),radius=24,fill=panel)
        for i,(name,label) in enumerate(names):
            x=66+(i%5)*216; y=162+(i//5)*128
            icon=Image.open(ROOT/'theme'/f'{name}-for-{mode}-theme.png').convert('RGBA')
            icon.thumbnail((56,56),Image.Resampling.LANCZOS)
            image.paste(icon,(x+66,y),icon)
            bbox=d.textbbox((0,0),label,font=regular)
            d.text((x+94-(bbox[2]-bbox[0])/2,y+71),label,font=regular,fill=fg)
        d.text((50,717),footer,font=small,fill=PALETTES[mode]['ink'])
        image.save(ROOT/'previews'/f'{mode}.png')
    Image.open(ROOT/'previews/light.png').resize((680,431),Image.Resampling.LANCZOS).save(ROOT/'previews/cover.jpg',quality=90)
    cols=10; cell=112; rows=(len(inventory)+cols-1)//cols
    sheet=Image.new('RGB',(cols*cell,rows*100),'#f8fafc'); d=ImageDraw.Draw(sheet)
    for i,name in enumerate(inventory):
        x=(i%cols)*cell; y=(i//cols)*100
        icon=Image.open(ROOT/'theme'/Path(name).with_suffix('.png')).convert('RGBA'); icon.thumbnail((38,38))
        sheet.paste(icon,(x+37,y+8),icon)
        label=Path(name).stem
        for row in range(2):
            piece=label[row*17:(row+1)*17]
            box=d.textbbox((0,0),piece,font=small)
            d.text((x+(cell-box[2])/2,y+54+row*15),piece,font=small,fill='#475569')
    sheet.save(ROOT/'previews/all-icons.png')


if __name__ == '__main__':
    build()

#!/usr/bin/env python3
"""Build the separate colored-pencil theme from its bundled edited atlases."""
import hashlib
import io
import json
import lzma
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLOR = ROOT/'themes/pencil-color'
sys.path.insert(0, str(ROOT/'tools'))
from icon_sizing import fit_icon
from build_clay import SHEETS, isolate_tile, resource as mapped_resource


def atlas_icons():
    from qt.core import QImage, QPainter, Qt
    icons, extraction = {}, {}
    for sheet, names in SHEETS.items():
        image = QImage(str(COLOR/'source'/sheet))
        if image.isNull() or len(names) != 36:
            raise ValueError(f'Invalid source atlas: {sheet}')
        w, h = image.width(), image.height()
        columns, rows = [0]*w, [0]*h
        for y in range(h):
            for x in range(w):
                if image.pixelColor(x, y).alpha() > 120:
                    columns[x] += 1
                    rows[y] += 1

        def boundaries(counts):
            n = len(counts)
            return [0] + [min(range(int((i-.2)*n/6), int((i+.2)*n/6)),
                             key=lambda v: (counts[v], abs(v-i*n/6)))
                          for i in range(1, 6)] + [n]

        xs, ys = boundaries(columns), boundaries(rows)
        for index, name in enumerate(names):
            row, col = divmod(index, 6)
            box = (xs[col], ys[row], xs[col+1]-xs[col], ys[row+1]-ys[row])
            tile = isolate_tile(image.copy(*box))
            tile = tile.scaled(116, 116, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            output = QImage(128, 128, QImage.Format.Format_ARGB32_Premultiplied)
            output.fill(Qt.GlobalColor.transparent)
            painter = QPainter(output)
            painter.drawImage((128-tile.width())//2, (128-tile.height())//2, tile)
            painter.end()
            icons[name] = output
            extraction[name] = {'sheet': sheet, 'row': row+1, 'column': col+1,
                                'rectangle': box}
    (COLOR/'source/extraction.json').write_text(json.dumps(extraction, indent=2)+'\n')
    return icons


def palette(image, mode):
    """Retain pigment and alpha; gently lift colored contours for dark UI."""
    from qt.core import QImage, QColor
    output = image.convertToFormat(QImage.Format.Format_ARGB32)
    if mode == 'dark':
        for y in range(output.height()):
            for x in range(output.width()):
                pixel = output.pixelColor(x, y)
                if pixel.alpha():
                    rgb = [round(c*.90+255*.10) for c in (pixel.red(), pixel.green(), pixel.blue())]
                    output.setPixelColor(x, y, QColor(*rgb, pixel.alpha()))
    return output


def resource(name, icons, mode):
    from qt.core import QPainter, QColor, QFont, QPen, QRectF, Qt
    path = Path(name)
    if path.parent.as_posix() != 'mimetypes' or path.stem in {'computer', 'dir'}:
        return mapped_resource(name, icons)
    image = icons['file'].copy()
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    ink = QColor('#286c70' if mode == 'light' else '#a6d8d3')
    painter.setBrush(QColor('#f8edcf' if mode == 'light' else '#30494c'))
    painter.setPen(QPen(ink, 1.25))
    painter.drawRoundedRect(QRectF(12, 77, 104, 27), 2, 2)
    grain = QColor(ink)
    grain.setAlpha(45)
    painter.setPen(QPen(grain, .6))
    for x in range(15, 112, 6):
        painter.drawLine(x, 101, min(x+9, 114), 80)
    font = QFont('DejaVu Sans Mono')
    font.setPixelSize(15 if len(path.stem) < 5 else 13)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(ink)
    label = {'unknown': '?', 'zero': '0', 'jpeg': 'JPG'}.get(path.stem, path.stem.upper())
    painter.drawText(QRectF(12, 77, 104, 27), Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    return image


def previews(inventory):
    from PIL import Image, ImageDraw, ImageFont
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    regular = ImageFont.truetype(font, 17)
    small = ImageFont.truetype(font, 12)
    title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', 40)
    names = [('add_book', 'Add books'), ('metadata', 'Metadata'), ('convert', 'Convert'),
             ('view', 'Read'), ('send', 'Send'), ('save', 'Save'), ('news', 'News'),
             ('connect_share', 'Share'), ('remove_books', 'Remove'), ('config', 'Preferences'),
             ('edit_book', 'Edit book'), ('polish', 'Polish'), ('library', 'Library'),
             ('search', 'Search'), ('tags', 'Tags'), ('series', 'Series'), ('catalog', 'Catalog'),
             ('store', 'Store'), ('user_profile', 'Authors'), ('plugins', 'Plugins')]
    for mode, bg, fg, muted, line in [
            ('light', '#f6f1e7', '#49463e', '#7b786e', '#ded7c9'),
            ('dark', '#26272b', '#eee5d4', '#bdb6a8', '#424247')]:
        canvas = Image.new('RGB', (1200, 890), bg)
        d = ImageDraw.Draw(canvas)
        d.text((48, 32), 'Tovu Pencil Color', font=title, fill=fg)
        d.text((50, 95), 'The same pencil spirit, in color.  /  Hand-drawn icons for Calibre', font=regular, fill=muted)
        d.line((48, 133, 1152, 133), fill=line, width=1)
        for i, (name, label) in enumerate(names):
            x, y = 48+(i % 5)*224, 151+(i//5)*164
            icon = Image.open(COLOR/'theme'/f'{name}-for-{mode}-theme.png').convert('RGBA')
            canvas.paste(icon, (x+40, y), icon)
            box = d.textbbox((0, 0), label, font=regular)
            d.text((x+104-(box[2]-box[0])/2, y+125), label, font=regular, fill=fg)
        d.line((48, 824, 1152, 824), fill=line, width=1)
        d.text((50, 846), 'Colored-pencil grain · Soft sketch contours · Cross-hatched shading · Transparent light and dark artwork', font=small, fill=muted)
        canvas.save(COLOR/'previews'/f'{mode}.png')
    Image.open(COLOR/'previews/light.png').resize((680, 504), Image.Resampling.LANCZOS).save(COLOR/'previews/cover.jpg', quality=92)
    cols, cell = 10, 120
    canvas = Image.new('RGB', (cols*cell, ((len(inventory)+cols-1)//cols)*112), '#f6f1e7')
    d = ImageDraw.Draw(canvas)
    small = ImageFont.truetype(font, 11)
    for i, name in enumerate(inventory):
        x, y = i % cols*cell, i//cols*112
        icon = Image.open(COLOR/'theme'/name).convert('RGBA')
        icon.thumbnail((70, 70))
        canvas.paste(icon, (x+25, y), icon)
        for row in range(2):
            label = Path(name).stem[row*18:(row+1)*18]
            box = d.textbbox((0, 0), label, font=small)
            d.text((x+(cell-box[2])/2, y+73+row*14), label, font=small, fill='#605a4e')
    canvas.save(COLOR/'previews/all-icons.png')


def build():
    from qt.core import QApplication
    app = QApplication.instance() or QApplication([])
    (COLOR/'previews').mkdir(parents=True, exist_ok=True)
    inventory = json.loads((ROOT/'tools/inventory.json').read_text())
    originals, hashes = atlas_icons(), {}
    for mode in ('light', 'dark'):
        icons = {name: palette(image, mode) for name, image in originals.items()}
        for name in inventory:
            image = fit_icon(resource(name, icons, mode))
            rel = str(Path(name).with_suffix(''))+f'-for-{mode}-theme.png'
            target = COLOR/'theme'/rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if not image.save(str(target)):
                raise OSError(f'Cannot save {target}')
            hashes[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
            if mode == 'light':
                (COLOR/'theme'/name).write_bytes(target.read_bytes())
                hashes[name] = hashes[rel]
    metadata = {'name': 'tovu_pencil_color', 'title': 'Tovu Pencil Color',
                'author': 'Tovu Calibre Themes', 'version': 1, 'color_palette': 'any', 'number': len(inventory),
                'description': 'A colored-pencil edition of Pencil: the same pictograms with teal, coral, green, ochre, blue and violet pigment, visible pencil grain and cross-hatched shading. Transparent light and dark artwork.',
                'license': 'See bundled artwork provenance'}
    meta = COLOR/'theme/metadata.json'
    meta.write_text(json.dumps(metadata, indent=2)+'\n')
    hashes['metadata.json'] = hashlib.sha256(meta.read_bytes()).hexdigest()
    previews(inventory)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
        for name in sorted(hashes):
            if name.endswith('.png'):
                z.writestr(name, (COLOR/'theme'/name).read_bytes())
    archive = COLOR/'tovu-pencil-color-theme.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_STORED) as z:
        z.write(meta, 'tovu_pencil_color/metadata.json')
        z.write(COLOR/'previews/cover.jpg', 'tovu_pencil_color/icon-theme-cover.jpg')
        z.writestr('tovu_pencil_color/icons.zip.xz', lzma.compress(buf.getvalue()))
    manifest = {'version': 1, 'icons': len(inventory), 'files': hashes,
                'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    (COLOR/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    print(f'Tovu Pencil Color: {len(originals)} colored pictograms, {len(inventory)} native names, 735 PNGs and native ZIP ready.')


if __name__ == '__main__':
    build()

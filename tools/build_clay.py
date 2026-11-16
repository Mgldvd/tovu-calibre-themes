#!/usr/bin/env python3
"""Package generated clay atlases into native Calibre resources using Qt."""
import hashlib
import io
import json
import lzma
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLAY=ROOT/'themes/clay'
sys.path.insert(0,str(ROOT/'tools'))
from icon_sizing import fit_icon
from build_theme import GROUPS, DEVICE_MAP

# Row-major coordinates of the 144 original generated clay pictograms.
SHEETS={
    '01-library.png': '''book-plus file-pen-line refresh-cw book-open-text send save
        newspaper share-2 trash-2 settings-2 book-open-check sparkles
        library-big search tags layers notebook-tabs shopping-bag
        user-round puzzle file folder tablet monitor
        heart star calendar-clock mail languages printer
        download upload package-open link sticky-note cloud-download'''.split(),
    '02-tools.png': '''scissors copy clipboard-paste undo-2 redo-2 eraser
        plus minus check x triangle-alert info
        circle-help lock-keyhole lock-keyhole-open settings cloud folder-search
        pencil highlighter paintbrush palette paint-bucket crop
        rotate-cw clock server keyboard card-sim cable
        book bookmark-plus bookmark-minus eye eye-off megaphone'''.split(),
    '03-navigation.png': '''arrow-left arrow-right arrow-up arrow-down chevrons-left chevrons-right
        external-link expand eject arrow-left-right split merge
        terminal bug list-filter grid-2x2 columns-3 panels-top-left
        bold italic underline heading type quote
        text-align-start text-align-center text-align-end text-align-justify list list-ordered
        code-xml braces hash spell-check arrow-down-a-z chart-no-axes-combined'''.split(),
    '04-details.png': '''accessibility route file-diff file-lock-2 file-input file-plus-2
        document-split image image-down file-code-2 folders gallery-horizontal-end
        list-tree toc fingerprint building-2 message-circle book-a
        subscript superscript strikethrough separator-horizontal indent-decrease indent-increase
        font_size_larger font_size_smaller baseline type-outline remove-formatting function-square
        square-dashed-mouse-pointer dot_green dot_red ellipsis ellipsis-vertical shuffle'''.split(),
}

# Generated atlases have slight spacing variation. These separators follow
# transparent gutters, rather than assuming every object is exactly centered.
GUTTERS={
    '01-library.png': ([0,219,411,609,812,1018,1254],[0,224,434,643,844,1034,1254]),
    '02-tools.png': ([0,216,418,615,828,1018,1254],[0,227,433,642,839,1036,1254]),
    '03-navigation.png': ([0,205,411,607,811,1011,1254],[0,217,423,642,828,1015,1254]),
    '04-details.png': ([0,203,408,621,816,1018,1254],[0,231,441,658,850,1044,1254]),
}
ALIASES={
    'a-large-small':'type','activity':'chart-no-axes-combined','arrow-left-to-line':'arrow-left',
    'arrow-right-left':'arrow-left-right','case-sensitive':'type','chevron-left':'arrow-left',
    'chevron-right':'arrow-right','folder-open':'folder','list-minus':'list',
    'radio':'share-2','sliders-horizontal':'settings-2','square-pen':'pencil',
    'arrow-down-circle':'arrow-down','book-copy':'library-big','book-open':'book-open-text',
    'bookmark':'book','bookmark-check':'book','circle':'dot_green','circle-x':'x',
    'combine':'merge','copy-plus':'copy','delete':'eraser','git-compare-arrows':'arrow-left-right',
    'library':'library-big','mails':'mail','music-2':'tablet','package':'package-open',
    'package-x':'package-open','package-check':'package-open','package-plus':'package-open',
    'scan-eye':'eye','scroll-text':'book-open-text','shapes':'grid-2x2',
    'tablet-smartphone':'tablet','text-search':'search','wand-sparkles':'sparkles',
}


def atlas_icons():
    from qt.core import QImage, QPainter, Qt, QRectF
    icons={}; extraction={}
    for sheet,names in SHEETS.items():
        if len(names)!=36:
            raise ValueError(f'Expected 36 subjects in {sheet}')
        image=QImage(str(CLAY/'source'/sheet))
        if (image.width(),image.height())!=(1254,1254):
            raise ValueError(f'Unexpected atlas dimensions: {sheet}')
        xs,ys=GUTTERS[sheet]
        for index,name in enumerate(names):
            row,col=divmod(index,6)
            box=(xs[col],ys[row],xs[col+1]-xs[col],ys[row+1]-ys[row])
            tile=isolate_tile(image.copy(*box))
            # Package the cell without changing its material, palette or alpha.
            # Equal output bounds keep native toolbar sizes consistent.
            tile=tile.scaled(116,116,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            output=QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied)
            output.fill(Qt.GlobalColor.transparent)
            painter=QPainter(output)
            painter.drawImage((128-tile.width())//2,(128-tile.height())//2,tile)
            painter.end()
            icons[name]=output
            extraction[name]={'sheet':sheet,'row':row+1,'column':col+1,'rectangle':box}
    (CLAY/'source/extraction.json').write_text(json.dumps(extraction,indent=2)+'\n')
    return icons


def isolate_tile(tile):
    """Keep this cell's objects and alpha shadows, excluding adjacent fragments."""
    from collections import deque
    from qt.core import QImage, QPainter, Qt, QColor
    w,h=tile.width(),tile.height()
    foreground={(x,y) for y in range(h) for x in range(w) if tile.pixelColor(x,y).alpha()>80}
    components=[]
    while foreground:
        start=foreground.pop(); queue=deque([start]); points=[start]
        while queue:
            x,y=queue.popleft()
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
                p=x+dx,y+dy
                if p in foreground:
                    foreground.remove(p); points.append(p); queue.append(p)
        components.append(points)
    largest=max(map(len,components),default=0)
    selected=[]
    for points in components:
        cx=sum(p[0] for p in points)/len(points); cy=sum(p[1] for p in points)/len(points)
        if len(points)>=max(30,largest*.018) and (len(points)>largest*.25 or (12<cx<w-12 and 12<cy<h-12)):
            selected.extend(points)
    mask=QImage(w,h,QImage.Format.Format_ARGB32_Premultiplied); mask.fill(Qt.GlobalColor.transparent)
    painter=QPainter(mask); painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('white'))
    rows={}
    for x,y in selected:
        rows.setdefault(y,[]).append(x)
    for y,xs in rows.items():
        xs.sort(); start=last=xs[0]
        for x in xs[1:]+[w+100]:
            if x>last+1:
                # The generated light falls from upper left: shadows extend
                # down/right. Keep a small antialiasing margin up/left without
                # including the previous cell's shadow fragments.
                painter.drawRect(start-3,y-3,last-start+21,21)
                start=x
            last=x
    painter.end()
    painter=QPainter(tile); painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0,0,mask); painter.end()
    return tile


def resource(name,icons):
    from qt.core import QImage, QPainter, Qt, QColor, QFont, QRectF, QLinearGradient, QPen
    path=Path(name); stem=path.stem; parent=path.parent.as_posix()
    if stem=='blank':
        out=QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied); out.fill(Qt.GlobalColor.transparent)
        return out
    if parent=='mimetypes' and stem not in {'computer','dir'}:
        out=icons['file'].copy(); painter=QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient=QLinearGradient(12,76,12,106)
        gradient.setColorAt(0,QColor('#8fa583')); gradient.setColorAt(1,QColor('#677f5d'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(55,39,28,40)); painter.drawRoundedRect(QRectF(15,80,102,28),7,7)
        painter.setBrush(gradient); painter.drawRoundedRect(QRectF(12,76,102,28),7,7)
        painter.setPen(QPen(QColor('#b6c4a9'),1)); painter.drawLine(20,78,106,78)
        label={'unknown':'?','zero':'0','jpeg':'JPG'}.get(stem,stem.upper())
        font=QFont('DejaVu Sans',12); font.setPixelSize(15 if len(label)<5 else 13); font.setBold(True)
        painter.setFont(font); painter.setPen(QColor('#fff6df'))
        painter.drawText(QRectF(12,76,102,28),Qt.AlignmentFlag.AlignCenter,label); painter.end()
        return out
    if parent=='devices':
        glyph=DEVICE_MAP[stem]
    elif parent=='mimetypes':
        glyph={'computer':'monitor','dir':'folder'}[stem]
    elif parent=='plugins':
        glyph='message-circle' if stem=='mobileread' else 'package-open'
    elif stem in {'dot_green','dot_red','font_size_larger','font_size_smaller'}:
        glyph=stem
    else:
        glyph=GROUPS[stem]
    glyph=ALIASES.get(glyph,glyph)
    if glyph not in icons:
        raise ValueError(f'Missing clay pictogram: {glyph} for {name}')
    out=icons[glyph].copy()
    badge=None
    if parent=='plugins' and stem!='mobileread':
        badge='x' if 'invalid' in stem else 'plus' if 'new' in stem else 'check' if stem.endswith(('valid','ok')) else 'download' if 'updates' in stem else None
    elif stem=='marked':
        badge='check'
    elif stem=='list_remove':
        badge='minus'
    if badge:
        painter=QPainter(out)
        painter.drawImage(QRectF(72,70,54,54),icons[badge]); painter.end()
    return out


def make_previews(inventory):
    from PIL import Image, ImageDraw, ImageFont
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    regular=ImageFont.truetype(font,17); small=ImageFont.truetype(font,13); title=ImageFont.truetype(font,40)
    names=[('add_book','Add books'),('metadata','Metadata'),('convert','Convert'),('view','Read'),
        ('send','Send'),('save','Save'),('news','News'),('connect_share','Share'),('remove_books','Remove'),
        ('config','Preferences'),('edit_book','Edit book'),('polish','Polish'),('library','Library'),
        ('search','Search'),('tags','Tags'),('series','Series'),('catalog','Catalog'),('store','Store'),
        ('user_profile','Authors'),('plugins','Plugins')]
    for mode,bg,fg,panel,muted in [('light','#fcf6ee','#57463c','#fffaf4','#8a7768'),('dark','#25232a','#f4e7d5','#312e36','#c6b6a5')]:
        canvas=Image.new('RGB',(1200,850),bg); d=ImageDraw.Draw(canvas)
        d.text((48,32),'Tovu Clay',font=title,fill=fg)
        d.text((50,91),'A softer little library.  /  Tactile 3D icons for Calibre',font=regular,fill=muted)
        d.rounded_rectangle((48,140,1152,778),radius=28,fill=panel)
        for i,(name,label) in enumerate(names):
            x=66+(i%5)*216; y=151+(i//5)*153
            icon=Image.open(CLAY/'theme'/f'{name}.png').convert('RGBA')
            canvas.paste(icon,(x+30,y),icon)
            box=d.textbbox((0,0),label,font=regular)
            d.text((x+94-(box[2]-box[0])/2,y+123),label,font=regular,fill=fg)
        d.text((50,808),'Warm pastels · Soft plasticine texture · Transparent icons · Light and dark modes',font=small,fill=muted)
        canvas.save(CLAY/'previews'/f'{mode}.png')
    Image.open(CLAY/'previews/light.png').resize((680,482),Image.Resampling.LANCZOS).save(CLAY/'previews/cover.jpg',quality=92)
    cols=10; cell=120; rows=(len(inventory)+cols-1)//cols
    sheet=Image.new('RGB',(cols*cell,rows*112),'#fcf6ee'); d=ImageDraw.Draw(sheet)
    fontsmall=ImageFont.truetype(font,11)
    for i,name in enumerate(inventory):
        x=(i%cols)*cell; y=(i//cols)*112
        icon=Image.open(CLAY/'theme'/name).convert('RGBA'); icon.thumbnail((70,70))
        sheet.paste(icon,(x+25,y),icon)
        for row in range(2):
            label=Path(name).stem[row*18:(row+1)*18]
            box=d.textbbox((0,0),label,font=fontsmall)
            d.text((x+(cell-box[2])/2,y+73+row*14),label,font=fontsmall,fill='#6e5d51')
    sheet.save(CLAY/'previews/all-icons.png')


def build():
    from qt.core import QApplication
    app=QApplication.instance() or QApplication([])
    inventory=json.loads((ROOT/'tools/inventory.json').read_text())
    icons=atlas_icons(); hashes={}
    for name in inventory:
        image=fit_icon(resource(name,icons))
        for suffix in ('','-for-light-theme','-for-dark-theme'):
            rel=str(Path(name).with_suffix(''))+suffix+'.png'
            target=CLAY/'theme'/rel; target.parent.mkdir(parents=True,exist_ok=True)
            if not image.save(str(target)):
                raise OSError(f'Could not save {target}')
            hashes[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
    metadata={'name':'tovu_clay','title':'Tovu Clay','author':'Tovu Calibre Themes',
        'version':1,'description':'Soft tactile 3D plasticine icons in warm pastels, with rounded forms and consistent lighting. Transparent artwork for light and dark modes.',
        'license':'See bundled artwork provenance','color_palette':'any','number':len(inventory)}
    p=CLAY/'theme/metadata.json'; p.write_text(json.dumps(metadata,indent=2)+'\n')
    hashes['metadata.json']=hashlib.sha256(p.read_bytes()).hexdigest()
    make_previews(inventory)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
        for name in sorted(hashes):
            if name.endswith('.png'): z.writestr(name,(CLAY/'theme'/name).read_bytes())
    archive=CLAY/'tovu-clay-theme.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
        z.write(CLAY/'theme/metadata.json','tovu_clay/metadata.json')
        z.write(CLAY/'previews/cover.jpg','tovu_clay/icon-theme-cover.jpg')
        z.writestr('tovu_clay/icons.zip.xz',lzma.compress(buf.getvalue()))
    manifest={'version':1,'icons':len(inventory),'files':hashes,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (CLAY/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Tovu Clay: {len(icons)} generated pictograms, {len(inventory)} native names, 735 PNGs. Native package ready.')


if __name__=='__main__':
    build()

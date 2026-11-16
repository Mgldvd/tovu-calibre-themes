#!/usr/bin/env python3
"""Package original graphite pencil atlases as a reversible Calibre theme."""
import hashlib
import io
import json
import lzma
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'src'
PENCIL=ROOT/'themes/pencil'
sys.path.insert(0,str(SRC/'tools'))
from icon_sizing import fit_icon
from build_clay import SHEETS, isolate_tile, resource as mapped_resource


def atlas_icons(folder=PENCIL):
    from qt.core import QImage,QPainter,Qt
    icons={}; extraction={}
    for sheet,names in SHEETS.items():
        image=QImage(str(SRC/'themes'/folder.name/'source'/sheet))
        if image.isNull() or len(names)!=36:
            raise ValueError(f'Invalid source atlas: {sheet}')
        w,h=image.width(),image.height()
        # Find the transparent gutters around the requested regular grid.
        columns=[0]*w; rows=[0]*h
        for y in range(h):
            for x in range(w):
                if image.pixelColor(x,y).alpha()>120:
                    columns[x]+=1; rows[y]+=1
        def boundaries(counts):
            n=len(counts); result=[0]
            for i in range(1,6):
                lo=int((i-.2)*n/6); hi=int((i+.2)*n/6)
                result.append(min(range(lo,hi),key=lambda v:counts[v]))
            return result+[n]
        xs,ys=boundaries(columns),boundaries(rows)
        for index,name in enumerate(names):
            row,col=divmod(index,6)
            box=(xs[col],ys[row],xs[col+1]-xs[col],ys[row+1]-ys[row])
            tile=isolate_tile(image.copy(*box))
            tile=tile.scaled(116,116,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            output=QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied); output.fill(Qt.GlobalColor.transparent)
            painter=QPainter(output); painter.drawImage((128-tile.width())//2,(128-tile.height())//2,tile); painter.end()
            icons[name]=output
            extraction[name]={'sheet':sheet,'row':row+1,'column':col+1,'rectangle':box}
    (SRC/'themes'/folder.name/'source/extraction.json').write_text(json.dumps(extraction,indent=2)+'\n')
    return icons


def graphite(image,mode):
    """Transfer graphite density to alpha, preserving grain in both palettes."""
    from qt.core import QImage,QColor,Qt
    output=QImage(image.width(),image.height(),QImage.Format.Format_ARGB32)
    output.fill(Qt.GlobalColor.transparent)
    rgb=(66,63,56) if mode=='light' else (231,224,207)
    for y in range(image.height()):
        for x in range(image.width()):
            pixel=image.pixelColor(x,y)
            if pixel.alpha()==0: continue
            luminance=.2126*pixel.red()+.7152*pixel.green()+.0722*pixel.blue()
            density=min(1,max(0,(255-luminance)/200))**.85
            alpha=round(pixel.alpha()*density)
            output.setPixelColor(x,y,QColor(*rgb,alpha))
    return output


def resource(name,icons,mode):
    from qt.core import QPainter,QColor,QFont,QPen,QRectF,Qt
    path=Path(name); stem=path.stem
    if path.parent.as_posix()!='mimetypes' or stem in {'computer','dir'}:
        return mapped_resource(name,icons)
    image=icons['file'].copy(); painter=QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    ink=QColor('#514d44' if mode=='light' else '#ded6c5')
    paper=QColor('#f0eddf' if mode=='light' else '#2c2d30'); paper.setAlpha(235)
    painter.setBrush(paper); painter.setPen(QPen(ink,1.25))
    painter.drawRoundedRect(QRectF(12,77,104,27),2,2)
    # Slightly repeated pencil edges, with paper showing through the badge.
    light=QColor(ink); light.setAlpha(65); painter.setPen(QPen(light,.7))
    painter.drawLine(13,76,114,78); painter.drawLine(11,103,117,105)
    font=QFont('DejaVu Sans Mono'); font.setPixelSize(15 if len(stem)<5 else 13); font.setBold(True)
    painter.setFont(font); painter.setPen(ink)
    label={'unknown':'?','zero':'0','jpeg':'JPG'}.get(stem,stem.upper())
    painter.drawText(QRectF(12,77,104,27),Qt.AlignmentFlag.AlignCenter,label); painter.end()
    return image


def previews(inventory):
    from PIL import Image,ImageDraw,ImageFont
    regular=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
    title=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',40)
    names=[('add_book','Add books'),('metadata','Metadata'),('convert','Convert'),('view','Read'),('send','Send'),
        ('save','Save'),('news','News'),('connect_share','Share'),('remove_books','Remove'),('config','Preferences'),
        ('edit_book','Edit book'),('polish','Polish'),('library','Library'),('search','Search'),('tags','Tags'),
        ('series','Series'),('catalog','Catalog'),('store','Store'),('user_profile','Authors'),('plugins','Plugins')]
    for mode,bg,fg,muted,line in [('light','#f2f0e5','#49463e','#878174','#ddd9cb'),('dark','#26272b','#e6dfce','#b1a99a','#424247')]:
        canvas=Image.new('RGB',(1200,890),bg); d=ImageDraw.Draw(canvas)
        d.text((48,32),'Tovu Pencil',font=title,fill=fg)
        d.text((50,95),'Pencil strokes. A quieter library.  /  Hand-drawn icons for Calibre',font=regular,fill=muted)
        d.line((48,133,1152,133),fill=line,width=1)
        for i,(name,label) in enumerate(names):
            x=48+(i%5)*224; y=151+(i//5)*164
            icon=Image.open(PENCIL/'theme'/f'{name}-for-{mode}-theme.png').convert('RGBA')
            canvas.paste(icon,(x+40,y),icon)
            box=d.textbbox((0,0),label,font=regular)
            d.text((x+104-(box[2]-box[0])/2,y+125),label,font=regular,fill=fg)
        d.line((48,824,1152,824),fill=line,width=1)
        d.text((50,846),'Graphite grain · Soft sketch contours · Cross-hatched shading · Transparent light and dark artwork',font=small,fill=muted)
        canvas.save(PENCIL/'previews'/f'{mode}.png')
    Image.open(PENCIL/'previews/light.png').resize((680,504),Image.Resampling.LANCZOS).save(PENCIL/'previews/cover.jpg',quality=92)
    cols=10; rows=(len(inventory)+cols-1)//cols; cell=120
    canvas=Image.new('RGB',(cols*cell,rows*112),'#f2f0e5'); d=ImageDraw.Draw(canvas)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',11)
    for i,name in enumerate(inventory):
        x=i%cols*cell; y=i//cols*112
        icon=Image.open(PENCIL/'theme'/name).convert('RGBA'); icon.thumbnail((70,70))
        canvas.paste(icon,(x+25,y),icon)
        for row in range(2):
            label=Path(name).stem[row*18:(row+1)*18]
            box=d.textbbox((0,0),label,font=small)
            d.text((x+(cell-box[2])/2,y+73+row*14),label,font=small,fill='#605a4e')
    canvas.save(PENCIL/'previews/all-icons.png')


def build():
    from qt.core import QApplication
    app=QApplication.instance() or QApplication([])
    inventory=json.loads((SRC/'tools/inventory.json').read_text()); originals=atlas_icons(); hashes={}
    for mode in ('light','dark'):
        icons={name:graphite(image,mode) for name,image in originals.items()}
        for name in inventory:
            image=fit_icon(resource(name,icons,mode))
            rel=str(Path(name).with_suffix(''))+f'-for-{mode}-theme.png'
            target=PENCIL/'theme'/rel; target.parent.mkdir(parents=True,exist_ok=True)
            if not image.save(str(target)): raise OSError(f'Cannot save {target}')
            hashes[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
            if mode=='light':
                base=PENCIL/'theme'/name; base.write_bytes(target.read_bytes()); hashes[name]=hashes[rel]
    metadata={'name':'tovu_pencil','title':'Tovu Pencil','author':'Tovu Calibre Themes','version':1,
        'description':'Graphite pencil drawings with softly repeated contours, visible grain and cross-hatched shading. Transparent warm graphite on light backgrounds and pale graphite on dark backgrounds.',
        'license':'See bundled artwork provenance','color_palette':'any','number':len(inventory)}
    meta=PENCIL/'theme/metadata.json'; meta.write_text(json.dumps(metadata,indent=2)+'\n'); hashes['metadata.json']=hashlib.sha256(meta.read_bytes()).hexdigest()
    previews(inventory)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
        for name in sorted(hashes):
            if name.endswith('.png'): z.writestr(name,(PENCIL/'theme'/name).read_bytes())
    archive=PENCIL/'tovu-pencil-theme.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
        z.write(meta,'tovu_pencil/metadata.json'); z.write(PENCIL/'previews/cover.jpg','tovu_pencil/icon-theme-cover.jpg')
        z.writestr('tovu_pencil/icons.zip.xz',lzma.compress(buf.getvalue()))
    manifest={'version':1,'icons':len(inventory),'files':hashes,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (PENCIL/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Tovu Pencil: {len(originals)} original pencil pictograms, {len(inventory)} native names, 735 PNGs and native ZIP ready.')


if __name__=='__main__':
    build()

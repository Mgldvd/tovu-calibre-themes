#!/usr/bin/env python3
"""Package original colorful vinyl sticker artwork as a Calibre icon theme."""
import hashlib
import io
import json
import lzma
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STICKERS=ROOT/'themes/stickers'
sys.path.insert(0,str(ROOT/'tools'))
from icon_sizing import fit_icon
from build_pencil import atlas_icons
from build_clay import resource as mapped_resource

FILE_COLORS={
    'epub':'#2ebd9d','kepub':'#2ebd9d','mobi':'#25aaa8','pdf':'#f36c79',
    'docx':'#9b74d5','odt':'#9b74d5','rtf':'#ed8c65','txt':'#25aaa8',
    'png':'#f28aab','jpeg':'#f28aab','gif':'#f28aab','svg':'#a880d8',
    'zip':'#f3c53d','rar':'#f3c53d','azw2':'#f3c53d','azw3':'#f3c53d',
}


def resource(name,icons):
    from qt.core import QPainter,QColor,QFont,QPen,QRectF,Qt
    path=Path(name); stem=path.stem
    if path.parent.as_posix()!='mimetypes' or stem in {'computer','dir'}:
        return mapped_resource(name,icons)
    image=icons['file'].copy(); painter=QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect=QRectF(8,78,112,28)
    painter.setBrush(QColor('white')); painter.setPen(QPen(QColor('white'),8))
    painter.drawRoundedRect(rect,7,7)
    painter.setBrush(QColor(FILE_COLORS.get(stem,'#b58cdd')))
    painter.setPen(QPen(QColor('#252042'),2.5)); painter.drawRoundedRect(rect,7,7)
    # Match the tiny vinyl highlights in the generated sticker artwork.
    painter.setPen(QPen(QColor('#ffffff'),1.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
    painter.drawLine(15,82,25,82)
    font=QFont('DejaVu Sans'); font.setPixelSize(14 if len(stem)<5 else 12); font.setBold(True)
    painter.setFont(font); painter.setPen(QColor('#252042'))
    label={'unknown':'?','zero':'0','jpeg':'JPG'}.get(stem,stem.upper())
    painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,label); painter.end()
    return image


def previews(inventory):
    from PIL import Image,ImageDraw,ImageFont
    base='/usr/share/fonts/truetype/dejavu/'
    title=ImageFont.truetype(base+'DejaVuSans-Bold.ttf',40)
    regular=ImageFont.truetype(base+'DejaVuSans.ttf',17); small=ImageFont.truetype(base+'DejaVuSans.ttf',12)
    names=[('add_book','Add books'),('metadata','Metadata'),('convert','Convert'),('view','Read'),('send','Send'),
        ('save','Save'),('news','News'),('connect_share','Share'),('remove_books','Remove'),('config','Preferences'),
        ('edit_book','Edit book'),('polish','Polish'),('library','Library'),('search','Search'),('tags','Tags'),
        ('series','Series'),('catalog','Catalog'),('store','Store'),('user_profile','Authors'),('plugins','Plugins')]
    for mode,bg,fg,muted in [('light','#f1edf8','#3a2c54','#837593'),('dark','#252135','#f7edff','#c0afd2')]:
        canvas=Image.new('RGB',(1200,890),bg); d=ImageDraw.Draw(canvas)
        d.text((48,32),'Tovu Stickers',font=title,fill=fg)
        d.text((50,95),'A little color. A little personality.  /  Die-cut icons for Calibre',font=regular,fill=muted)
        for i,(name,label) in enumerate(names):
            x=48+(i%5)*224; y=151+(i//5)*164
            icon=Image.open(STICKERS/'theme'/f'{name}.png').convert('RGBA')
            canvas.paste(icon,(x+40,y),icon)
            box=d.textbbox((0,0),label,font=regular)
            d.text((x+104-(box[2]-box[0])/2,y+125),label,font=regular,fill=fg)
        d.text((50,846),'Bright illustrated stickers · White die-cut edges · Soft shadows · Transparent artwork',font=small,fill=muted)
        canvas.save(STICKERS/'previews'/f'{mode}.png')
    Image.open(STICKERS/'previews/light.png').resize((680,504),Image.Resampling.LANCZOS).save(STICKERS/'previews/cover.jpg',quality=92)
    cols=10; rows=(len(inventory)+cols-1)//cols; cell=120
    canvas=Image.new('RGB',(cols*cell,rows*112),'#f1edf8'); d=ImageDraw.Draw(canvas)
    small=ImageFont.truetype(base+'DejaVuSans.ttf',11)
    for i,name in enumerate(inventory):
        x=i%cols*cell; y=i//cols*112
        icon=Image.open(STICKERS/'theme'/name).convert('RGBA'); icon.thumbnail((70,70))
        canvas.paste(icon,(x+25,y),icon)
        for row in range(2):
            label=Path(name).stem[row*18:(row+1)*18]
            box=d.textbbox((0,0),label,font=small)
            d.text((x+(cell-box[2])/2,y+73+row*14),label,font=small,fill='#54416c')
    canvas.save(STICKERS/'previews/all-icons.png')


def build():
    from qt.core import QApplication
    app=QApplication.instance() or QApplication([])
    inventory=json.loads((ROOT/'tools/inventory.json').read_text())
    icons=atlas_icons(STICKERS); hashes={}
    for name in inventory:
        image=fit_icon(resource(name,icons))
        for suffix in ('','-for-light-theme','-for-dark-theme'):
            rel=str(Path(name).with_suffix(''))+suffix+'.png'
            target=STICKERS/'theme'/rel; target.parent.mkdir(parents=True,exist_ok=True)
            if not image.save(str(target)): raise OSError(f'Cannot save {target}')
            hashes[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
    metadata={'name':'tovu_stickers','title':'Tovu Stickers','author':'Tovu Calibre Themes','version':1,
        'description':'Colorful illustrated die-cut stickers with bold dark outlines, thick white edges, small highlights and soft shadows. Transparent artwork for light and dark backgrounds.',
        'license':'See bundled artwork provenance','color_palette':'any','number':len(inventory)}
    meta=STICKERS/'theme/metadata.json'; meta.write_text(json.dumps(metadata,indent=2)+'\n'); hashes['metadata.json']=hashlib.sha256(meta.read_bytes()).hexdigest()
    previews(inventory)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
        for name in sorted(hashes):
            if name.endswith('.png'): z.writestr(name,(STICKERS/'theme'/name).read_bytes())
    archive=STICKERS/'tovu-stickers-theme.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
        z.write(meta,'tovu_stickers/metadata.json'); z.write(STICKERS/'previews/cover.jpg','tovu_stickers/icon-theme-cover.jpg')
        z.writestr('tovu_stickers/icons.zip.xz',lzma.compress(buf.getvalue()))
    manifest={'version':1,'icons':len(inventory),'files':hashes,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (STICKERS/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Tovu Stickers: {len(icons)} original sticker pictograms, {len(inventory)} native names, 735 PNGs and native ZIP ready.')


if __name__=='__main__':
    build()

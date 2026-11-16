#!/usr/bin/env python3
"""Build Tovu Sky from editable vectors, using the supplied style reference."""
import hashlib
import io
import json
import lzma
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'src'
SKY=ROOT/'themes/sky'
sys.path.insert(0,str(SRC/'tools'))
from build_theme import svg_icon as line_svg

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
# Each family has its own outline and gradient. Equal visual weight and shared
# geometry keep the pack cohesive without making blue the dominant color.
FAMILIES={
    'mint': {'light':('#307b55','#ebf9dc','#a5dfb4'), 'dark':('#b4edc5','#294b37','#427958')},
    'teal': {'light':('#237f86','#e2faf3','#98dfd5'), 'dark':('#a2e8df','#254b48','#397d75')},
    'coral': {'light':('#b75f4d','#fff1df','#ffc1ac'), 'dark':('#ffc2ad','#57392f','#8c5a49')},
    'rose': {'light':('#b24e6b','#ffeaf0','#f2afc7'), 'dark':('#f5b8d0','#532e42','#834c67')},
    'violet': {'light':('#8057a7','#f5eaff','#d1b7ed'), 'dark':('#ddc1f5','#473555','#725587')},
    'amber': {'light':('#a16a1d','#fff5ce','#f3d28e'), 'dark':('#f5d68f','#51452c','#7e6840')},
    'indigo': {'light':('#6267ac','#f0efff','#c4c7f2'), 'dark':('#c7cbfa','#343b57','#555e8a')},
}
COLOR_GROUPS={
    'mint':'add_book edit_book store ok dot_green drm-unlocked book bookmarks marked',
    'teal':'view viewer reader save search config filter tweak tweaks download-metadata connect_share_on',
    'coral':'send sync user_profile series donate edit_input modified',
    'rose':'remove_books trash dialog_error dot_red search_delete_saved',
    'violet':'metadata library bookshelf generic-library calibre apple-touch-icon favicon-192 favicon-512 plugins connect_share',
    'amber':'convert news tags rating polish ai beautify wizard heuristics dialog_warning drm-locked tb_folder document_open folder_saved_search',
    'indigo':'catalog books_in_series cover_flow layout column toc chapters',
}
EXPLICIT={name:family for family,names in COLOR_GROUPS.items() for name in names.split()}
FORMATS={
    'epub':'mint','kepub':'mint','mobi':'teal','azw2':'amber','azw3':'amber','kfx':'violet',
    'pdf':'rose','docx':'indigo','odt':'violet','rtf':'coral','txt':'teal',
    'png':'coral','jpeg':'coral','gif':'rose','bmp':'amber','svg':'violet',
    'zip':'amber','rar':'amber','cbr':'coral','cbz':'mint',
}


def palette_for(name,mode):
    path=Path(name); stem=path.stem
    if path.parent.as_posix()=='mimetypes':
        family=FORMATS.get(stem,'amber' if stem=='dir' else None)
    elif path.parent.as_posix()=='devices':
        family='amber' if stem=='folder' else 'indigo'
    elif path.parent.as_posix()=='plugins':
        family='rose' if 'invalid' in stem else 'amber' if 'deprecated' in stem else 'mint' if stem.endswith(('valid','ok')) else 'violet'
    else:
        family=EXPLICIT.get(stem)
    if family is None:
        # Stable across Python runs and additions to the icon inventory.
        family=tuple(FAMILIES)[int.from_bytes(hashlib.sha256(stem.encode()).digest()[:2],'big')%len(FAMILIES)]
    ink,start,end=FAMILIES[family][mode]
    return {'ink':ink,'start':start,'end':end,'opacity':'0.85' if mode=='light' else '0.75','family':family}
SILHOUETTES={
    'add_book':'M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z',
    'metadata':'M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z',
    'remove_books':'M5 6h14v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2Z',
    'trash':'M5 6h14v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2Z',
}


def svg_icon(name,mode):
    palette=palette_for(name,mode); stem=Path(name).stem
    node=ET.Element(f'{{{NS}}}svg',{'width':'128','height':'128','viewBox':'0 0 24 24'})
    defs=ET.SubElement(node,'defs')
    for ident,start,end in [('accent',palette['start'],palette['end'])]:
        grad=ET.SubElement(defs,'linearGradient',{'id':ident,'x1':'0%','y1':'0%','x2':'85%','y2':'100%'})
        ET.SubElement(grad,'stop',{'offset':'0','stop-color':start})
        ET.SubElement(grad,'stop',{'offset':'1','stop-color':end})
    if stem=='blank':
        return ET.tostring(node,encoding='unicode')
    if Path(name).parent.as_posix()=='mimetypes' and stem not in {'computer','dir'}:
        group=ET.SubElement(node,'g',{'stroke':palette['ink'],'stroke-width':'1.7','stroke-linecap':'round','stroke-linejoin':'round'})
        ET.SubElement(group,'path',{'d':'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z','fill':'url(#accent)','fill-opacity':palette['opacity']})
        ET.SubElement(group,'path',{'d':'M14 2v6h6','fill':'none'})
        ET.SubElement(group,'rect',{'x':'1','y':'12','width':'22','height':'7.5','rx':'2','fill':'url(#accent)'})
        label={'unknown':'?','zero':'0','jpeg':'JPG'}.get(stem,stem.upper())
        text=ET.SubElement(node,'text',{'x':'12','y':'17.3','text-anchor':'middle','font-family':'DejaVu Sans,sans-serif','font-size':'4.5','font-weight':'bold','fill':palette['ink']})
        text.text=label
        return ET.tostring(node,encoding='unicode')
    source=ET.fromstring(line_svg(name,mode))
    gradient='accent'
    # Color belongs beneath the contours, retaining their constant stroke.
    if stem in SILHOUETTES:
        ET.SubElement(node,'path',{'d':SILHOUETTES[stem],'fill':f'url(#{gradient})','fill-opacity':palette['opacity']})
    else:
        candidates=[]
        for child in source.iter():
            tag=child.tag.split('}')[-1]
            closed=tag in {'rect','polygon','ellipse'} or (tag=='circle' and float(child.get('r','0'))>1) or (tag=='path' and re.search(r'[zZ]\s*$',child.get('d','')))
            if closed:
                candidates.append(child)
        # A restrained wash in one enclosed shape; typography and navigation
        # remain clear outlines. Additional small forms keep their whitespace.
        if candidates:
            chosen=max(candidates,key=lambda child:len(child.get('d','')) if child.tag.endswith('path') else 30)
            fill=ET.fromstring(ET.tostring(chosen))
            fill.set('fill',f'url(#{gradient})'); fill.set('fill-opacity',palette['opacity']); fill.set('stroke','none')
            node.append(fill)
    outline=ET.SubElement(node,'g',{'stroke':palette['ink'],'stroke-width':'1.7','stroke-linecap':'round','stroke-linejoin':'round','fill':'none'})
    for child in list(source):
        for shape in child.iter():
            if 'fill' in shape.attrib and shape.get('fill')!='none':
                shape.set('fill',palette['ink'])
        outline.append(child)
    if stem in {'dot_green','dot_red'}:
        for shape in outline:
            shape.set('fill','url(#accent)')
    return ET.tostring(node,encoding='unicode')


def previews(inventory):
    from PIL import Image, ImageDraw, ImageFont
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title=ImageFont.truetype(font,40); regular=ImageFont.truetype(font,17); small=ImageFont.truetype(font,12)
    names=[('add_book','Add books'),('metadata','Metadata'),('convert','Convert'),('view','Read'),('send','Send'),
        ('save','Save'),('news','News'),('connect_share','Share'),('remove_books','Remove'),('config','Preferences'),
        ('edit_book','Edit book'),('polish','Polish'),('library','Library'),('search','Search'),('tags','Tags'),
        ('series','Series'),('catalog','Catalog'),('store','Store'),('user_profile','Authors'),('plugins','Plugins')]
    for mode,bg,fg,muted,card in [('light','#f8f8f5','#3c4552','#78808b','#ffffff'),('dark','#20222b','#eceaf2','#b5afbf','#2a2d38')]:
        canvas=Image.new('RGB',(1200,860),bg); d=ImageDraw.Draw(canvas)
        d.text((48,32),'Tovu Sky',font=title,fill=fg)
        d.text((50,92),'Clear outlines. More color.  /  Icons for Calibre',font=regular,fill=muted)
        # Every cell has identical dimensions, icon size and padding.
        for i,(name,label) in enumerate(names):
            x=48+(i%5)*224; y=143+(i//5)*162
            d.rounded_rectangle((x,y,x+208,y+146),radius=18,fill=card)
            icon=Image.open(SKY/'theme'/f'{name}-for-{mode}-theme.png').convert('RGBA')
            icon=icon.resize((76,76),Image.Resampling.LANCZOS)
            canvas.paste(icon,(x+66,y+18),icon)
            box=d.textbbox((0,0),label,font=regular)
            d.text((x+104-(box[2]-box[0])/2,y+108),label,font=regular,fill=fg)
        d.text((50,816),'Mint · Teal · Coral · Rose · Violet · Amber · Indigo / Soft gradients · Light and dark modes',font=small,fill=muted)
        canvas.save(SKY/'previews'/f'{mode}.png')
    Image.open(SKY/'previews/light.png').resize((680,487),Image.Resampling.LANCZOS).save(SKY/'previews/cover.jpg',quality=92)
    cols=10; rows=(len(inventory)+cols-1)//cols; cell=120
    sheet=Image.new('RGB',(cols*cell,rows*110),'#f8f8f5'); d=ImageDraw.Draw(sheet)
    for i,name in enumerate(inventory):
        x=i%cols*cell; y=i//cols*110
        icon=Image.open(SKY/'theme'/name).convert('RGBA'); icon.thumbnail((60,60))
        sheet.paste(icon,(x+30,y+4),icon)
        for row in range(2):
            label=Path(name).stem[row*18:(row+1)*18]
            box=d.textbbox((0,0),label,font=small)
            d.text((x+(cell-box[2])/2,y+69+row*15),label,font=small,fill='#3c4552')
    sheet.save(SKY/'previews/all-icons.png')


def build():
    from qt.core import QImage,QPainter,QRectF,Qt,QSvgRenderer,QApplication
    app=QApplication.instance() or QApplication([])
    inventory=json.loads((SRC/'tools/inventory.json').read_text()); hashes={}
    for name in inventory:
        for mode in ('light','dark'):
            svg=svg_icon(name,mode)
            vector=SKY/'svg'/mode/Path(name).with_suffix('.svg'); vector.parent.mkdir(parents=True,exist_ok=True); vector.write_text(svg)
            image=QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied); image.fill(Qt.GlobalColor.transparent)
            painter=QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer=QSvgRenderer(svg.encode())
            if not renderer.isValid(): raise ValueError(f'Invalid SVG: {name}')
            renderer.render(painter,QRectF(0,0,128,128)); painter.end()
            rel=str(Path(name).with_suffix(''))+f'-for-{mode}-theme.png'
            target=SKY/'theme'/rel; target.parent.mkdir(parents=True,exist_ok=True)
            if not image.save(str(target)): raise OSError(f'Cannot save {target}')
            hashes[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
            if mode=='light':
                base=SKY/'theme'/name; base.write_bytes(target.read_bytes()); hashes[name]=hashes[rel]
    metadata={'name':'tovu_sky','title':'Tovu Sky','author':'Tovu Calibre Themes · Lucide contributors','version':2,
        'description':'Colorful clean outlines and minimal gradient fills in mint, teal, coral, rose, violet, amber and indigo. Consistent 1.7-unit strokes, rounded curves and equal padding. Light and dark variants.',
        'license':'ISC / MIT','color_palette':'any','number':len(inventory)}
    meta=SKY/'theme/metadata.json'; meta.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n'); hashes['metadata.json']=hashlib.sha256(meta.read_bytes()).hexdigest()
    previews(inventory)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
        for name in sorted(hashes):
            if name.endswith('.png'): z.writestr(name,(SKY/'theme'/name).read_bytes())
    archive=SKY/'tovu-sky-theme.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
        z.write(meta,'tovu_sky/metadata.json'); z.write(SKY/'previews/cover.jpg','tovu_sky/icon-theme-cover.jpg')
        z.writestr('tovu_sky/icons.zip.xz',lzma.compress(buf.getvalue()))
    manifest={'version':1,'icons':len(inventory),'files':hashes,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (SKY/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(f'Tovu Sky: {len(inventory)} native names, 490 editable SVGs, 735 PNGs and native theme ZIP ready.')


if __name__=='__main__':
    build()

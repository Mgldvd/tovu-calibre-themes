#!/usr/bin/env python3
"""Create portable English previews with theme and palette selectors."""
import base64
import html
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def build():
    spec=importlib.util.spec_from_file_location('tovu_installer',ROOT/'installer.py')
    installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
    themes=installer.THEMES; default=installer.DEFAULT_THEME
    page='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tovu Calibre Themes</title><style>
:root{color-scheme:light dark}*{box-sizing:border-box}html,body{margin:0;font-family:var(--font-sans,system-ui);color:var(--foreground,inherit)}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px;align-items:center}.modes{display:flex;gap:6px;margin-left:auto}
button{font:inherit;font-size:13px;padding:8px 13px;border:1px solid var(--border,currentColor);border-radius:var(--radius,8px);background:var(--secondary,transparent);color:var(--secondary-foreground,inherit);cursor:pointer}
button[aria-pressed="true"]{background:var(--primary,teal);color:var(--primary-foreground,white);border-color:transparent}
button:focus-visible{outline:2px solid var(--ring,currentColor);outline-offset:3px}
img{width:100%;height:auto;display:block;border-radius:var(--radius,12px)}[hidden]{display:none!important}
.caption{font-size:12px;color:var(--muted-foreground,inherit);margin:10px 0 0}
</style><div class="controls" aria-label="Theme preview controls">
'''
    for key,theme in themes.items():
        pressed='true' if key==default else 'false'
        page+=f'<button data-theme="{key}" aria-pressed="{pressed}">{html.escape(theme["title"])}</button>'
    page+='<div class="modes"><button data-mode="light" aria-pressed="true">Light</button><button data-mode="dark" aria-pressed="false">Dark</button></div></div>'
    for theme,details in themes.items():
        folder=details['root']
        for mode in ('light','dark'):
            data=base64.b64encode((folder/'previews'/f'{mode}.png').read_bytes()).decode()
            hidden='' if (theme,mode)==(default,'light') else ' hidden'
            page+=f'<img id="{theme}-{mode}"{hidden} alt="Tovu {theme.title()} icons on a {mode} background" src="data:image/png;base64,{data}">'
    page+='''<p class="caption">245 native icon names per theme · Transparent PNGs · Reversible installation</p>
<script>/*STATE*/function update(){for(const t of themeIds)for(const m of ['light','dark'])document.getElementById(t+'-'+m).hidden=t!==theme||m!==mode;for(const b of document.querySelectorAll('[data-theme]'))b.setAttribute('aria-pressed',String(b.dataset.theme===theme));for(const b of document.querySelectorAll('[data-mode]'))b.setAttribute('aria-pressed',String(b.dataset.mode===mode));}for(const b of document.querySelectorAll('[data-theme]'))b.onclick=()=>{theme=b.dataset.theme;update()};for(const b of document.querySelectorAll('[data-mode]'))b.onclick=()=>{mode=b.dataset.mode;update()};</script></html>'''
    page=page.replace('/*STATE*/',f'const themeIds={json.dumps(list(themes))};let theme={json.dumps(default)},mode="light";')
    for p in [details['root']/'previews/preview.html' for details in themes.values()]:
        p.write_text(page)
    print('English preview galleries built for '+', '.join(theme['title'] for theme in themes.values())+'.')


if __name__=='__main__':
    build()

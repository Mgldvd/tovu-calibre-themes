#!/usr/bin/env python3
"""Integration checks. Writes only to temporary Calibre profiles."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def files(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob('*') if p.is_file() and not p.relative_to(root).as_posix().startswith(('tovu-backups/','calibra-backups/'))}


def check():
    with tempfile.TemporaryDirectory(prefix='tovu-check-') as d:
        profile=Path(d)/'profile with spaces'; profile.mkdir()
        env={**os.environ,'CALIBRE_CONFIG_DIRECTORY':str(profile),'QT_QPA_PLATFORM':'offscreen'}
        # Calibre's GUI mutex is shared across profiles. Give the test processes
        # their own real mutex namespace so the user's open Calibre stays open.
        namespace='TovuTest-'+uuid.uuid4().hex[:12]+'-'
        runner=Path(d)/'isolated_runner.py'
        runner.write_text('import runpy,sys\nimport calibre.utils.lock as lock\noriginal=lock.SingleInstance\n'
            +f'lock.SingleInstance=lambda name: original({namespace!r}+name)\n'
            +f'sys.argv=[{str(ROOT/"installer.py")!r}]+sys.argv[1:]\n'
            +f'runpy.run_path({str(ROOT/"installer.py")!r},run_name="__main__")\n')
        def command(args, success=True, extra_env=None):
            result=subprocess.run(args,env={**env,**(extra_env or {})},text=True,capture_output=True,timeout=45)
            if (result.returncode==0) != success:
                raise AssertionError(f'{args}\n{result.stdout}\n{result.stderr}')
            return result.stdout+result.stderr
        def installer(*args,success=True,theme='line'):
            return command(['calibre-debug','-e',str(runner),'--',*args,'--theme',theme,'--config-dir',str(profile)],success)
        # Exercise the real shell launcher's argument forwarding separately.
        assert '"installed": false' in command([str(ROOT/'install-linux.sh'),'--status','--config-dir',str(profile)])
        # The macOS launcher is plain bash, so its lookup and forwarding run here too.
        assert '"installed": false' in command(['bash',str(ROOT/'install-mac.command'),f'--config-dir={profile}','--status'])
        for name,data in {
            'icons-any.rcc':b'previous any theme','icons-light.rcc':b'previous light theme',
            'icons-dark.rcc':b'previous dark theme',
            'resources/images/add_book.png':b'custom toolbar override',
            'resources/images/mimetypes/epub-for-dark-theme.png':b'custom nested override',
            'resources/images/icon-theme.json':b'{"title":"legacy"}',
            'resources/images/textures/custom.png':b'keep texture',
            'resources/images/plugins/unrelated.png':b'keep plugin override',
            'gui.json':b'{"personal":"unchanged"}',
        }.items():
            p=profile/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
        before=files(profile)
        # Calibre's bootstrap creates its default global.py.json in a new
        # profile. Status must preserve every file already present.
        assert '"installed": false' in installer('--status')
        for name,value in before.items():
            assert files(profile).get(name)==value
        print(installer('--install').strip())
        assert (profile/'icons-any.rcc').stat().st_size>100000
        assert not (profile/'icons-dark.rcc').exists()
        assert not (profile/'resources/images/add_book.png').exists()
        assert not (profile/'resources/images/mimetypes/epub-for-dark-theme.png').exists()
        assert not (profile/'resources/images/icon-theme.json').exists()
        assert (profile/'resources/images/textures/custom.png').read_bytes()==b'keep texture'
        assert (profile/'resources/images/plugins/unrelated.png').read_bytes()==b'keep plugin override'
        state=(profile/'tovu-state.json').read_bytes()
        assert (profile/'gui.json').read_bytes()==b'{"personal":"unchanged"}', 'installer changed preferences'
        print(installer('--install').strip())
        assert (profile/'tovu-state.json').read_bytes()==state
        # Calibre's GUI module can rewrite its own preferences at exit. Check
        # native lookups on a copy so its bootstrap is outside installer QA.
        native=Path(d)/'native-lookup'; shutil.copytree(profile,native)
        print(command(['calibre-debug','-e',str(ROOT/'tools/check_native_theme.py')],extra_env={'CALIBRE_CONFIG_DIRECTORY':str(native)}).strip())
        original_backup=json.loads(state)['backup']
        # Switching must keep the pre-Tovu theme, including its overrides.
        for theme in ('clay','sky','pencil','pencil-color','pencil','stickers','line','stickers'):
            print(installer('--install',theme=theme).strip())
            active=json.loads((profile/'tovu-state.json').read_text())
            assert active['theme_id']==theme
            assert active['backup']==original_backup
            assert active['previous']==json.loads(state)['previous']
            lookup=Path(d)/('lookup-'+theme)
            if lookup.exists(): shutil.rmtree(lookup)
            shutil.copytree(profile,lookup)
            print(command(['calibre-debug','-e',str(ROOT/'tools/check_native_theme.py')],
                extra_env={'CALIBRE_CONFIG_DIRECTORY':str(lookup),'TOVU_TEST_THEME':theme}).strip())
        state=(profile/'tovu-state.json').read_bytes()
        # Restore must refuse an incomplete backup without deleting the theme.
        s=json.loads(state); saved=profile/s['backup']/'icons-dark.rcc'; original=saved.read_bytes()
        saved.write_bytes(b'corrupted')
        unchanged=files(profile)
        assert 'damaged' in installer('--uninstall',success=False)
        assert files(profile)==unchanged
        saved.write_bytes(original)
        # Changes made after install are retained in a separate recovery folder.
        (profile/'icons-light.rcc').write_bytes(b'later user theme')
        (profile/'resources/images/add_book.png').write_bytes(b'later icon override')
        print(installer('--uninstall').strip())
        # Application may have created auxiliary settings while loading Qt; the
        # original files themselves must all be restored byte for byte.
        after=files(profile)
        for name,value in before.items():
            assert after.get(name)==value,(name,'not restored')
        assert not (profile/'tovu-state.json').exists()
        assert any(p.read_bytes()==b'later user theme' for p in (profile/'tovu-backups').rglob('icons-light.rcc'))
        assert 'is not installed' in installer('--uninstall')
        print('Backup, repeat install, nested overrides, damaged backup, later edits and restore: OK')

        # Restore Calibre's own icons: every theme file goes to a backup, the
        # pre-Tovu theme stays restorable and unrelated resources stay put.
        print(installer('--install',theme='stickers').strip())
        print(installer('--restore-default').strip())
        icon_files=['icons-any.rcc','icons-light.rcc','icons-dark.rcc','resources/images/add_book.png',
            'resources/images/mimetypes/epub-for-dark-theme.png','resources/images/icon-theme.json']
        assert not any((profile/n).exists() for n in icon_files)
        assert (profile/'resources/images/textures/custom.png').read_bytes()==b'keep texture'
        assert (profile/'resources/images/plugins/unrelated.png').read_bytes()==b'keep plugin override'
        assert (profile/'gui.json').read_bytes()==b'{"personal":"unchanged"}'
        assert (profile/'tovu-state.json').exists(), 'restore default dropped the previous theme'
        assert '"icons": "Calibre default icons"' in installer('--status')
        assert any(p.stat().st_size>100000 for p in (profile/'tovu-backups').glob('*-before-default/icons-any.rcc'))
        assert 'already using its default icons' in installer('--restore-default')
        print(installer('--uninstall').strip())
        after=files(profile)
        for name,value in before.items():
            assert after.get(name)==value,(name,'not restored after default')
        print(installer('--restore-default').strip())
        assert not any((profile/n).exists() for n in icon_files)
        assert not (profile/'tovu-state.json').exists()
        print('Restore Calibre default icons, then previous theme: OK')

        # Upgrading from the Calibra-era installer: its state file and backup
        # folder must still restore the theme the user had before.
        legacy=Path(d)/'legacy'; legacy.mkdir()
        profile=legacy
        env['CALIBRE_CONFIG_DIRECTORY']=str(legacy)
        (legacy/'icons-any.rcc').write_bytes(b'theme from before calibra')
        print(installer('--install',theme='stickers').strip())
        s=json.loads((legacy/'tovu-state.json').read_text())
        (legacy/'tovu-backups').rename(legacy/'calibra-backups')
        s['backup']=s['backup'].replace('tovu-backups/','calibra-backups/',1); s['title']='Calibra Stickers'
        (legacy/'calibra-state.json').write_text(json.dumps(s)); (legacy/'tovu-state.json').unlink()
        status=installer('--status')
        assert '"icons": "Tovu Stickers"' in status, status
        print(installer('--install',theme='clay').strip())
        assert not (legacy/'calibra-state.json').exists(), 'legacy state file not migrated'
        migrated=json.loads((legacy/'tovu-state.json').read_text())
        assert migrated['theme_id']=='clay' and migrated['backup'].startswith('calibra-backups/')
        print(installer('--uninstall').strip())
        assert (legacy/'icons-any.rcc').read_bytes()==b'theme from before calibra'
        assert not (legacy/'tovu-state.json').exists()
        print('Upgrade from Calibra-era state and backups: OK')

        # Empty profile and graphical installer lifecycle.
        clean=Path(d)/'clean'; clean.mkdir()
        profile=clean
        env['CALIBRE_CONFIG_DIRECTORY']=str(clean)
        print(installer('--install').strip())
        print(installer('--uninstall').strip())
        assert not any((clean/n).exists() for n in ['icons-any.rcc','icons-light.rcc','icons-dark.rcc'])
        print(installer('--install').strip())
        print(installer('--restore-default').strip())
        assert not (clean/'tovu-state.json').exists(), 'state kept although the previous theme was the default'
        assert not any((clean/n).exists() for n in ['icons-any.rcc','icons-light.rcc','icons-dark.rcc'])
        for theme in ('line','clay','sky','pencil','pencil-color','stickers'):
            print(command(['calibre-debug','-e',str(runner),'--','--theme',theme,'--config-dir',str(clean)],extra_env={'TOVU_GUI_SMOKE_TEST':'1'}).strip())
        print(installer('--install').strip())
        for scheme in ('light','dark'):
            print(command(['calibre-debug','-e',str(ROOT/'tools/check_gui.py')],
                extra_env={'TOVU_GUI_PROFILE':str(clean),'TOVU_GUI_SCHEME':scheme}).strip())
        print('Clean install/restore and graphical Qt assistant: OK')

        # Hold Calibre's own GUI mutex and prove installation refuses to proceed.
        marker=Path(d)/'locked'
        lock_script=Path(d)/'hold_lock.py'
        lock_script.write_text('from calibre.utils.lock import SingleInstance\nfrom pathlib import Path\nimport sys\n'+f'with SingleInstance({namespace+"GUI"!r}) as held:\n assert held\n Path(sys.argv[-1]).write_text("ready")\n sys.stdin.read()\n')
        holder=subprocess.Popen(['calibre-debug','-e',str(lock_script),'--',str(marker)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            import time
            for attempt in range(100):
                if marker.exists(): break
                time.sleep(.02)
            assert marker.exists(),'lock process did not start'
            assert 'Close Calibre' in installer('--install',success=False)
        finally:
            holder.communicate(input=b'',timeout=10)
        print('Running-Calibre lock: OK')
    print('All checks passed. No user profile was modified.')


if __name__=='__main__':
    check()

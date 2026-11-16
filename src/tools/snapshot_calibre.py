#!/usr/bin/env python3
"""Screenshot the real Calibre main window with Tovu themes installed.

python3 tovu-calibre-themes/src/tools/snapshot_calibre.py

Each shot uses a throwaway profile and a sample library of public-domain
books, so your own Calibre profile and libraries are never read or changed.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/'src'
OUT = ROOT/'previews'
SCALE = '1.5'
SIZE = (1440, 860)
# (file name, theme, Calibre colour palette)
SHOTS = (
    ('calibre-stickers-light.png', 'stickers', 'light'),
    ('calibre-sky-dark.png', 'sky', 'dark'),
    ('calibre-clay-light.png', 'clay', 'light'),
    ('calibre-line-dark.png', 'line', 'dark'),
    ('calibre-pencil-light.png', 'pencil', 'light'),
    ('calibre-pencil-color-dark.png', 'pencil-color', 'dark'),
)
FEATURED = 'Frankenstein'
EXPANDED = ('Series', 'Formats')
BOOKS = (
    ('Pride and Prejudice', 'Jane Austen', 'Romance, Classics', None, 5),
    ('Moby-Dick', 'Herman Melville', 'Adventure, Classics', None, 4),
    ('Frankenstein', 'Mary Shelley', 'Gothic, Science Fiction', None, 5),
    ('The Adventures of Sherlock Holmes', 'Arthur Conan Doyle', 'Mystery', ('Sherlock Holmes', 3), 5),
    ('The Hound of the Baskervilles', 'Arthur Conan Doyle', 'Mystery', ('Sherlock Holmes', 5), 4),
    ("Alice's Adventures in Wonderland", 'Lewis Carroll', 'Fantasy, Classics', ('Alice', 1), 4),
    ('Through the Looking-Glass', 'Lewis Carroll', 'Fantasy, Classics', ('Alice', 2), 3),
    ('Dracula', 'Bram Stoker', 'Gothic, Horror', None, 4),
    ('The Time Machine', 'H. G. Wells', 'Science Fiction', None, 4),
    ('Little Women', 'Louisa May Alcott', 'Classics', None, 3),
    ('Jane Eyre', 'Charlotte Brontë', 'Romance, Gothic', None, 5),
    ('Treasure Island', 'Robert Louis Stevenson', 'Adventure', None, 4),
    ('Don Quixote', 'Miguel de Cervantes', 'Adventure, Classics', None, 5),
    ('The War of the Worlds', 'H. G. Wells', 'Science Fiction', None, 4),
)


def isolate_mutexes(namespace):
    # Calibre's GUI mutex is shared across profiles; use a private namespace so
    # an open Calibre session is left alone.
    import calibre.utils.lock as lock
    original = lock.SingleInstance
    lock.SingleInstance = lambda name: original(namespace+name)


def make_library(library):
    from io import BytesIO
    from calibre.ebooks.covers import generate_cover
    from calibre.ebooks.metadata.book.base import Metadata
    from calibre.library import db
    from qt.core import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841 (covers need Qt)
    api = db(library).new_api
    for index, (title, author, tags, series, rating) in enumerate(BOOKS):
        mi = Metadata(title, [author])
        mi.tags = [t.strip() for t in tags.split(',')]
        mi.rating = rating*2
        mi.languages = ['eng']
        mi.publisher = 'Public Domain'
        if series:
            mi.series, mi.series_index = series
        book_id = api.create_book_entry(mi, cover=generate_cover(mi))
        for fmt in ('EPUB', 'AZW3', 'PDF')[:1+index % 3]:
            api.add_format(book_id, fmt, BytesIO(b'Sample'), run_hooks=False)


def take_shot(library, out, palette):
    from calibre.gui2 import gprefs
    from calibre.utils.config import dynamic, prefs
    dynamic.set('welcome_wizard_was_run', True)
    gprefs['color_palette'] = palette
    gprefs['new_version_notification'] = False
    gprefs['quick_start_guide_added'] = True
    prefs['library_path'] = library
    from calibre.gui2 import ui
    from qt.core import QApplication, QTimer
    original = ui.Main.post_initialize_actions

    def post_initialize_actions(self):
        original(self)
        self.resize(*SIZE)
        view = self.library_view
        for column in ('timestamp', 'size', 'pubdate'):
            if column in view.column_map:
                view.hideColumn(view.column_map.index(column))
        view.sort_by_named_field('title', True)
        featured = self.current_db.new_api.search(f'title:"={FEATURED}"')
        QTimer.singleShot(800, lambda: view.select_rows(featured))

        def expand_categories():
            tags = self.tags_view
            model = tags.model()
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                if str(index.data() or '').startswith(EXPANDED):
                    tags.expand(index)
        QTimer.singleShot(1200, expand_categories)

        def grab():
            QApplication.processEvents()
            ok = self.grab().save(out)
            print(('Saved ' if ok else 'Could not save ')+out, flush=True)
            os._exit(0 if ok else 1)
        QTimer.singleShot(3000, grab)
    ui.Main.post_initialize_actions = post_initialize_actions
    from calibre.gui2.main import main
    main(['calibre', '--with-library', library])


def orchestrate():
    with tempfile.TemporaryDirectory(prefix='tovu-calibre-shot-') as tmp:
        tmp = Path(tmp)
        for name, theme, palette in SHOTS:
            profile, library = tmp/theme/'profile', tmp/theme/'Library'
            profile.mkdir(parents=True); library.mkdir()
            env = {**os.environ, 'CALIBRE_CONFIG_DIRECTORY':str(profile), 'QT_QPA_PLATFORM':'offscreen',
                'QT_SCALE_FACTOR':SCALE, 'TOVU_MUTEX':f'tovu-shot-{os.getpid()}-'}
            run = lambda *args: subprocess.run(['calibre-debug', '-e', __file__, '--', *args], env=env, check=True)
            run('library', str(library))
            subprocess.run([str(ROOT/'install-linux.sh'), '--install', '--theme', theme, '--config-dir', str(profile)],
                env=env, check=True, stdout=subprocess.DEVNULL)
            run('shot', str(library), str(OUT/name), palette)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--']
    if not args:
        orchestrate()
    else:
        isolate_mutexes(os.environ['TOVU_MUTEX'])
        if args[0] == 'library':
            make_library(args[1])
        else:
            take_shot(*args[1:])

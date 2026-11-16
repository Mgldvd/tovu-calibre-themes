# Tovu Stickers artwork

This pack was created for the project with the built-in `image_gen.imagegen` tool. Four transparent sheets contain 144 original illustrated sticker pictograms, all using the first sheet as their style reference. The artwork uses rounded forms, bright coral, jade, teal, yellow, lavender and pink fills, bold dark contours, thick white die-cut edges and gentle lower-right shadows.

The original generated atlases are preserved in `source/`. `source/prompts.json` records the exact prompts and tool used; `source/extraction.json` records each source cell and rectangle. The packaging code extracts complete stickers from their transparent cells and excludes fragments from adjacent cells, keeping the generated colors and white edges.

Each theme covers the bundled inventory of 245 native Calibre icon names. Related actions share appropriate pictograms. File formats have small, readable labels in white-edged colorful badges, and plugin states use generated sticker checkmarks, crosses and plus signs. Success and error indicators are also distinguished by their glyphs.

All icons are 128 × 128 transparent PNGs. The same colors and white sticker edge work on both light and dark backgrounds; base, light and dark resources are supplied for 735 PNG files. The previews use lilac or dark purple presentation backgrounds, which are not installed behind individual icons.

The bundle rebuilds offline with `calibre-debug -e tools/build_stickers.py` from the project folder. Installation and rebuilding require no image-generation API key or network access. The project scripts and original packaging contributions are provided under the root MIT license. Lucide artwork notices apply to the separate Line and Sky themes.

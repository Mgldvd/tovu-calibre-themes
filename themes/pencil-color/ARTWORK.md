# Tovu Pencil Color artwork

Pencil Color is a separate colored-pencil edition of Tovu Pencil. Its four source atlases were edited with the built-in `image_gen.imagegen` tool, using the corresponding original Pencil atlas as each edit target. The prompts request the same 144 pictograms, grid placement, repeated sketch contours, pencil grain and cross-hatched shading, with added teal, coral, green, ochre, blue and violet pigment. Paper details remain cream; backgrounds and holes are transparent.

Exact prompts are retained in `source/prompts.json`. The edited transparent atlases are in `source/01-library.png` through `source/04-details.png`; `source/extraction.json` records their extracted cells. The original graphite Pencil source atlases and installable package remain in `../pencil/`.

The offline builder isolates each cell, exports it at 128 × 128 pixels and maps the pictograms to all 245 native icon names. Dark artwork gently lifts the pigment colors without changing alpha or removing their texture. File-format labels use small hatched teal badges. Status icons retain checkmarks and crosses, with green and coral coloring. There are 735 PNG resources: base compatibility, light and dark variants.

Rebuild from the project root with `QT_QPA_PLATFORM=offscreen calibre-debug -e tovu-calibre-themes/tools/build_pencil_color.py`. Installation and rebuilding use the bundled assets and require no image-generation service or API key. Original project scripts and packaging are under the root MIT license. This theme is independent of the Lucide artwork used by Line and Sky.

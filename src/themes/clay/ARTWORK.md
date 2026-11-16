# Tovu Clay artwork

This pack was created for the project with the built-in `image_gen.imagegen` tool. No external image-generation API key is needed to install or rebuild it.

The original transparent output atlases are preserved in `source/`:

1. `01-library.png`: library and primary toolbar actions.
2. `02-tools.png`: editing, status and utility controls.
3. `03-navigation.png`: arrows, typography and alignment.
4. `04-details.png`: specialized tools, document actions and indicators.

Each atlas contains 36 pictograms. The first atlas supplied the style reference for the next three. `source/prompts.json` records the exact prompts and tool used. `source/extraction.json` records every pictogram's source cell and rectangle.

The packaging script selects the transparent cell contents, excludes neighboring cell fragments and preserves the generated material and lighting. It exports resources at 128 × 128 px with alpha. Related native actions reuse relevant pictograms. File formats receive readable format badges; plugin states receive clay status badges. The same pastel artwork is used in light and dark mode, with transparency allowing Calibre's own background to show through.

The generated clay artwork is distinct from the Lucide-based vector theme. The project scripts and original packaging additions are provided under the root MIT license. The Lucide notices apply to the Line theme's original and adapted vector artwork.

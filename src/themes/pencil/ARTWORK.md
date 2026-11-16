# Tovu Pencil artwork

The user-provided graphite bell in `source/style-reference.png` guides this theme's sketch contours, pencil grain and cross-hatched shading. That image is a style reference and is not installed as an icon or application background. No license is claimed for the supplied reference.

The actual artwork was created for this project with the built-in `image_gen.imagegen` tool. Four transparent sheets contain 144 original pencil pictograms. Their exact prompts are recorded in `source/prompts.json`, and `source/extraction.json` records each source cell and rectangle. The original atlases are retained unchanged.

The build process exports individual icons, isolates their transparent cell contents and transfers graphite density into alpha. Warm graphite is used on light backgrounds and pale graphite on dark backgrounds, preserving the original hatching and pressure grain. Related native actions share relevant pictograms. File format labels are added in small, lightly outlined badges, and plugin states use the generated pencil status symbols. Success and error indicators use checkmarks and crosses so their meaning survives the monochrome palette.

Each palette includes all 245 native Calibre icon names from the bundled inventory. Base compatibility resources are included as well, for 735 transparent PNGs at 128 × 128 pixels. At small toolbar sizes the drawing naturally appears softer; larger toolbar sizes show more of the pencil texture. There are no paper rectangles behind the installed icons.

The supplied assets allow rebuilding offline with `calibre-debug -e src/tools/build_pencil.py` from the project folder. No image-generation service or API key is required to install or rebuild. The project scripts and original packaging contributions are provided under the root MIT license. Lucide artwork notices apply to the separate Line and Sky themes.

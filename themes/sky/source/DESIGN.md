# Tovu Sky

The supplied `style-reference.png` guides the clean outlines, gentle gradients and equally spaced presentation. Following the user's revision, version 2 replaces the predominantly blue palette with seven coordinated color families: mint, teal, coral, rose, violet, amber and indigo. Its weather subjects are translated into Calibre's existing library and editing actions; the reference itself is not installed as application artwork.

The icon geometry adapts the bundled Lucide 1.73.0 vector sources. Original ISC and MIT notices are in `../../../vendor/lucide/LICENSE`. The supplied reference remains a user-provided reference, with no license claimed for that image.

- Consistent 1.7-unit strokes, rounded caps and rounded joins.
- A shared 28-unit view box with equal outer padding.
- A colored outline and matching gentle gradient for each icon, with lighter variants for dark backgrounds.
- One subtle gradient wash in a selected enclosed form, leaving other details open.
- Stable color assignments across rebuilds; rose for destructive/error actions, mint for success and amber for warnings.
- Transparent 128 × 128 PNG resources, plus editable light and dark SVGs.
- Native format badges and preserved status meanings.

The installer uses the ready-made native theme package. Rebuild entirely offline with `calibre-debug -e tools/build_sky.py` from the project folder. No image-generation service or API key is used for Sky.

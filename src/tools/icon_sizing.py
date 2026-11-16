"""Fit raster artwork into a consistent 128-pixel Calibre icon canvas."""


def fit_icon(image):
    from qt.core import QImage, QPainter, Qt

    # Ignore nearly invisible edge pixels when measuring; retain a small
    # allowance for antialiasing and shadows around the visible artwork.
    points = [(x, y) for y in range(image.height()) for x in range(image.width())
              if image.pixelColor(x, y).alpha() > 8]
    if not points:
        return image  # The intentionally empty icon stays empty.
    left = max(0, min(x for x, y in points) - 2)
    top = max(0, min(y for x, y in points) - 2)
    right = min(image.width(), max(x for x, y in points) + 3)
    bottom = min(image.height(), max(y for x, y in points) + 3)
    tile = image.copy(left, top, right-left, bottom-top)
    tile = tile.scaled(116, 116, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    output = QImage(128, 128, QImage.Format.Format_ARGB32_Premultiplied)
    output.fill(Qt.GlobalColor.transparent)
    painter = QPainter(output)
    painter.drawImage((128-tile.width())//2, (128-tile.height())//2, tile)
    painter.end()
    return output

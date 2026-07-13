"""Synthetic test invoice images for OCR tests — not real invoices.
Generates a clean, legible invoice image and a deliberately degraded one.
"""
import io
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_TEXTO_FACTURA = [
    "FACTURA",
    "Emisor NIF: 12345678Z",
    "Fecha: 15/03/2026",
    "Base imponible: 100.00 EUR",
    "Tipo IVA: 21%",
    "Cuota IVA: 21.00 EUR",
    "Total: 121.00 EUR",
]


def crear_imagen_factura_clara() -> bytes:
    img = Image.new("RGB", (600, 400), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=24)
    y = 20
    for linea in _TEXTO_FACTURA:
        draw.text((30, y), linea, fill="black", font=font)
        y += 45
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def crear_imagen_factura_baja_calidad() -> bytes:
    img = Image.new("RGB", (600, 400), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=8)  # tiny font
    y = 20
    for linea in _TEXTO_FACTURA:
        draw.text((30, y), linea, fill=(180, 180, 180), font=font)  # low contrast
        y += 45

    # Heavy noise overlay
    random.seed(42)
    pixels = img.load()
    for _ in range(40000):
        x = random.randint(0, 599)
        yy = random.randint(0, 399)
        pixels[x, yy] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    img = img.filter(ImageFilter.GaussianBlur(radius=3))
    # Downscale then upscale to destroy detail (pixelation)
    img = img.resize((60, 40)).resize((600, 400))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

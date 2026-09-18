"""Image preprocessing for OCR. Never destroys the original — saves a processed
copy next to it and returns both paths."""
import os
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

MAX_DIM = 2000

def preprocess(image_path: str, out_dir: str = "") -> dict:
    """Return {original, processed, width, height}. Raises on unreadable input."""
    im = Image.open(image_path)
    im = ImageOps.exif_transpose(im)
    w, h = im.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    gray = ImageOps.grayscale(im)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    gray = ImageEnhance.Contrast(gray).enhance(1.2)

    base = os.path.dirname(image_path)
    stem = os.path.splitext(os.path.basename(image_path))[0]
    proc_dir = os.path.join(os.path.dirname(base), "processed")
    os.makedirs(proc_dir, exist_ok=True)
    proc_path = os.path.join(proc_dir, f"{stem}_ocr.png")
    gray.save(proc_path)
    return {"original": image_path, "processed": proc_path,
            "width": gray.size[0], "height": gray.size[1]}

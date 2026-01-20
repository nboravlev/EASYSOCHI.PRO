from PIL import Image, ImageDraw
import os

INPUT_DIR = "static/images"
OUTPUT_DIR = "static/images/rounded"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(INPUT_DIR):
    if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
        continue

    path = os.path.join(INPUT_DIR, filename)
    img = Image.open(path).convert("RGBA")

    # создаём маску с прозрачными углами
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, *img.size), fill=255)

    img.putalpha(mask)
    img.save(os.path.join(OUTPUT_DIR, filename))
    print(f"✅ {filename}_r")

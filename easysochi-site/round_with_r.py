from PIL import Image, ImageDraw
import sys

def round_corners(image_path, output_path, radius=50):
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    # создаём маску
    mask = Image.new("L", img.size, 255)
    draw = ImageDraw.Draw(mask)

    # четыре угла
    draw.pieslice([0, 0, radius*2, radius*2], 180, 270, fill=0)
    draw.pieslice([width - radius*2, 0, width, radius*2], 270, 0, fill=0)
    draw.pieslice([0, height - radius*2, radius*2, height], 90, 180, fill=0)
    draw.pieslice([width - radius*2, height - radius*2, width, height], 0, 90, fill=0)

    # прямоугольники между углами
    draw.rectangle([radius, 0, width - radius, height], fill=0)
    draw.rectangle([0, radius, width, height - radius], fill=0)

    # инвертируем маску
    mask = Image.eval(mask, lambda p: 255 - p)

    # применяем альфу
    img.putalpha(mask)
    img.save(output_path, format="PNG")
    print(f"✅ Сохранено: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 round_with_r.py <входной_файл> <выходной_файл> [radius]")
        sys.exit(1)

    image_in = sys.argv[1]
    image_out = sys.argv[2]
    radius = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    round_corners(image_in, image_out, radius)

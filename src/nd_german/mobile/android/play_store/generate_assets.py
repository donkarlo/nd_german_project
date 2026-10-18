#!/usr/bin/env python3
"""Rebuild the two graphical Google Play assets from the NoonDreams source icon."""
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
OUT.mkdir(parents=True, exist_ok=True)
SRC_ICON = HERE.parents[4] / "assets" / "app_icon.svg"
if not SRC_ICON.exists():
    SRC_ICON = Path("/home/donkarlo/Dropbox/repo/nd_german_project/assets/app_icon.svg")
ICON = OUT / "store_icon_512.png"
FEATURE = OUT / "feature_graphic_1024x500.png"

subprocess.run(["convert", "-background", "none", "-density", "384", str(SRC_ICON),
                "-resize", "512x512", str(ICON)], check=True, capture_output=True)

W, H = 1024, 500
im = Image.new("RGB", (W, H))
pix = im.load()
for y in range(H):
    for x in range(W):
        t = 0.42 * (x / W) + 0.58 * (y / H)
        pix[x, y] = (int(29 + 58*t), int(20 + 46*t), int(71 + 98*t))
d = ImageDraw.Draw(im, "RGBA")
for cx, cy, r, col in [(900, 90, 275, (180, 149, 255, 30)),
                       (760, 510, 270, (114, 210, 237, 20)),
                       (10, 15, 205, (255, 255, 255, 11))]:
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=col)
for i in range(9):
    xx = 575 + i * 38
    d.line((xx, 0, xx + 110, H), fill=(255, 255, 255, 8), width=1)

reg = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
bold = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
font = lambda sz, is_bold=False: ImageFont.truetype(bold if is_bold else reg, sz)
d.text((70, 65), "NOONDREAMS", font=font(19, True), fill=(199, 189, 255, 255), stroke_width=0)
d.rounded_rectangle((68, 125, 124, 130), radius=2, fill=(142, 199, 249, 255))
d.text((66, 157), "German", font=font(65, True), fill=(255, 255, 255, 255))
d.text((66, 235), "Learning", font=font(65, True), fill=(255, 255, 255, 255))
d.text((70, 355), "Offline dictionary & grammar", font=font(24), fill=(230, 227, 252, 255))
d.text((70, 408), "DEUTSCH   ·   ENGLISH   ·   PERSIAN", font=font(16, True), fill=(180, 192, 251, 255))

# Dictionary-card illustration (not a screenshot of the app).
shadow = Image.new("RGBA", im.size)
s = ImageDraw.Draw(shadow)
s.rounded_rectangle((655, 70, 976, 444), radius=37, fill=(0, 0, 0, 155))
shadow = shadow.filter(ImageFilter.GaussianBlur(25))
im = Image.alpha_composite(im.convert("RGBA"), shadow)
d = ImageDraw.Draw(im, "RGBA")
d.rounded_rectangle((645, 52, 965, 430), radius=31,
                    fill=(250, 250, 255, 255), outline=(255, 255, 255, 110), width=3)
d.rounded_rectangle((674, 83, 748, 121), radius=17, fill=(94, 74, 174, 255))
d.text((693, 89), "DE", font=font(18, True), fill="white")
d.text((675, 148), "Haus", font=font(48, True), fill=(46, 37, 87, 255))
d.line((673, 225, 931, 225), fill=(228, 226, 242, 255), width=2)
d.text((675, 243), "English", font=font(17, True), fill=(110, 93, 177, 255))
d.text((675, 275), "house", font=font(25), fill=(43, 42, 63, 255))
d.text((675, 327), "Persian", font=font(17, True), fill=(110, 93, 177, 255))
d.text((675, 356), "خانه", font=ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf", 30), direction="rtl", fill=(43, 42, 63, 255))
im.convert("RGB").save(FEATURE, "PNG", optimize=True)
with Image.open(ICON) as img:
    assert img.size == (512, 512) and img.mode in ("RGBA", "RGB")
with Image.open(FEATURE) as img:
    assert img.size == (1024, 500) and img.mode == "RGB"
print("Store icon:", ICON, ICON.stat().st_size, "bytes")
print("Feature graphic:", FEATURE, FEATURE.stat().st_size, "bytes")

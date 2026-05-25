"""Generate icon.ico for FH6 Subtitle Switcher."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent / "icon.ico"
SIZE = 256
BG_COLOR = (200, 30, 50, 255)       # FH-ish red
FG_COLOR = (255, 255, 255, 255)     # white text
RADIUS = 44
MARGIN = 12

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle(
    [MARGIN, MARGIN, SIZE - MARGIN, SIZE - MARGIN],
    radius=RADIUS, fill=BG_COLOR,
)

# Bold Chinese for the "字" — try JhengHei Bold first, fall back to others
for candidate in [
    r"C:\Windows\Fonts\msjhbd.ttc",     # JhengHei Bold (Traditional)
    r"C:\Windows\Fonts\msyhbd.ttc",     # YaHei Bold (Simplified)
    r"C:\Windows\Fonts\msjh.ttc",       # JhengHei Regular
    r"C:\Windows\Fonts\kaiu.ttf",       # DFKai-SB
]:
    if Path(candidate).exists():
        font_path = candidate
        break
else:
    raise SystemExit("No suitable Chinese font found")

# Auto-fit
size = 220
while size > 80:
    font = ImageFont.truetype(font_path, size)
    b = draw.textbbox((0, 0), "字", font=font)
    tw, th = b[2] - b[0], b[3] - b[1]
    if tw <= SIZE * 0.72 and th <= SIZE * 0.72:
        break
    size -= 4

x = (SIZE - tw) // 2 - b[0]
y = (SIZE - th) // 2 - b[1]
draw.text((x, y), "字", font=font, fill=FG_COLOR)

# Save multi-size ICO
img.save(
    OUT,
    format="ICO",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print(f"Saved: {OUT}  ({OUT.stat().st_size} bytes)")

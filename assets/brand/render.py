"""Add editable type to Gemini backgrounds for repository banner previews."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = next((font for font in (
    '/System/Library/Fonts/Avenir Next.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
) if Path(font).exists()), None)
if not FONT:
    raise SystemExit('Install Avenir Next or DejaVu Sans to render banners')
TITLE = ImageFont.truetype(FONT, 174)
SMALL = ImageFont.truetype(FONT, 38)

for name, x, y, ink, accent in [
    ('signal', 185, 190, '#F7F3E9', '#F3A365'),
    ('workshop', 450, 690, '#152338', '#DA432C'),
    ('atlas', 365, 570, '#173A64', '#E45147'),
]:
    canvas = Image.open(HERE / 'concepts' / f'{name}.jpg').convert('RGB')
    draw = ImageDraw.Draw(canvas)
    draw.text((x, y), 'THE LOCAL', font=TITLE, fill=ink, stroke_width=0)
    draw.text((x, y + 162), 'NODE', font=TITLE, fill=ink, stroke_width=0)
    draw.rectangle((x + 4, y + 381, x + 140, y + 389), fill=accent)
    draw.text((x, y + 428), 'LEARN BY BUILDING', font=SMALL, fill=ink)
    canvas.save(HERE / 'concepts' / f'{name}-banner.jpg', quality=92, optimize=True)

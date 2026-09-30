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

for name, ink, accent in [
    ('relay', '#F7F3E9', '#F3A365'),
    ('folio', '#173A64', '#D7472D'),
    ('modules', '#173A64', '#D7472D'),
]:
    background = Image.open(HERE / 'concepts' / f'{name}.jpg').convert('RGB')
    canvas = background.copy()
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype(FONT, 164)
    tagline = ImageFont.truetype(FONT, 42)
    cx = canvas.width // 2
    cy = canvas.height // 2 + (115 if name == 'modules' else 0)
    draw.text((cx, cy - 95), 'THE LOCAL NODE', font=title, fill=ink, anchor='mm')
    draw.rectangle((cx - 78, cy + 38, cx + 78, cy + 46), fill=accent)
    draw.text((cx, cy + 115), 'LEARN BY BUILDING', font=tagline, fill=ink, anchor='mm')
    canvas.save(HERE / 'concepts' / f'{name}-banner.jpg', quality=92, optimize=True)

    youtube = background.resize((2560, 1440), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(youtube)
    title = ImageFont.truetype(FONT, 116)
    tagline = ImageFont.truetype(FONT, 38)
    safe_left, safe_top, safe_right, safe_bottom = 507, 509, 2053, 931
    for label, font, y in [('THE LOCAL NODE', title, 660), ('LEARN BY BUILDING', tagline, 803)]:
        box = draw.textbbox((1280, y), label, font=font, anchor='mm')
        assert safe_left <= box[0] < box[2] <= safe_right
        assert safe_top <= box[1] < box[3] <= safe_bottom
        draw.text((1280, y), label, font=font, fill=ink, anchor='mm')
    draw.rectangle((1210, 737, 1350, 745), fill=accent)
    youtube.save(HERE / 'concepts' / f'{name}-youtube.jpg', quality=92, optimize=True)

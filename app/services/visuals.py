from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiogram.types import BufferedInputFile

def vs_card(left: str, right: str) -> BufferedInputFile:
    """Creates a compact neon VS card for Telegram; no user image is exposed in anonymous mode."""
    image = Image.new("RGB", (1200, 630), "#080d1c")
    draw = ImageDraw.Draw(image)
    bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 58)
    huge = ImageFont.truetype("DejaVuSans-Bold.ttf", 150)
    small = ImageFont.truetype("DejaVuSans.ttf", 30)
    draw.rounded_rectangle((40, 40, 570, 590), radius=40, fill="#172554", outline="#38bdf8", width=4)
    draw.rounded_rectangle((630, 40, 1160, 590), radius=40, fill="#3b0764", outline="#c084fc", width=4)
    draw.text((300, 125), "PLAYER 1", font=small, fill="#7dd3fc", anchor="mm")
    draw.text((900, 125), "PLAYER 2", font=small, fill="#d8b4fe", anchor="mm")
    draw.multiline_text((300, 315), left, font=bold, fill="white", anchor="mm", align="center", spacing=12)
    draw.multiline_text((900, 315), right, font=bold, fill="white", anchor="mm", align="center", spacing=12)
    draw.ellipse((475, 205, 725, 455), fill="#f97316", outline="#fde68a", width=7)
    draw.text((600, 325), "VS", font=huge, fill="white", anchor="mm")
    output = BytesIO(); image.save(output, "PNG")
    return BufferedInputFile(output.getvalue(), filename="pvp-vs.png")

import requests
import textwrap
import subprocess
import tempfile
import os
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

# ---------- Settings ----------
IMG_W, IMG_H = 1920, 1080
MARGIN = 120
BG_COLOR = (15, 20, 30)
TEXT_COLOR = (255, 255, 255)
TITLE_FONT_SIZE = 70
BODY_FONT_SIZE = 46
MAX_WORDS_PER_SLIDE = 40
SLIDE_DURATION = 6
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---------- Fetch Text ----------
def fetch_page_text(url):
    r = requests.get(url, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    blocks = []
    for tag in soup.find_all(["h1","h2","h3","p","li"]):
        t = tag.get_text(" ", strip=True)
        if t and len(t) > 40:
            blocks.append(t)
    return blocks

# ---------- Slide Grouping ----------
def group_slides(blocks):
    slides = []
    buf, count = [], 0
    for blk in blocks:
        words = blk.split()
        if count + len(words) <= MAX_WORDS_PER_SLIDE:
            buf.append(blk)
            count += len(words)
        else:
            slides.append(" ".join(buf))
            buf, count = [blk], len(words)
    if buf: slides.append(" ".join(buf))
    return slides

# ---------- Render Slide ----------
def render_slide(text, idx, folder):
    font_body = ImageFont.truetype(FONT_PATH, BODY_FONT_SIZE)
    font_title = ImageFont.truetype(FONT_PATH, TITLE_FONT_SIZE)

    img = Image.new("RGB", (IMG_W, IMG_H), BG_COLOR)
    d = ImageDraw.Draw(img)

    y = MARGIN
    d.text((MARGIN, y), "Zama — Explained", fill=TEXT_COLOR, font=font_title)
    y += TITLE_FONT_SIZE + 40

    lines = textwrap.wrap(text, width=38)
    for line in lines:
        d.text((MARGIN, y), line, fill=TEXT_COLOR, font=font_body)
        y += BODY_FONT_SIZE + 10

    path = os.path.join(folder, f"slide_{idx:03d}.png")
    img.save(path)
    return path

# ---------- Create Male-like Audio ----------
def tts_male_voice(text, out_path):
    temp = "raw_voice.mp3"
    gTTS(text, lang="en").save(temp)

    # pitch down = male voice feel
    cmd = [
        "ffmpeg", "-y",
        "-i", temp,
        "-af", "asetrate=16000*0.85,atempo=1.1",  # pitch + tone adjustment
        out_path
    ]
    subprocess.run(cmd, check=True)
    os.remove(temp)

# ---------- FFmpeg merge ----------
def make_video(slides, audio_path, output_path):
    work = tempfile.mkdtemp()
    list_file = os.path.join(work, "list.txt")

    with open(list_file, "w") as f:
        for slide in slides:
            f.write(f"file '{slide}'\n")
            f.write(f"duration {SLIDE_DURATION}\n")
        f.write(f"file '{slides[-1]}'\n")

    tmp = os.path.join(work, "temp.mp4")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        tmp
    ], check=True)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", tmp, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac",
        "-shortest", output_path
    ], check=True)


# ---------- MAIN ----------
def main():
    url = "https://www.zama.org/blog"
    blocks = fetch_page_text(url)
    slides = group_slides(blocks)

    folder = tempfile.mkdtemp()
    slide_paths = []

    for i, s in enumerate(slides, 1):
        slide_paths.append(render_slide(s, i, folder))

    text_for_audio = " ".join(slides[:8])
    audio_path = os.path.join(folder, "voice_male.mp3")
    tts_male_voice(text_for_audio, audio_path)

    make_video(slide_paths, audio_path, "zama_explainer_male.mp4")
    print("DONE: zama_explainer_male.mp4")

if __name__ == "__main__":
    main()

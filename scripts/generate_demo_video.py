"""Generate demo.mp4 — 6-scene product walkthrough for StoreMD landing page."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
OUT = Path("frontend/public/demo.mp4")
TMP = Path("/tmp/demo_frames")

BG = (249, 250, 251)
CARD = (255, 255, 255)
BORDER = (229, 231, 235)
TEXT = (17, 24, 39)
MUTED = (107, 114, 128)
BLUE = (37, 99, 235)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
AMBER = (245, 158, 11)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def centered(draw: ImageDraw.ImageDraw, text: str, y: int, f: ImageFont.FreeTypeFont,
             color=TEXT) -> None:
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, font=f, fill=color)


def rounded_card(draw: ImageDraw.ImageDraw, xy, radius: int = 16,
                 fill=CARD, outline=BORDER, width: int = 2) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def scene_title() -> Image.Image:
    img, d = new_canvas()
    d.rounded_rectangle((860, 380, 1060, 480), radius=20, fill=BLUE)
    centered(d, "SM", 398, font(60, True), CARD)
    centered(d, "StoreMD", 520, font(96, True), TEXT)
    centered(d, "Your store health score in 60 seconds.", 640, font(48), MUTED)
    centered(d, "Scan. Score. Fix.", 720, font(40), BLUE)
    return img


def scene_install() -> Image.Image:
    img, d = new_canvas()
    centered(d, "Install StoreMD", 90, font(56, True), TEXT)
    centered(d, "on storemdtest.myshopify.com", 170, font(32), MUTED)

    rounded_card(d, (360, 260, 1560, 960), radius=24)

    d.rounded_rectangle((396, 296, 456, 356), radius=12, fill=BLUE)
    centered_x = 396 + (456 - 396) // 2
    bbox = d.textbbox((0, 0), "SM", font=font(28, True))
    d.text((centered_x - (bbox[2] - bbox[0]) // 2, 310), "SM", font=font(28, True),
           fill=CARD)
    d.text((480, 304), "StoreMD", font=font(36, True), fill=TEXT)
    d.text((480, 350), "by Altidigitech", font=font(24), fill=MUTED)

    d.line((396, 410, 1524, 410), fill=BORDER, width=2)
    d.text((420, 440), "This app will be able to:", font=font(30, True), fill=TEXT)

    scopes = [
        "View your products and collections",
        "View your theme code and assets",
        "View your orders (read-only)",
        "View your script tags",
    ]
    y = 500
    for s in scopes:
        d.ellipse((430, y + 10, 458, y + 38), fill=GREEN)
        d.line((436, y + 24, 446, y + 32), fill=CARD, width=4)
        d.line((446, y + 32, 454, y + 20), fill=CARD, width=4)
        d.text((480, y + 4), s, font=font(28), fill=TEXT)
        y += 64

    d.rounded_rectangle((1220, 840, 1510, 910), radius=12, fill=BLUE)
    centered_btn = 1220 + (1510 - 1220) // 2
    bbox = d.textbbox((0, 0), "Install app", font=font(30, True))
    d.text((centered_btn - (bbox[2] - bbox[0]) // 2, 858),
           "Install app", font=font(30, True), fill=CARD)
    return img


def scene_scan(progress: float) -> Image.Image:
    img, d = new_canvas()
    centered(d, "Scanning your store...", 140, font(64, True), TEXT)
    centered(d, "storemdtest.myshopify.com", 230, font(32), MUTED)

    rounded_card(d, (360, 340, 1560, 780), radius=24)
    centered(d, f"{int(progress * 100)}%", 420, font(140, True), BLUE)

    bx0, by0, bx1, by1 = 460, 620, 1460, 680
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=30, fill=(229, 231, 235))
    fill_end = bx0 + int((bx1 - bx0) * progress)
    if fill_end > bx0 + 4:
        d.rounded_rectangle((bx0, by0, fill_end, by1), radius=30, fill=BLUE)

    steps = [
        (0.0, "Fetching products & themes..."),
        (0.25, "Analyzing app impact..."),
        (0.50, "Detecting code residue..."),
        (0.70, "Scoring agentic readiness..."),
        (0.90, "Compiling report..."),
    ]
    current = steps[0][1]
    for pct, label in steps:
        if progress >= pct:
            current = label
    centered(d, current, 720, font(32), MUTED)
    return img


def draw_ring(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, thickness: int,
              progress: float, color) -> None:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(229, 231, 235),
              width=thickness)
    if progress <= 0:
        return
    steps = max(1, int(360 * progress))
    bbox = (cx - r, cy - r, cx + r, cy + r)
    d.arc(bbox, start=-90, end=-90 + steps, fill=color, width=thickness)


def scene_dashboard(progress: float) -> Image.Image:
    img, d = new_canvas()

    d.rectangle((0, 0, W, 100), fill=CARD)
    d.line((0, 100, W, 100), fill=BORDER, width=2)
    d.rounded_rectangle((40, 28, 100, 88), radius=12, fill=BLUE)
    bbox = d.textbbox((0, 0), "SM", font=font(28, True))
    d.text((70 - (bbox[2] - bbox[0]) // 2, 42), "SM", font=font(28, True), fill=CARD)
    d.text((120, 34), "StoreMD", font=font(32, True), fill=TEXT)
    d.text((120, 70), "Dashboard · storemdtest.myshopify.com", font=font(22),
           fill=MUTED)

    rounded_card(d, (60, 160, 900, 760), radius=24)
    d.text((100, 200), "Store Health", font=font(32, True), fill=TEXT)

    score_target = 78
    displayed = int(score_target * progress)
    draw_ring(d, 480, 470, 190, 28, progress, BLUE)
    centered_text = str(displayed)
    bbox = d.textbbox((0, 0), centered_text, font=font(140, True))
    d.text((480 - (bbox[2] - bbox[0]) // 2, 400 - (bbox[3] - bbox[1]) // 2 + 30),
           centered_text, font=font(140, True), fill=TEXT)
    d.text((480 - 40, 540), "/ 100", font=font(36), fill=MUTED)
    centered(d, "Good · trending up", 700, font(28), GREEN)

    rounded_card(d, (960, 160, 1860, 760), radius=24)
    d.text((1000, 200), "Top issues", font=font(32, True), fill=TEXT)

    issues = [
        (RED, "CRITICAL", "3 apps still injecting after uninstall"),
        (RED, "CRITICAL", "SSL cert expires in 9 days"),
        (AMBER, "MAJOR", "47 products missing alt text"),
        (AMBER, "MAJOR", "Meta Pixel firing twice on /checkout"),
        (MUTED, "MINOR", "robots.txt blocks ai-crawlers"),
    ]
    y = 270
    visible = min(len(issues), int(progress * (len(issues) + 1)))
    for i, (color, sev, text) in enumerate(issues[:visible]):
        rounded_card(d, (1000, y, 1820, y + 76), radius=12, fill=(249, 250, 251),
                     outline=BORDER, width=1)
        d.rounded_rectangle((1020, y + 22, 1160, y + 54), radius=8, fill=color)
        bbox = d.textbbox((0, 0), sev, font=font(20, True))
        d.text((1090 - (bbox[2] - bbox[0]) // 2, y + 28), sev, font=font(20, True),
               fill=CARD)
        d.text((1180, y + 22), text, font=font(24), fill=TEXT)
        y += 90

    return img


def scene_listings() -> Image.Image:
    img, d = new_canvas()
    centered(d, "Listing Audit", 70, font(56, True), TEXT)
    centered(d, "87 products analyzed · 12 need attention", 150, font(28), MUTED)

    rounded_card(d, (120, 220, 1800, 960), radius=24)

    headers = [("Product", 160), ("Score", 1040), ("Alt text", 1240),
              ("AI-ready", 1440), ("Action", 1620)]
    for h, x in headers:
        d.text((x, 260), h, font=font(24, True), fill=MUTED)
    d.line((160, 310, 1760, 310), fill=BORDER, width=2)

    rows = [
        ("Midnight Hoodie — Charcoal", 92, GREEN, "OK", GREEN, "OK", GREEN, "Up to date"),
        ("Linen Shirt — Sand", 81, GREEN, "OK", GREEN, "OK", GREEN, "Up to date"),
        ("Classic Tee — Black", 64, AMBER, "Missing", RED, "Weak", RED, "Fix now"),
        ("Wool Beanie", 58, AMBER, "Missing", AMBER, "Partial", AMBER, "Fix now"),
        ("Linen Pants — Olive", 73, GREEN, "OK", GREEN, "Partial", AMBER, "Review"),
        ("Silk Scarf — Rose", 41, RED, "Missing", RED, "Weak", RED, "Fix now"),
    ]
    y = 340
    for name, score, sc_color, alt, alt_color, ai, ai_color, action in rows:
        d.text((160, y), name, font=font(26), fill=TEXT)
        d.text((1040, y), str(score), font=font(28, True), fill=sc_color)
        d.rounded_rectangle((1240, y - 4, 1400, y + 40), radius=8,
                            fill=(249, 250, 251), outline=alt_color, width=2)
        bbox = d.textbbox((0, 0), alt, font=font(22, True))
        d.text((1320 - (bbox[2] - bbox[0]) // 2, y + 6), alt, font=font(22, True),
               fill=alt_color)
        d.rounded_rectangle((1440, y - 4, 1580, y + 40), radius=8,
                            fill=(249, 250, 251), outline=ai_color, width=2)
        bbox = d.textbbox((0, 0), ai, font=font(22, True))
        d.text((1510 - (bbox[2] - bbox[0]) // 2, y + 6), ai, font=font(22, True),
               fill=ai_color)
        action_color = BLUE if action == "Fix now" else MUTED
        d.text((1620, y), action, font=font(22, True), fill=action_color)
        y += 90

    return img


def scene_end() -> Image.Image:
    img, d = new_canvas()
    d.rounded_rectangle((860, 340, 1060, 440), radius=20, fill=BLUE)
    centered(d, "SM", 358, font(60, True), CARD)
    centered(d, "Your store deserves a doctor.", 480, font(72, True), TEXT)
    centered(d, "Free plan. Get started in 60 seconds.", 580, font(40), MUTED)
    d.rounded_rectangle((760, 680, 1160, 780), radius=16, fill=BLUE)
    bbox = d.textbbox((0, 0), "Get started  →", font=font(40, True))
    d.text((960 - (bbox[2] - bbox[0]) // 2, 702), "Get started  →",
           font=font(40, True), fill=CARD)
    centered(d, "storemd.vercel.app", 830, font(28), MUTED)
    return img


def ease(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


def render() -> None:
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    scenes: list[tuple[str, int]] = []

    def still(name: str, img: Image.Image, seconds: int) -> None:
        path = TMP / f"{name}.png"
        img.save(path, "PNG", optimize=False)
        scenes.append((str(path), seconds))

    def animated(name: str, frame_fn, seconds: int) -> None:
        total = seconds * FPS
        folder = TMP / name
        folder.mkdir()
        for i in range(total):
            t = i / max(1, total - 1)
            frame_fn(t).save(folder / f"{i:04d}.png", "PNG", optimize=False)
        scenes.append((str(folder / "%04d.png"), -seconds))

    print("scene 1: title")
    still("s1", scene_title(), 3)
    print("scene 2: install")
    still("s2", scene_install(), 3)
    print("scene 3: scan (animated)")
    animated("s3", lambda t: scene_scan(ease(t)), 5)
    print("scene 4: dashboard (animated)")
    animated("s4", lambda t: scene_dashboard(ease(t)), 5)
    print("scene 5: listings")
    still("s5", scene_listings(), 4)
    print("scene 6: end card")
    still("s6", scene_end(), 3)

    print("compiling per-scene mp4s...")
    parts: list[Path] = []
    for i, (src, seconds) in enumerate(scenes):
        out = TMP / f"part_{i:02d}.mp4"
        if seconds > 0:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-loop", "1", "-framerate", str(FPS), "-t", str(seconds),
                "-i", src,
                "-vf", f"scale={W}:{H},format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-movflags", "+faststart",
                str(out),
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-framerate", str(FPS), "-i", src,
                "-vf", f"scale={W}:{H},format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-movflags", "+faststart",
                str(out),
            ]
        subprocess.run(cmd, check=True)
        parts.append(out)

    concat_list = TMP / "concat.txt"
    concat_list.write_text("".join(f"file '{p}'\n" for p in parts))

    print("concatenating...")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", "-movflags", "+faststart",
        str(OUT),
    ], check=True)

    print(f"done: {OUT} ({OUT.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    render()

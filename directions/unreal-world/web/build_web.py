"""Turn the Unreal renders into the web direction's assets, and tell the page where the poster is.

  python3 build_web.py --concept 1 [--renders ../world/Saved/MovieRenders]

Writes assets/: still.avif/.webp and still-phone.* (the finals), loop.mp4/.webm and loop-phone.* (the 10 s loops),
depth.png and depth-phone.png (disparity 2/d, 8 bit), and the poster's place in each frame into index.html
(between /*FRAMES*/ and /*END*/). The poster's corners are projected through the same camera the scene used.
"""
import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "world", "scripts"))
import concepts  # noqa: E402
from terrain import height  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--concept", type=int, default=1)
ap.add_argument("--renders", default=os.path.join(HERE, "..", "world", "Saved", "MovieRenders"))
args = ap.parse_args()
A = os.path.join(HERE, "assets")
os.makedirs(A, exist_ok=True)
R = args.renders


def ff(*a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *a], check=True)


def project(cam, sensor, pts, w, h):
    """Project world points (metres) through a CineCamera (pitch/yaw in degrees, focal mm, filmback mm) to 0-1."""
    p, y = math.radians(cam["pitch"]), math.radians(cam["yaw"])
    C = (cam["x"], cam["y"], height(cam["x"], cam["y"]) + cam["eye"])
    f = (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))
    r = (-math.sin(y), math.cos(y), 0.0)
    u = (-math.sin(p) * math.cos(y), -math.sin(p) * math.sin(y), math.cos(p))
    sw = sensor[0]
    sh = sw * h / w  # MRQ crops the filmback to the output's aspect
    out = []
    for P in pts:
        d = [P[i] - C[i] for i in range(3)]
        x = sum(d[i] * f[i] for i in range(3))
        out.append((0.5 + sum(d[i] * r[i] for i in range(3)) / x * cam["focal"] / sw,
                    0.5 - sum(d[i] * u[i] for i in range(3)) / x * cam["focal"] / sh, x))
    return out


def sample(png, u, v, n=5):
    """Mean value (0-1) of an n x n patch of a grey PNG at (u, v): the pivot must match the texture's own encoding."""
    wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", png],
                        capture_output=True, text=True, check=True).stdout.strip().split(",")
    x, y = int(int(wh[0]) * u), int(int(wh[1]) * v)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", png, "-vf", f"crop={n}:{n}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    return sum(raw) / len(raw) / 255


def poster_box(look, cam, sensor, w, h):
    x, y, yaw = look["lightbox"]
    W, H, foot = 1.16, 1.74, 0.45
    z0 = height(x, y) + foot
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    corners = []
    for ly in (-W / 2, W / 2):
        for lz in (0.0, H):
            lx = -0.005
            corners.append((x + lx * c - ly * s, y + lx * s + ly * c, z0 + lz))
    pr = project(cam, sensor, corners, w, h)
    us, vs = [q[0] for q in pr], [q[1] for q in pr]
    dist = sum(q[2] for q in pr) / 4
    return [round(min(us), 4), round(min(vs), 4), round(max(us), 4), round(max(vs), 4)], dist


name, line, look = concepts.look(args.concept)
phone_cam = dict(look["camera"], yaw=look["camera"]["yaw"] + 3.0, pitch=look["camera"]["pitch"] + 2.0, focal=17.0)
frames = {}
for key, pat, loopdir, depth_pat, cam, sensor, (w, h), suffix in [
        ("wide", "hero_final_0000.png", "loop", "hero_depth_0000*isparity*.png", look["camera"], (36.0, 20.25), (3840, 2160), ""),
        ("phone", "phone_final_0000.png", "loop_phone", "phone_depth_0000*isparity*.png", phone_cam, (16.6, 36.0), (1080, 2340), "-phone")]:
    still = os.path.join(R, pat)
    if not os.path.exists(still):
        print("missing", still)
        continue
    sw_ = "scale=2560:-2" if key == "wide" else "scale=1080:-2"   # the page's still; the full 4K is kept in ../world/renders
    ff("-i", still, "-vf", sw_, "-c:v", "libwebp", "-quality", "82", os.path.join(A, f"still{suffix}.webp"))
    ff("-i", still, "-vf", sw_, "-c:v", "libaom-av1", "-still-picture", "1", "-crf", "28", "-pix_fmt", "yuv420p",
       os.path.join(A, f"still{suffix}.avif"))
    full = os.path.join(HERE, "..", "world", "renders")
    os.makedirs(full, exist_ok=True)
    ff("-i", still, "-c:v", "libwebp", "-quality", "92", os.path.join(full, f"{name}{suffix}-{w}x{h}.webp"))
    lw = 1920 if key == "wide" else 720
    loop = sorted(glob.glob(os.path.join(R, loopdir, "*.png")))
    if loop:
        src = os.path.join(R, loopdir, re.sub(r"\d{4}\.png$", "%04d.png", os.path.basename(loop[0])))
        # Frame 0 is a first-frame artefact (warm-up); 1 to 239 wrap cleanly (239 to 1 matches adjacent frames).
        ff("-framerate", "24", "-start_number", "1", "-i", src, "-vf", f"scale={lw}:-2", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", os.path.join(A, f"loop{suffix}.mp4"))
        ff("-framerate", "24", "-start_number", "1", "-i", src, "-vf", f"scale={lw}:-2", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34",
           "-row-mt", "1", "-an", os.path.join(A, f"loop{suffix}.webm"))
    dp = sorted(glob.glob(os.path.join(R, depth_pat)))
    if dp:
        ff("-i", dp[0], "-vf", f"scale={lw}:-2,format=gray", os.path.join(A, f"depth{suffix}.png"))
    box, dist = poster_box(look, cam, sensor, w, h)
    pad = 0.35
    bw, bh = box[2] - box[0], box[3] - box[1]
    frames[key] = {"w": w, "h": h, "paper": box,
                   "stone": [round(box[0] - bw * pad, 4), round(box[1] - bh * pad, 4), round(box[2] + bw * pad, 4), round(box[3] + bh * pad, 4)],
                   "stone_disp": round(min(1.0, 2.0 / dist), 4)}
    dpng = os.path.join(A, f"depth{suffix}.png")
    if os.path.exists(dpng):  # the depth map is stored sRGB-encoded: read the pivot from it at the print
        frames[key]["stone_disp"] = round(sample(dpng, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2), 4)

page = os.path.join(HERE, "index.html")
html = open(page).read()
html = re.sub(r"/\*FRAMES\*/.*?/\*END\*/", "/*FRAMES*/" + json.dumps(frames) + "/*END*/", html, flags=re.S)
open(page, "w").write(html)
json.dump(dict(frames, concept=args.concept, name=name), open(os.path.join(A, "frame.json"), "w"), indent=1)
print(json.dumps(frames))
for f in sorted(os.listdir(A)):
    print(f"{os.path.getsize(os.path.join(A, f)) / 1024:9.0f} KB  {f}")

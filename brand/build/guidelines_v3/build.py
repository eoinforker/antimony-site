"""Builds the Antimony brand guidelines (../../guidelines/) and kit (../../kit-v3/).

  python3 build.py assets   grains, icons, mock-up pages, SVG masters, and the render jobs
  node render.cjs jobs/textures.json; node render.cjs jobs/exports.json
  python3 build.py finish   favicon.ico, the zip, the copies the guidelines link to
  python3 build.py pages    the guidelines pages

run.sh does all of it in order."""
import json, os, shutil, subprocess, sys, zipfile
import numpy as np
from PIL import Image
import geo as g
import mockups

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "../../.."))
GUIDE = os.path.join(SITE, "brand/guidelines")
KIT = os.path.join(SITE, "brand/kit-v3")
ZIP = os.path.join(SITE, "brand/antimony-kit-v3.zip")
FONTS = os.path.join(SITE, "assets/fonts")
JOBS = os.path.join(HERE, "jobs")
CAPTURE = os.path.join(HERE, "src/motion")      # frames captured from directions/blend-c by cap/blendc.cjs
LAB = "file://" + os.path.join(HERE, "textures.html")

def mk(*p):
    d = os.path.join(*p); os.makedirs(d, exist_ok=True); return d
def write(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(s)

# ---------- grain, baked once, the same recipe as the website ----------
def grains():
    d = mk(GUIDE, "img/tex")
    rng = np.random.default_rng(51)
    n = 256
    r = rng.random((n, n)); a1 = rng.random((n, n)); a = np.zeros((n, n, 4), np.uint8)
    dark = r < .42; light = (r >= .42) & (r < .5)
    a[dark] = [52, 46, 38, 0]; a[dark, 3] = (7 + a1[dark] * 15).astype(np.uint8)
    a[light] = [255, 255, 255, 0]; a[light, 3] = (10 + a1[light] * 12).astype(np.uint8)
    Image.fromarray(a, "RGBA").save(os.path.join(d, "grain-alpha.png"), optimize=True)
    b = np.zeros((n, n, 4), np.uint8); lit = r < .3
    b[lit] = [238, 234, 224, 0]; b[lit, 3] = (4 + a1[lit] * 9).astype(np.uint8)
    Image.fromarray(b, "RGBA").save(os.path.join(d, "grain-light.png"), optimize=True)
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(os.path.join(d, "grain-none.png"))
    # a swatch of grain on cream, for the art direction chapter
    base = np.ones((n, n, 3)) * np.array([238, 234, 224])
    al = a[..., 3:4] / 255.0
    sw = base * (1 - al) + a[..., :3] * al
    Image.fromarray(sw.astype(np.uint8)).save(os.path.join(d, "grain-cream.png"), optimize=True)

# ---------- textures, drawn by textures.html ----------
TEX = [  # name, w, h, params
    ("light-poster.jpg", 2400, 3394, "t=light&lx=.56&ly=.12&seed=2"),
    ("light-wide.jpg", 3000, 1000, "t=light&lx=.74&ly=.02&seed=5"),
    ("light-panel.jpg", 2400, 1350, "t=light&lx=.62&ly=.08&seed=3"),
    ("stipple-wide.png", 3168, 792, "t=stipple&lx=.78&ly=.02&seed=4&cell=8"),
    ("stipple-deck.png", 2880, 1620, "t=stipple&lx=.8&ly=.05&seed=6&cell=8"),
    ("stipple-panel.png", 2400, 1350, "t=stipple&lx=.6&ly=.1&seed=3&cell=8"),
    ("halftone-panel.png", 2400, 1350, "t=halftone&lx=.6&ly=.1&seed=3&cell=14"),
    ("halftone-ink-panel.png", 2400, 1350, "t=halftone&ground=ink&lx=.6&ly=.1&seed=3&cell=14"),
    ("chars-panel.png", 2400, 1350, "t=chars&lx=.5&ly=.5&seed=7&fs=22"),
    ("chars-poster.png", 2400, 3394, "t=chars&lx=.5&ly=.46&seed=8&fs=24&boost=1.3"),
    ("stone-card.jpg", 1004, 650, "t=stone&seed=1"),
    ("stone-panel.jpg", 2400, 1350, "t=stone&seed=1"),
]
def texture_jobs():
    d = mk(GUIDE, "img/tex")
    return [{"url": f"{LAB}?{p}&w={w}&h={h}", "w": w, "h": h, "out": os.path.join(d, n), "waitTitle": 1} for n, w, h, p in TEX]

# ---------- SVG masters for the kit ----------
GROUNDS = [("cream", g.CREAM), ("ink", g.INK), ("prussian", g.PRU), ("washi", g.WASHI)]
def kit_svgs():
    """Every master, as (relative path, svg, 1x width in px, 1x height or None)."""
    out = []
    def add(rel, svg, w, h=None): out.append((rel, svg, w, h))
    # the mark
    for gn, gc in GROUNDS:
        add(f"mark/antimony-mark-full-colour-for-{gn}.svg", g.mark(**g.mark_for(gc)), 512, 512)
    add("mark/antimony-mark-full-colour-light.svg", g.mark(light=True), 512, 512)
    add("mark/antimony-mark-full-colour-light-for-ink.svg", g.mark(**g.mark_for(g.INK, light=True)), 512, 512)
    add("mark/antimony-mark-small-16-to-30px.svg", g.mark(small=True), 512, 512)
    for nm, c in (("ink", g.INK), ("stone", g.STONE), ("prussian", g.PRU)):
        add(f"mark/one-colour/antimony-mark-one-colour-{nm}.svg", g.mark_one(c), 512, 512)
    # the line mark
    for nm, c in (("ink", g.INK), ("cream", g.CREAM), ("prussian", g.PRU), ("sky", g.SKY)):
        add(f"line-mark/antimony-line-mark-{nm}.svg", g.line_mark(c, 1.0), 512, 512)
        add(f"line-mark/hairline/antimony-line-mark-hairline-{nm}.svg", g.line_mark(c, 1.0, nonscaling=True), 512, 512)
    # wordmarks
    wms = {"caps": lambda f, c: g.caps(f, c), "lowercase": lambda f, c: g.serif(f, c), "heavy": lambda f, c: g.serif(f, c, heavy=True), "title": lambda f, c: g.title(f, c)}
    for wn, fn in wms.items():
        for gn, gc in GROUNDS:
            fg = g.INK if gc in g.LIGHT else g.CREAM
            add(f"wordmark/{wn}/antimony-wordmark-{wn}-for-{gn}.svg", fn(fg, g.lit_for(gc)), 1600)
        for nm, c in (("ink", g.INK), ("cream", g.CREAM), ("prussian", g.PRU)):
            one = (lambda f: g.caps(f, None)) if wn == "caps" else (lambda f: g.title(f, None)) if wn == "title" else (lambda f: g.serif(f, f, heavy=(wn == "heavy")))
            add(f"wordmark/{wn}/one-colour/antimony-wordmark-{wn}-one-colour-{nm}.svg", one(c), 1600)
    # lockups
    for gn, gc in GROUNDS:
        add(f"lockup/primary/antimony-lockup-primary-for-{gn}.svg", g.lockup(gc), 1600)
        add(f"lockup/stacked/antimony-lockup-stacked-for-{gn}.svg", g.stacked(gc), 800)
    for nm, c in (("ink", g.INK), ("prussian", g.PRU), ("cream-line", g.CREAM)):
        add(f"lockup/primary/one-colour/antimony-lockup-primary-one-colour-{nm}.svg", g.lockup(one=c), 1600)
        add(f"lockup/stacked/one-colour/antimony-lockup-stacked-one-colour-{nm}.svg", g.stacked(one=c), 800)
    # product lockups
    for gn, gc in (("cream", g.CREAM), ("ink", g.INK)):
        add(f"product/orbe-by-antimony-for-{gn}.svg", g.product(gc), 1600)
    return out

def svg_size(svg, w, h):
    import re
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    return w, h or round(w * vb[3] / vb[2])

def kit_assets():
    if os.path.isdir(KIT): shutil.rmtree(KIT)
    mk(KIT)
    jobs = []
    vdir = mk(HERE, "jobs/view")
    for rel, svg, w, h in kit_svgs():
        p = os.path.join(KIT, "svg", rel); write(p, '<?xml version="1.0" encoding="UTF-8"?>\n' + svg + "\n")
        W, Hh = svg_size(svg, w, h)
        base = rel[:-4]
        # a tiny page per master, so the PNG is drawn by the same engine as the guidelines
        vp = os.path.join(vdir, base.replace("/", "__") + ".html")
        write(vp, f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}img{{display:block;width:{W}px;height:{Hh}px}}</style></head><body><img src="file://{p}"></body></html>')
        for k in (1, 2):
            jobs.append({"url": "file://" + vp, "w": W, "h": Hh, "scale": k, "omit": True, "out": os.path.join(KIT, "png", f"{base}@{k}x.png")})
            mk(os.path.dirname(os.path.join(KIT, "png", f"{base}@{k}x.png")))
    # icons
    idir = mk(KIT, "icons")
    write(os.path.join(idir, "favicon.svg"), favicon_svg())
    icons = [("favicon-16.png", 16, g.favicon(16)), ("favicon-32.png", 32, g.favicon(32)), ("favicon-48.png", 48, g.favicon(48)),
             ("apple-touch-icon.png", 180, g.app_icon()), ("icon-192.png", 192, g.app_icon()), ("icon-512.png", 512, g.app_icon()),
             ("icon-maskable-512.png", 512, g.app_icon()), ("app-icon-1024.png", 1024, g.app_icon())]
    for n, px, svg in icons:
        vp = os.path.join(vdir, "icon__" + n + ".html")
        write(vp, f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}svg{{display:block;width:{px}px;height:{px}px}}</style></head><body>{svg}</body></html>')
        jobs.append({"url": "file://" + vp, "w": px, "h": px, "omit": True, "out": os.path.join(idir, n)})
    write(os.path.join(idir, "app-icon.svg"), g.app_icon())
    write(os.path.join(idir, "site.webmanifest"), json.dumps({"name": "Antimony", "short_name": "Antimony", "theme_color": "#EEEAE0", "background_color": "#EEEAE0",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}, indent=1))
    write(os.path.join(idir, "head.html"), '<link rel="icon" href="/favicon.ico" sizes="any">\n<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
          '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n<link rel="manifest" href="/site.webmanifest">\n')
    return jobs

def favicon_svg():
    q = g.QS
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="22" fill="#EEEAE0"/>'
            f'<path d="{q["stone"]}" fill="#141311"/><path d="{q["gem"]}" fill="#94E6FF"/><path d="{q["facet"]}" fill="#fff" fill-opacity=".28"/></svg>\n')

# ---------- mock-ups ----------
MOCK_EXPORT = {  # name: (kit folder, [(scale, suffix)], pdf)
    "linkedin-banner": ("social", [(1, "@1x"), (2, "@2x")], None), "linkedin-avatar": ("social", [(1, "@1x"), (2, "@2x")], None),
    "x-header": ("social", [(1, "@1x"), (2, "@2x")], None), "link-card": ("social", [(1, "@1x"), (2, "@2x")], None),
    "poster-light": ("posters", [(2, "")], None), "poster-paper": ("posters", [(2, "")], None), "poster-stone": ("posters", [(2, "")], None),
    "card-front": ("print", [(3.125, "-300dpi")], ("85mm", "55mm")), "card-back": ("print", [(3.125, "-300dpi")], ("85mm", "55mm")),
    "letterhead": ("print", [(3.125, "-300dpi")], ("210mm", "297mm")),
    "deck-title": ("deck", [(1, "@1x"), (2, "@2x")], None), "email-signature": ("email", [(2, "@2x")], None),
}
MM = 96 / 25.4
def px(v): return float(v[:-2]) * MM if isinstance(v, str) else float(v)

def mock_assets():
    d = mk(GUIDE, "mockups"); jobs = []
    sizes = {}
    for name, (w, h, html) in mockups.all_mockups().items():
        write(os.path.join(d, name + ".html"), html)
        W, Hh = px(w), px(h); sizes[name] = (round(W, 2), round(Hh, 2))
        folder, scales, pdf = MOCK_EXPORT[name]
        for k, suf in scales:
            out = os.path.join(mk(KIT, folder), f"antimony-{name}{suf}.png")
            jobs.append({"url": "file://" + os.path.join(d, name + ".html"), "w": int(-(-W // 1)), "h": int(-(-Hh // 1)), "clipW": W, "clipH": Hh, "scale": k, "out": out, "wait": 400})
        if pdf:
            jobs.append({"url": "file://" + os.path.join(d, name + ".html"), "w": int(-(-W // 1)), "h": int(-(-Hh // 1)), "out": os.path.join(KIT, folder, f"antimony-{name}.pdf"), "pdf": {"width": pdf[0], "height": pdf[1]}, "wait": 400})
        # a 1x preview for the guidelines' download links
        jobs.append({"url": "file://" + os.path.join(d, name + ".html"), "w": int(-(-W // 1)), "h": int(-(-Hh // 1)), "clipW": W, "clipH": Hh, "scale": 1 if W > 500 else 2,
                     "out": os.path.join(mk(GUIDE, "img/use"), f"antimony-{name}.png"), "wait": 400})
    json.dump(sizes, open(os.path.join(JOBS, "mock-sizes.json"), "w"))
    # the email signature as a file to use
    write(os.path.join(KIT, "email/signature.html"),
          '<!-- Paste into your mail client\'s signature settings. Host the lockup image and replace its src with the hosted address. -->\n'
          '<table cellpadding="0" cellspacing="0" border="0" style="font-family:Georgia,\'Times New Roman\',serif;color:#0B0C0C">\n'
          '<tr><td style="font-size:15px;font-weight:bold;line-height:20px">E&oacute;in Forker</td></tr>\n'
          '<tr><td style="font-size:14px;line-height:19px;color:#5B5A56">Founder, Antimony</td></tr>\n'
          '<tr><td style="padding-top:16px"><img src="antimony-lockup-email@2x.png" width="162" height="39" alt="Antimony" style="display:block;border:0"></td></tr>\n</table>\n')
    return jobs

def site_icons():
    d = mk(GUIDE, "img")
    write(os.path.join(d, "favicon.svg"), favicon_svg())
    jobs = []
    for n, pxs, svg in (("favicon-32.png", 32, g.favicon(32)), ("apple-touch-icon.png", 180, g.app_icon())):
        vp = os.path.join(mk(HERE, "jobs/view"), "site__" + n + ".html")
        write(vp, f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}svg{{display:block;width:{pxs}px;height:{pxs}px}}</style></head><body>{svg}</body></html>')
        jobs.append({"url": "file://" + vp, "w": pxs, "h": pxs, "omit": True, "out": os.path.join(d, n)})
    # the email lockup, as the signature uses it
    vp = os.path.join(HERE, "jobs/view/email-lockup.html")
    write(vp, f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}svg{{display:block;width:162px;height:auto}}</style></head><body>{g.lockup(g.CREAM)}</body></html>')
    jobs.append({"url": "file://" + vp, "w": 162, "h": 39, "scale": 2, "omit": True, "out": os.path.join(KIT, "email/antimony-lockup-email@2x.png")})
    return jobs

def copy_static():
    fd = mk(GUIDE, "fonts")
    for f in ("TimelessSerifVF.woff2", "TimelessSerifItalicVF.woff2", "CommitMono-Latin-VF.woff2", "CommitMono-OFL.txt"):
        shutil.copy(os.path.join(FONTS, f), fd)
    # the kit carries the open font, and a note on the licensed one
    kf = mk(KIT, "fonts")
    for f in ("CommitMono-Latin-VF.woff2", "CommitMono-OFL.txt"):
        shutil.copy(os.path.join(FONTS, f), kf)
    write(os.path.join(kf, "TIMELESS-SERIF.txt"), "Timeless Serif is licensed to Antimony and is not included in this kit.\n"
          "Ask the brand owner for the files and the terms of the licence before you set type in it.\n"
          "Every wordmark and lockup in this kit is drawn as outlines, so you do not need the font to use them.\n")

def textures_to_kit():
    td = mk(KIT, "textures")
    for n, w, h, p in TEX:
        if n.endswith("-poster.jpg") or n.endswith("-poster.png") or "panel" in n or "wide" in n:
            shutil.copy(os.path.join(GUIDE, "img/tex", n), td)
    for n in ("grain-alpha.png", "grain-light.png", "grain-cream.png"):
        shutil.copy(os.path.join(GUIDE, "img/tex", n), td)

def motion_frames():
    """Crops the frames captured from the website's opening for the storyboard."""
    d = mk(GUIDE, "img/motion")
    if not os.path.isdir(CAPTURE): return
    for f in sorted(os.listdir(CAPTURE)):
        src = os.path.join(CAPTURE, f)
        if not f.endswith(".png"):
            shutil.copy(src, d); continue
        im = Image.open(src).convert("RGB")
        if f.startswith("beat-"):
            if f == "beat-typed.png": im = im.crop((420, 0, 1020, 375))
            else: im = im.crop((240, 82, 1200, 682))
            im.save(os.path.join(d, f[:-4] + ".jpg"), quality=88)
        else:
            im.save(os.path.join(d, f[:-4] + ".jpg"), quality=90)

def finish():
    # print PNGs at exactly 300 dpi: 85 x 55 mm is 1004 x 650, A4 is 2480 x 3508
    for n, size in (("card-front", (1004, 650)), ("card-back", (1004, 650)), ("letterhead", (2480, 3508))):
        p = os.path.join(KIT, "print", f"antimony-{n}-300dpi.png")
        im = Image.open(p)
        if im.size != size: im.resize(size, Image.LANCZOS).save(p, dpi=(300, 300), optimize=True)
    # favicon.ico from the three small PNGs
    idir = os.path.join(KIT, "icons")
    subprocess.run(["convert", *(os.path.join(idir, f"favicon-{s}.png") for s in (16, 32, 48)), os.path.join(idir, "favicon.ico")], check=True)
    textures_to_kit()
    write(os.path.join(KIT, "README.txt"), README)
    if os.path.exists(ZIP): os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(KIT):
            for f in sorted(files):
                p = os.path.join(root, f)
                z.write(p, os.path.join("antimony-kit-v3", os.path.relpath(p, KIT)))
    dd = mk(GUIDE, "downloads"); shutil.copy(ZIP, dd)
    print("zip", round(os.path.getsize(ZIP) / 1e6, 1), "MB")

README = """Antimony brand kit, edition three
=================================

The full guidelines are in the brand guidelines site (brand/guidelines/index.html). This kit holds the files.

svg/          Masters. Use these wherever you can.
  mark/         The Break in full colour for cream, ink, Prussian and washi grounds; the light version, where the
                crystal holds water; the small drawing for 16 to 30 px; one colour versions.
  line-mark/    The mark in outline. hairline/ keeps a one pixel line at any size, for the mark as a design element.
  wordmark/     caps (primary), lowercase, heavy and title, for each ground, and in one colour.
  lockup/       primary (mark beside the capitals) and stacked (mark above), for each ground, and in one colour.
  product/      Orbe, by Antimony.
png/          Every master at 1x and 2x, on a transparent ground.
icons/        favicon.ico, favicon.svg, favicons at 16, 32 and 48, the Apple touch icon, app icons at 192, 512 and
              1024, a maskable icon, site.webmanifest and the lines for the head of a page (head.html).
social/       LinkedIn banner and avatar, X header, link card, at 1x and 2x.
posters/      Three posters at 2400 by 3394 (A series proportion).
print/        Business card front and back and the letterhead, as PNG at 300 dpi and PDF at true size.
deck/         The title slide at 1920 by 1080, and 2x.
email/        The signature, as a picture and as HTML, and its lockup image.
textures/     Paper grain, water light, stippled light, halftone, the character field and stone, as drawn for the guidelines.
fonts/        Commit Mono (SIL Open Font License). Timeless Serif is licensed to Antimony and not included.

Choosing a file
  "for-cream" means the file is drawn to sit on cream; "for-ink" on ink; and so on. The stone is always dark:
  on dark grounds its cut edges carry a hairline of light. Never place a pale tile on a dark ground.
  One colour on a dark ground is the line mark.

Clear space: 22 units of the mark's 100 on every side. Smallest sizes: the mark 16 px (6 mm), the primary
lockup 180 px (40 mm), the stacked lockup 120 px (26 mm).
"""

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "assets"
    mk(JOBS)
    if stage == "assets":
        grains()
        json.dump(texture_jobs(), open(os.path.join(JOBS, "textures.json"), "w"), indent=0)
        jobs = kit_assets() + mock_assets() + site_icons()
        copy_static()
        json.dump(jobs, open(os.path.join(JOBS, "exports.json"), "w"), indent=0)
        motion_frames()
        print("jobs", len(jobs))
    elif stage == "finish":
        finish()
    elif stage == "pages":
        import pages
        pages.build()

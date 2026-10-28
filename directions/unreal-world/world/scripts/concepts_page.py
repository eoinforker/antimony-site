"""Write previews/concepts/index.html (a review page for the ten concepts) and contact.webp (all ten on one sheet).
  python3 concepts_page.py"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import concepts  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previews", "concepts")
items = []
for n, (name, line, _) in sorted(concepts.CONCEPTS.items()):
    f = f"{n:02d}-{name}.webp"
    if os.path.exists(os.path.join(OUT, f)):
        items.append((n, name, line, f))

cards = "\n".join(f'''  <figure><img src="{f}" alt="Concept {n}: {line}" loading="lazy"><figcaption><b>{n:02d}</b> {name.replace("-", " ")}<br><span>{line}</span></figcaption></figure>'''
                  for n, name, line, f in items)
html = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Antimony world: ten concepts</title>
<style>
body {{ margin: 0; background: #0B0C0C; color: #EEEAE0; font: 15px/1.5 Georgia, serif; }}
header {{ padding: 32px 28px 8px; }} h1 {{ font-weight: 400; font-size: 22px; margin: 0 0 6px; }}
header p {{ margin: 0; color: rgba(238,234,224,.65); max-width: 52em; }}
main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(560px, 1fr)); gap: 28px; padding: 24px 28px 48px; }}
figure {{ margin: 0; }} img {{ width: 100%; display: block; border-radius: 3px; }}
figcaption {{ margin-top: 8px; }} figcaption b {{ color: #94E6FF; font-weight: 400; margin-right: 6px; }}
figcaption span {{ color: rgba(238,234,224,.62); font-size: 14px; }}
</style></head><body>
<header><h1>The Antimony world: ten concepts</h1>
<p>Unreal Engine 5.8, Lumen, quick previews (1920 x 1080) of one world in ten framings and moods. Pick one to three to take to final.
Built by <code>world/scripts/build_world.py</code> with the looks in <code>world/scripts/concepts.py</code>.</p></header>
<main>
{cards}
</main></body></html>
'''
open(os.path.join(OUT, "index.html"), "w").write(html)
if items:
    files = [os.path.join(OUT, f) for *_, f in items]
    cols = 2
    rows = (len(files) + cols - 1) // cols
    inputs = sum((["-i", f] for f in files), [])
    scale = "".join(f"[{i}:v]scale=960:540[v{i}];" for i in range(len(files)))
    pad = len(files) % cols
    layout = "|".join(f"{(i % cols) * 960}_{(i // cols) * 540}" for i in range(len(files)))
    flt = scale + "".join(f"[v{i}]" for i in range(len(files))) + f"xstack=inputs={len(files)}:layout={layout}:fill=black[o]"
    if len(files) == 1:
        flt = "[0:v]scale=960:540[o]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", flt, "-map", "[o]", "-q:v", "85",
                    os.path.join(OUT, "contact.webp")], check=True)
print(f"{len(items)} concepts on the page")

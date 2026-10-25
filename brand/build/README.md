# Building the identity

Everything is drawn from `geometry.py`, which writes `geo.json`. Run in this folder:

    python3 geometry.py      # the Bond, the Seal and the wordmark
    python3 pixels.py        # 16 and 32 px drawings for the favicon
    python3 exports.py       # one page per export, into pages/
    node render.js           # PNG and PDF into ../exports
    python3 svgs.py          # master SVGs into ../exports/svg
    python3 sting.py && node sting.js   # the motion sting, MP4 (needs ffmpeg)
    python3 book.py          # the brand book, ../index.html

The wordmark's kerning was measured in Chromium from Timeless Serif at weight 420 (`ts-420-0.ttf`, an instance of our licensed font).

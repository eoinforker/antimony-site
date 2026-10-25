"""The brand in use: each mock-up is a standalone page at its true size. The guidelines show them scaled; render.cjs exports them."""
import geo as g

BASE = """<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width={w}"><title>{title}</title><style>
@font-face {{ font-family: "Timeless Serif"; src: url(../fonts/TimelessSerifVF.woff2) format("woff2"); font-weight: 200 700; }}
@font-face {{ font-family: "Commit Mono"; src: url(../fonts/CommitMono-Latin-VF.woff2) format("woff2"); font-weight: 200 700; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {w}; height: {h}; overflow: hidden; background: {bg}; }}
body {{ position: relative; font: 500 16px/1.4 "Timeless Serif", Georgia, serif; -webkit-font-smoothing: antialiased; color: {fg}; }}
.bg {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }}
.gr {{ position: absolute; inset: 0; pointer-events: none; background: url(../img/tex/{grain}.png) 0 0 / 128px 128px; }}
.abs {{ position: absolute; display: block; }}
.mono {{ font: 400 11px/1.5 "Commit Mono", ui-monospace, monospace; letter-spacing: .14em; text-transform: uppercase; }}
{css}
</style></head><body>{body}</body></html>"""

def page(w, h, title, body, bg=g.INK, fg=g.CREAM, grain="grain-light", css=""):
    return BASE.format(w=w if isinstance(w, str) else f"{w}px", h=h if isinstance(h, str) else f"{h}px", title=title, body=body, bg=bg, fg=fg, grain=grain, css=css)

def huge_line(colour, left, top, size, sw=1.2, opacity=1):
    """The line mark drawn huge and thin: a hairline that stays a hairline at any size."""
    return (f'<div class="abs" style="left:{left}px;top:{top}px;width:{size}px;height:{size}px;opacity:{opacity}">'
            + g.line_mark(colour, sw, nonscaling=True, style="width:100%;height:100%;overflow:visible", label="") + '</div>')

TAG = "Software for the people who make the work"

def all_mockups():
    M = {}
    # ---------- social ----------
    M["linkedin-banner"] = (1584, 396, page(1584, 396, "LinkedIn banner",
        '<img class="bg" src="../img/tex/stipple-wide.png" alt="">' + huge_line(g.SKY, 1020, -230, 860, 1.1, .95)
        + f'<div class="abs" style="left:520px;top:166px;width:430px">{g.caps(g.CREAM, g.SKY, style="width:100%;height:auto")}</div>'
        + f'<p class="abs mono" style="left:521px;top:222px;color:rgba(238,234,224,.6);font-size:10.5px;letter-spacing:.3em">{TAG}</p><div class="gr"></div>'))
    M["linkedin-avatar"] = (400, 400, page(400, 400, "Avatar",
        f'<div class="abs" style="left:92px;top:92px;width:216px;height:216px">{g.mark(light=True, style="width:100%;height:100%")}</div><div class="gr"></div>',
        bg=g.CREAM, fg=g.INK, grain="grain-alpha"))
    M["x-header"] = (1500, 500, page(1500, 500, "X header",
        '<img class="bg" src="../img/tex/light-wide.jpg" alt="">' + huge_line("#FFFFFF", 760, -330, 1100, 1.2, .92)
        + f'<p class="abs mono" style="right:48px;top:40px;color:rgba(11,12,12,.62);font-size:10.5px;letter-spacing:.3em">{TAG}</p><div class="gr"></div>'))
    M["link-card"] = (1200, 630, page(1200, 630, "Link card",
        f'<div class="abs" style="left:518px;top:150px;width:164px">{g.stacked(g.CREAM, style="width:100%;height:auto")}</div>'
        + '<div class="abs" style="left:0;right:0;bottom:42px;display:flex;flex-direction:column;align-items:center;gap:13px;color:rgba(11,12,12,.6)">'
        + f'<p style="font-size:11px;letter-spacing:.34em;margin-right:-.34em;text-transform:uppercase">{TAG}</p></div><div class="gr"></div>',
        bg=g.CREAM, fg=g.INK, grain="grain-alpha"))

    # ---------- posters, A series proportion ----------
    PW, PH = 1200, 1697
    cols = lambda c, items, top: "".join(f'<div class="abs" style="left:{x}px;top:{top}px;width:{w}px;color:{c};font-size:14px;line-height:1.42">{t}</div>' for x, w, t in items)
    M["poster-light"] = (PW, PH, page(PW, PH, "Poster: light",
        '<img class="bg" src="../img/tex/light-poster.jpg" alt="">' + huge_line("#FFFFFF", -230, 150, 1660, 1.3, .95)
        + f'<p class="abs mono" style="left:60px;top:58px;color:rgba(11,12,12,.66)">The Break</p><p class="abs mono" style="right:60px;top:58px;color:rgba(11,12,12,.66)">Sixteen degrees</p>'
        + f'<div class="abs" style="left:60px;bottom:70px;width:470px">{g.serif(g.CREAM, g.SKY, style="width:100%;height:auto")}</div>'
        + cols("rgba(238,234,224,.9)", [(700, 200, "A tile of dark stone, split by a seam at sixteen degrees from upright. A crystal grows in the break."),
                                         (930, 210, "The crystal holds light, the way water does. It is the only colour in the mark.")], 1530)
        + '<div class="gr"></div>'))
    M["poster-paper"] = (PW, PH, page(PW, PH, "Poster: paper",
        huge_line(g.PRU, 260, 640, 1500, 1.3, .9)
        + f'<div class="abs" style="left:60px;top:66px;width:1080px">{g.serif(g.INK, g.PRU, style="width:100%;height:auto")}</div>'
        + '<div class="abs" style="left:60px;right:60px;top:372px;border-top:1.5px solid #0B0C0C"></div>'
        + '<p class="abs mono" style="left:60px;top:392px;color:rgba(11,12,12,.7)">Antimony</p>'
        + f'<p class="abs" style="left:430px;top:386px;width:620px;font:500 50px/1.06 \'Timeless Serif\',serif;letter-spacing:-.02em">A stone split open, with a crystal grown in the break.</p>'
        + f'<div class="abs" style="left:60px;bottom:64px;width:58px">{g.mark(style="width:100%;height:auto")}</div>'
        + cols("rgba(11,12,12,.82)", [(430, 200, "Antimony makes software for the people who make the work."),
                                       (660, 200, "Element 51. Its ore, stibnite, grows in long grey crystals."),
                                       (890, 250, "The mark is measured on a square of 100 units. Every point in it is found from a handful of numbers.")], 1554)
        + '<div class="gr"></div>', bg=g.CREAM, fg=g.INK, grain="grain-alpha"))
    M["poster-stone"] = (PW, PH, page(PW, PH, "Poster: stone",
        '<img class="bg" src="../img/tex/chars-poster.png" alt="">' + huge_line(g.SKY, -330, 230, 1860, 1.2, .95)
        + f'<div class="abs" style="left:60px;top:76px;width:1080px">{g.caps(g.CREAM, g.SKY, style="width:100%;height:auto")}</div>'
        + cols("rgba(238,234,224,.84)", [(700, 200, "The characters are the mark's own drawing, set as text: the stone, the seam, the cavity, the crystal."),
                                          (930, 210, TAG + ".")], 1540)
        + '<div class="gr"></div>'))

    # ---------- print ----------
    card_css = ".card { position: absolute; left: 0; top: 0; width: 85mm; height: 55mm; overflow: hidden; }"
    M["card-front"] = ("85mm", "55mm", page("85mm", "55mm", "Business card, front",
        f'<div class="card"><div class="abs" style="left:6mm;top:6.4mm;width:29mm">{g.caps(g.INK, g.PRU, style="width:100%;height:auto")}</div>'
        '<p class="abs" style="left:6mm;bottom:12.2mm;font:600 9.6pt/1.1 \'Timeless Serif\',serif;letter-spacing:-.005em">E&oacute;in Forker</p>'
        '<p class="abs" style="left:6mm;bottom:8mm;font:500 7.6pt/1.1 \'Timeless Serif\',serif;color:rgba(11,12,12,.66)">Founder</p>'
        '<div class="gr" style="background-size:96px 96px"></div></div>',
        bg=g.CREAM, fg=g.INK, grain="grain-alpha", css=card_css))
    M["card-back"] = ("85mm", "55mm", page("85mm", "55mm", "Business card, back",
        f'<div class="card"><img class="bg" src="../img/tex/stone-card.jpg" alt=""><div class="abs" style="left:34.5mm;top:19.5mm;width:16mm;height:16mm">{g.mark(**g.mark_for(g.INK, light=True), style="width:100%;height:100%")}</div>'
        '</div>', css=card_css))
    letter = ("<p>Dear printer,</p><p>Thank you for taking on our first run of cards and letterheads. A few notes, so the colours come out as we mean them.</p>"
              "<p>The paper colour is cream, #EEEAE0 on screen. Please match it to a drawdown on the stock we have chosen rather than converting it by formula, and send us the drawdown before the run.</p>"
              "<p>The crystal in the mark is the only bright colour we use. If it cannot be printed as a clean, light sky blue on this stock, print the mark in one colour instead; the files for that are in the kit, in the folder called one-colour.</p>"
              "<p>The wordmark and the mark are supplied as outlines, so no fonts are needed. Please do not redraw, stretch or recolour them.</p><p>With thanks,</p>")
    M["letterhead"] = ("210mm", "297mm", page("210mm", "297mm", "Letterhead",
        f'<div class="abs" style="left:20mm;top:18mm;width:46mm">{g.lockup(g.CREAM, style="width:100%;height:auto")}</div>'
        '<p class="abs" style="left:122mm;top:20.4mm;font:500 8.5pt/1.5 \'Timeless Serif\',serif;color:rgba(11,12,12,.7)">25 October 2026</p>'
        f'<div class="abs" style="left:20mm;top:70mm;width:120mm;font:500 10.5pt/1.5 \'Timeless Serif\',serif;color:#141311;display:grid;gap:4.2mm">{letter}'
        '<p style="margin-top:6mm;font-weight:600">E&oacute;in Forker<br><span style="font-weight:500;color:rgba(11,12,12,.66)">Founder</span></p></div>'
        '<div class="abs" style="left:20mm;right:20mm;bottom:16mm;border-top:.25mm solid rgba(11,12,12,.5);padding-top:3.2mm;display:flex;justify-content:space-between;align-items:center;font:400 6.4pt/1 \'Commit Mono\',monospace;letter-spacing:.16em;text-transform:uppercase;color:rgba(11,12,12,.62)">'
        f'<span>Antimony</span><span>{TAG}</span></div>',
        bg=g.CREAM, fg=g.INK, grain="grain-none"))
    # ---------- presentations ----------
    M["deck-title"] = (1920, 1080, page(1920, 1080, "Deck title slide",
        '<img class="bg" src="../img/tex/stipple-deck.png" alt="">' + huge_line(g.SKY, 1180, -170, 1420, 1.2, .9)
        + f'<div class="abs" style="left:96px;top:92px;width:300px">{g.caps(g.CREAM, g.SKY, style="width:100%;height:auto")}</div>'
        + '<h1 class="abs" style="left:92px;top:540px;width:1080px;font:400 112px/.98 \'Timeless Serif\',serif;letter-spacing:-.035em">Software for the people who make the work.</h1>'
        + '<p class="abs mono" style="left:96px;bottom:92px;color:rgba(238,234,224,.6);font-size:13px">October 2026</p><div class="gr"></div>'))
    # ---------- email ----------
    sig_css = "body { font-family: Georgia, 'Times New Roman', serif; }"
    M["email-signature"] = (600, 190, page(600, 190, "Email signature",
        '<div class="abs" style="left:28px;top:28px;right:28px">'
        '<p style="font:bold 15px/1.35 Georgia,serif;color:#0B0C0C">E&oacute;in Forker</p>'
        '<p style="font:14px/1.35 Georgia,serif;color:#5B5A56">Founder, Antimony</p>'
        '<div style="margin-top:18px;border-top:1px solid #DAD6CC;padding-top:18px;display:flex;align-items:center;gap:16px">'
        f'<span style="display:block;width:162px">{g.lockup(g.CREAM, style="width:100%;height:auto")}</span>'
        f'<span style="font:11px/1.4 Georgia,serif;color:#77756F;letter-spacing:.02em">{TAG}.</span></div></div>',
        bg="#FFFFFF", fg=g.INK, grain="grain-none", css=sig_css))
    return M

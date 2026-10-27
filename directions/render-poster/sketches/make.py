import random
W,H=640,360
random.seed(7)
def poster(cx,base,h=120,stand=False):
    w=h*0.66; x=cx-w/2; y=base-h
    s=f'<defs><radialGradient id="g{cx}{base}" cx="50%" cy="50%" r="60%"><stop offset="0" stop-color="#cfe6ff" stop-opacity=".55"/><stop offset="1" stop-color="#cfe6ff" stop-opacity="0"/></radialGradient></defs>'
    s+=f'<ellipse cx="{cx}" cy="{y+h/2}" rx="{w*1.6}" ry="{h*0.95}" fill="url(#g{cx}{base})"/>'
    if stand: s+=f'<rect x="{cx-w*0.35}" y="{base}" width="3" height="{h*0.12}" fill="#0b1426"/><rect x="{cx+w*0.35-3}" y="{base}" width="3" height="{h*0.12}" fill="#0b1426"/>'
    s+=f'<rect x="{x-3}" y="{y-3}" width="{w+6}" height="{h+6}" rx="2" fill="#0a1220"/>'
    s+=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#e9eef3"/>'
    s+=f'<rect x="{x}" y="{y+h*0.62}" width="{w}" height="{h*0.38}" fill="#5a78b8" opacity=".55"/>'
    m=w*0.32; mx=cx-m/2; my=y+h*0.22
    s+=f'<rect x="{mx}" y="{my}" width="{m}" height="{m}" rx="{m*0.22}" fill="#141311"/>'
    s+=f'<path d="M{mx+m*.586} {my+m*.215}L{mx+m*.706} {my+m*.467}L{mx+m*.678} {my+m*.563}L{mx+m*.414} {my+m*.815}L{mx+m*.294} {my+m*.563}L{mx+m*.322} {my+m*.467}Z" fill="#94E6FF"/>'
    s+=f'<rect x="{cx-w*0.28}" y="{y+h*0.5}" width="{w*0.56}" height="1.6" fill="#141311" opacity=".7"/>'
    s+=f'<rect x="{cx-w*0.32}" y="{y+h*0.92}" width="{w*0.64}" height="1.2" fill="#141311" opacity=".5"/>'
    return s
def rain(n=90,op=.35,area=(0,0,W,H)):
    s=''
    for _ in range(n):
        x=random.uniform(area[0],area[2]); y=random.uniform(area[1],area[3]); l=random.uniform(8,18)
        s+=f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x-1.5:.1f}" y2="{y+l:.1f}" stroke="#bcd3ff" stroke-width=".7" opacity="{op}"/>'
    return s
def mist(y,h,op=.5):
    s=''
    for i in range(6):
        s+=f'<ellipse cx="{random.uniform(0,W):.0f}" cy="{y+random.uniform(-h/3,h/3):.0f}" rx="{random.uniform(140,260):.0f}" ry="{h/2:.0f}" fill="#9fb4e0" opacity="{op*random.uniform(.25,.5):.2f}"/>'
    return s
def flowers(y0,y1,n=160,col="#a9c8ff",r=(1,2.4)):
    return ''.join(f'<circle cx="{random.uniform(0,W):.1f}" cy="{random.uniform(y0,y1):.1f}" r="{random.uniform(*r):.1f}" fill="{col}" opacity="{random.uniform(.5,.95):.2f}"/>' for _ in range(n))
def bg(top,bot):
    k=str(abs(hash(top+bot)))
    return (f'<defs><linearGradient id="bg{k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
            f'<stop offset="1" stop-color="{bot}"/></linearGradient></defs><rect width="{W}" height="{H}" fill="url(#bg{k})"/>')
def wall(top=0,bot=270):
    s=f'<rect x="0" y="{top}" width="{W}" height="{bot-top}" fill="#1d2f57"/>'
    for x in range(0,W,107): s+=f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bot}" stroke="#14223f" stroke-width="1.5"/>'
    for y in range(top,bot,54): s+=f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#14223f" stroke-width="1.5"/>'
    return s
S={}
S[1]=bg('#0e1a36','#0a1222')+wall()+'<rect y="270" width="640" height="90" fill="#0d1630"/>'+'<rect x="268" y="280" width="104" height="70" fill="#9fc3ff" opacity=".12"/>'+poster(320,262,130)+mist(282,40,.9)+rain(140)
S[2]=bg('#0e1a36','#0a1222')+wall()+'<rect y="270" width="640" height="90" fill="#0d1630"/>'+poster(320,262,130)+flowers(262,300,150)+''.join(f'<line x1="{x}" y1="285" x2="{x+30}" y2="345" stroke="#0a1224" stroke-width="1.2"/>' for x in range(30,640,90))+flowers(300,350,60)+rain(50,.25)
S[3]=bg('#2a3f72','#121f40')+''.join(f'<polygon points="{x-w},{250} {x+random.uniform(-6,6)},{t} {x+w},{250}" fill="#0f1b3a" opacity=".95"/>' for x,t,w in [(90,70,26),(150,120,18),(470,40,34),(540,95,22),(395,150,16)])+mist(235,50,.8)+'<rect y="250" width="640" height="110" fill="#14244c"/>'+flowers(250,360,420,"#7fa6ff",(1,2.8))+poster(320,268,96,True)+rain(70,.25)
S[4]=bg('#1b2b55','#0d1730')+''.join(f'<path d="M{x} 260V140Q{x+45} 90 {x+90} 140V260" fill="none" stroke="#2b3f6e" stroke-width="16"/>' for x in (40,180,370,510))+'<path d="M245 262V120Q320 50 395 120V262" fill="none" stroke="#2f4575" stroke-width="20"/>'+'<rect y="262" width="640" height="98" fill="#111d3c"/>'+mist(250,40,.7)+flowers(262,350,300,"#e8f0ff",(1,2.2))+poster(320,258,104)
S[5]=bg('#33508a','#16244a')+'<rect x="40" y="168" width="560" height="14" rx="7" fill="#0f1b3a" opacity=".95"/>'+''.join(f'<rect x="{x}" y="182" width="12" height="60" fill="#0f1b3a" opacity=".95"/>' for x in (120,250,380,510))+mist(215,50,.9)+'<rect y="240" width="640" height="120" fill="#1a2c58"/>'+flowers(240,360,380,"#c4d8ff",(1,2.6))+poster(320,282,96,True)
S[6]=bg('#0f1c3a','#0a1224')+wall(0,190)+'<rect y="190" width="640" height="170" fill="#0c1733"/>'+'<g transform="translate(0,392) scale(1,-1)" opacity=".45">'+poster(320,182,110)+'</g>'+poster(320,182,110)+''.join(f'<ellipse cx="{random.uniform(0,640):.0f}" cy="{random.uniform(215,350):.0f}" rx="{random.uniform(6,18):.0f}" ry="2" fill="none" stroke="#9fb8ef" stroke-width=".6" opacity=".5"/>' for _ in range(22))+mist(200,30,.5)
S[7]=bg('#060b18','#060b18')+'<rect x="150" y="40" width="340" height="240" fill="#30508f"/>'+mist(200,90,.9)+''.join(f'<rect x="{x}" y="{y}" width="3" height="5" fill="#cfe0ff" opacity=".6"/>' for x,y in [(190,150),(230,130),(420,140),(450,160),(380,120)])+rain(160,.45,(150,40,490,280))+'<rect x="0" y="0" width="150" height="360" fill="#0b1328"/><rect x="490" y="0" width="150" height="360" fill="#0b1328"/><rect x="0" y="0" width="640" height="40" fill="#0b1328"/>'+'<rect y="280" width="640" height="80" fill="#0e1834"/>'+poster(320,285,118)
S[8]=bg('#13224a','#0b1430')+'<rect x="0" y="40" width="640" height="190" fill="#1e3160"/>'+'<rect x="0" y="40" width="90" height="320" fill="#162851"/><rect x="550" y="40" width="90" height="320" fill="#162851"/>'+'<ellipse cx="320" cy="300" rx="230" ry="44" fill="#0a1430"/>'+''.join(f'<ellipse cx="{x}" cy="{y}" rx="13" ry="4" fill="#2f5a6e" opacity=".7"/>' for x,y in [(200,292),(260,310),(410,300),(450,288),(360,318)])+'<ellipse cx="110" cy="40" rx="190" ry="70" fill="#0d1a3a"/>'+poster(320,228,108)+rain(60,.25)
S[9]=bg('#16264f','#0b1430')+''.join(f'<polygon points="{x},0 {x+40},0 {x+150},360 {x+70},360" fill="#b7cdff" opacity=".08"/>' for x in (150,260,380))+''.join(f'<rect x="{x}" y="0" width="{w}" height="360" fill="#050a17"/>' for x,w in [(40,26),(120,16),(200,22),(430,24),(510,30),(590,18)])+mist(300,60,.8)+'<rect y="300" width="640" height="60" fill="#0e1a38"/>'+poster(320,300,112)
S[10]=bg('#2c4a8a','#5b78b8')+''.join(f'<rect x="{x}" y="{t}" width="{w}" height="{230-t}" fill="#17295a" opacity=".9"/>' for x,t,w in [(70,120,8),(520,90,10),(560,140,6)])+mist(225,70,1.2)+'<rect y="250" width="640" height="110" fill="#16244a"/><rect y="250" width="640" height="6" fill="#26396a"/>'+''.join(f'<rect x="{x}" y="236" width="5" height="14" fill="#26396a"/>' for x in range(10,640,22))+poster(320,300,104,True)
names={1:'Mist',2:'Flowers',3:'Blue field',4:'Ruins',5:'The plate',6:'Still water',7:'Undercity',8:'Pond courtyard',9:'Moon forest',10:'Above the clouds'}
cells=''.join(f'<figure><svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">{S[i]}</svg><figcaption><b>{i:02d}</b> {names[i]}</figcaption></figure>' for i in range(1,11))
html=f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;background:#EEEAE0;font:15px Georgia,serif;color:#0B0C0C;padding:28px}}main{{display:grid;grid-template-columns:repeat(2,1fr);gap:22px 22px}}figure{{margin:0}}svg{{width:100%;display:block;border-radius:2px}}figcaption{{margin-top:8px;letter-spacing:.02em}}b{{font-weight:400;opacity:.5;margin-right:8px}}h1{{font-weight:400;font-size:13px;letter-spacing:.3em;margin:0 0 20px}}</style></head><body><h1>POSTER 1: TEN COMPOSITIONS</h1><main>{cells}</main></body></html>'
open('sheet.html','w').write(html)

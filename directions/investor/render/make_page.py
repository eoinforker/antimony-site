# Fill the page template with the wordmark and the frame data: python3 make_page.py
import json, os
H = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(H, 'page.html')).read()
wm = open('/tmp/claude-0/-home-user/5a08d946-6e0e-5f87-9dad-cc05a4b0877f/scratchpad/wordmark.txt').read().split('\n', 1)
fr = json.load(open(os.path.join(H, '..', 'assets', 'hero', 'frame.json')))
ph = '.ph { background-image: url(%s); }\n@media (max-aspect-ratio: 4/5) { .ph { background-image: url(%s); } }' % (fr['landscape']['ph'], fr['portrait']['ph'])
fr = {k: {kk: vv for kk, vv in fr[k].items() if kk != 'ph'} for k in ('landscape', 'portrait')}
out = tpl.replace('__VB__', wm[0].strip()).replace('__WM__', wm[1].strip().replace('<defs></defs>', '')).replace('__PH__', ph).replace('__FRAME__', json.dumps(fr, separators=(',', ':')))
open(os.path.join(H, '..', 'index.html'), 'w').write(out)
print(len(out.encode()))

# Writes ../index.html from page.html with the wordmark inlined.
import os
H = os.path.dirname(os.path.abspath(__file__))
wm = open(os.path.join(H, 'wordmark.txt')).read().split('\n', 1)
s = open(os.path.join(H, 'page.html')).read().replace('{{VIEWBOX}}', wm[0].strip()).replace('{{WORDMARK}}', wm[1].strip())
open(os.path.join(H, '..', 'index.html'), 'w').write(s)
print('index.html', len(s))

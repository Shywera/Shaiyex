# every class we toggle on <body> must not also be a standalone rule,
# or the rule lands on the body itself. this is what hid the whole page.
import re, io
s = io.open(r'C:/Users/krist/shaiyex/public/beat/index.html', encoding='utf-8').read()
css = re.search(r'<style>(.*?)</style>', s, re.S).group(1)
js  = re.search(r'<script>(.*?)</script>', s, re.S).group(1)
body_classes = set(re.findall(r"document\.body\.classList\.(?:toggle|add)\('([^']+)'", js))
bare = set()
for c in body_classes:
    if re.search(r'(^|[\s,}])\.' + re.escape(c) + r'\s*[,{]', css):
        bare.add(c)
print("classes toggled on body :", sorted(body_classes))
print("also used as a bare rule:", sorted(bare) if bare else "none")
raise SystemExit(1 if bare else 0)

#!/usr/bin/env python3
"""Bundle site/ into a single HTML page (CSS + JS inlined) + data/*.json, for hosting as a Claude artifact."""
import os, re, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1]
site = os.path.join(ROOT, "site")
html = open(os.path.join(site, "index.html"), encoding="utf-8").read()
css = open(os.path.join(site, "styles.css"), encoding="utf-8").read()
js = open(os.path.join(site, "app.js"), encoding="utf-8").read()
head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
head = re.sub(r'\s*<meta name="viewport"[^>]*>|\s*<link rel="stylesheet" href="styles.css">', "", head)
body = body.replace('<script src="app.js"></script>', "<script>\n" + js + "\n</script>")
os.makedirs(os.path.join(out, "data"), exist_ok=True)
with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
    f.write(head.strip() + "\n<style>\n" + css + "\n</style>\n" + body.strip() + "\n")
for n in os.listdir(os.path.join(site, "data")):
    shutil.copy(os.path.join(site, "data", n), os.path.join(out, "data", n))
print("built", out)

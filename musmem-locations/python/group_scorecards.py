import os
import re
from collections import defaultdict

d = "/tmp/scorecards"
files = sorted(os.listdir(d))

contests = defaultdict(list)
for f in files:
    if not f.endswith(".png"):
        continue
    # slug is everything before -imgN.png or .png
    m = re.match(r'^(.+?)(-img(\d+))?\.png$', f)
    if m:
        slug = m.group(1)
        img_n = int(m.group(3)) if m.group(3) else 0  # 0 = base (no suffix)
        contests[slug].append((img_n, f))

for slug, images in sorted(contests.items()):
    images.sort(key=lambda x: (x[0] if x[0] > 0 else 999))  # img1,img2,img3 first, base last
    print(f"\nSLUG: {slug}")
    for n, f in images:
        print(f"  {'img'+str(n) if n else 'base'}: {f}")

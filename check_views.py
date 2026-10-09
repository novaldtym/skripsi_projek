html = open('templates/index.html', encoding='utf-8').read()
lines = html.splitlines()
for i, l in enumerate(lines):
    if 'id="view-' in l or "id='view-" in l:
        print(f"Line {i+1}: {l.strip()[:100]}")

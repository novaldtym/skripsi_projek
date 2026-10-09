with open('Web_Dashboard_Server.py', 'r', encoding='utf-8') as f:
    for i, l in enumerate(f):
        if "@app.route(" in l:
            print(f"{i+1}: {l.strip()}")

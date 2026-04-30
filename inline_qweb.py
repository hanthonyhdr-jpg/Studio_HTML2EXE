import sys

file_path = r'c:\Users\hanth\OneDrive\Desktop\COLOR CHAT HMTL\color-chart-app\assets\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

qweb_path = r'c:\Users\hanth\OneDrive\Desktop\COLOR CHAT HMTL\color-chart-app\assets\qwebchannel.js'
with open(qweb_path, 'r', encoding='utf-8') as f:
    qweb = f.read()

if '<script src="qwebchannel.js"></script>' in content:
    content = content.replace('<script src="qwebchannel.js"></script>', '<script>\n' + qweb + '\n</script>')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Inlined QWebChannel successfully!')
else:
    print('Script tag not found.')

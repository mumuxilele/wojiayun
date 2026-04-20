import re
path = '/www/wwwroot/wojiayun/business-userH5/application_form_v2.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 465 (0-indexed 464): hide the first card-title
if 'card-title">' in lines[464]:
    lines[464] = lines[464].replace('card-title">', 'card-title" style="display:none">')
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Done - hid first card-title')
else:
    print('Not found:', lines[464])

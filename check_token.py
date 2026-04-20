import tokenize
try:
    with open('/tmp/broken_app.py', 'rb') as f:
        tokenize.tokenize(f.readline)
except tokenize.TokenError as e:
    print('TokenError:', e)
except SyntaxError as e:
    print('SyntaxError at line', e.lineno)
    print('Msg:', e.msg)

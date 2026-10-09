
import sys
try:
    print('Trying print...')
    sys.stdout.flush()
    with open('test_handle.txt', 'w') as f:
        f.write('SUCCESS')
except Exception as e:
    with open('test_handle.txt', 'w') as f:
        f.write(f'ERROR: {e}')

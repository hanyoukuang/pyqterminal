import sys
import traceback
import faulthandler
faulthandler.enable()

def catch_exceptions(type, value, tb):
    traceback.print_exception(type, value, tb)
    
sys.excepthook = catch_exceptions

with open('pty_demo.py') as f:
    code = f.read()

exec(code, {'__name__': '__main__'})

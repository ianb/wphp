from wphp import PHPApp
from paste.fixture import TestApp
import os
import logging
logging.basicConfig()

class PLogger:

    def debug(self, msg, *args, **kw):
        if args:
            msg = msg % args
        if kw:
            msg = msg % kw
        print msg

    info = warn = warning = fatal = debug

wsgi_app = PHPApp(os.path.join(os.path.dirname(__file__), 'php-files'),
                  logger=PLogger())
app = TestApp(wsgi_app)

def test_php():
    res = app.get('/test.php')
    assert '2 = 2' in res
    res = app.post('/test2.php?name=Guy', {'myname': 'Stan'})
    print res
    assert "I've been POSTed" in res
    assert 'Hello, Guy' in res
    assert 'My name is Stan' in res

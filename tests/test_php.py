from wphp import PHPApp
from paste.fixture import TestApp
import os

wsgi_app = PHPApp(os.path.join(os.path.dirname(__file__), 'php-files'))
app = TestApp(wsgi_app)

def test_php():
    res = app.get('/test.php')
    assert '2 = 2' in res
    

# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
#

class PHPApp(object):

    def __init__(self, base_dir):
        self.base_dir = base_dir

    def __call__(self, environ, start_response):
        pass

def make_app(global_conf, **kw):
    return PHPApp(**kw)


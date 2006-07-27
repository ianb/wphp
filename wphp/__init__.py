# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
#
import threading
import os
import socket
import logging
import atexit
import signal
import time
import posixpath
from paste import fileapp
from wphp import fcgi_app

here = os.path.dirname(__file__)
default_php_ini = os.path.join(here, 'default-php.ini')

class PHPApp(object):

    def __init__(self, base_dir, fcgi_port=None,
                 php_script='php-cgi',
                 php_ini=default_php_ini,
                 php_options=None,
                 search_fcgi_port_starting=10000,
                 logger='wphp'):
        self.base_dir = base_dir
        self.fcgi_port = fcgi_port
        self.php_script = php_script
        self.php_ini = php_ini
        if php_options is None:
            php_options = {}
        self.php_options = php_options
        self.search_fcgi_port_starting = search_fcgi_port_starting
        if isinstance(logger, basestring):
            logger = logging.getLogger(logger)
        self.logger = logger
        
        self.lock = threading.Lock()
        self.child_pid = None
        self.fcgi_app = None

    def __call__(self, environ, start_response):
        if self.child_pid is None:
            if environ['wsgi.multiprocess']:
                environ['wsgi.errors'].write(
                    "wphp doesn't support multiprocess apps very well yet")
            self.create_child()
        path_info = environ.get('PATH_INFO', '').lstrip('/')
        script_filename, path_info = self.find_script(self.base_dir, path_info)
        if script_filename is None:
            exc = httpexceptions.HTTPNotFound()
            return exc(environ, start_response)
        script_name = posixpath.join(environ.get('SCRIPT_NAME', ''), script_filename)
        script_filename = posixpath.join(self.base_dir, script_filename)
        environ['SCRIPT_NAME'] = script_name
        environ['SCRIPT_FILENAME'] = os.path.join(self.base_dir, script_filename)
        environ['PATH_INFO'] = path_info
        ext = posixpath.splitext(script_filename)[1]
        if ext != '.php':
            app = fileapp.FileApp(script_filename)
            return app(environ, start_response)
        return self.fcgi_app(environ, start_response)

    def find_script(self, base, path):
        path_info = ''
        while 1:
            full_path = os.path.join(base, path)
            if not os.path.exists(full_path):
                if not path:
                    return None, None
                path_info = '/' + os.path.basename(path) + path_info
                path = os.path.dirname(path)
            else:
                return path, path_info
            

    def create_child(self):
        self.lock.acquire()
        try:
            if self.child_pid:
                return
            if self.logger:
                self.logger.info('Spawning PHP process')
            if self.fcgi_port is None:
                self.fcgi_port = self.find_port()
            self.spawn_php(self.fcgi_port)
            self.fcgi_app = fcgi_app.FCGIApp(
                connect=('127.0.0.1', self.fcgi_port),
                filterEnviron=False)
        finally:
            self.lock.release()

    def spawn_php(self, port):
        cmd = [self.php_script,
               '-b',
               '127.0.0.1:%s' % self.fcgi_port]
        if self.php_ini:
            cmd.extend([
                '-c', self.php_ini])
        for name, value in self.php_options.items():
            cmd.extend([
                '-d', '%s=%s' % (name, value)])
        pid = os.fork()
        if pid:
            self.child_pid = pid
            if self.logger:
                self.logger.info(
                    'PHP process spawned in PID %s, port %s'
                    % (pid, self.fcgi_port))
            atexit.register(self.close)
            # PHP doesn't start up *quite* right away, so we give it a
            # moment to be ready to accept connections
            time.sleep(0.1)
            return
        os.execvpe(
            self.php_script,
            cmd,
            os.environ)

    def find_port(self):
        host = '127.0.0.1'
        port = self.search_fcgi_port_starting
        while 1:
            s = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind((host, port))
            except socket.error, e:
                port += 1
            else:
                s.close()
                return port

    def close(self):
        # @@: Note, in a multiprocess setup this cannot
        # be handled this way
        if self.child_pid:
            if self.logger:
                self.logger.info(
                    "Killing PHP subprocess %s"
                    % self.child_pid)
            os.kill(self.child_pid, signal.SIGKILL)

def make_app(global_conf, **kw):
    if 'fcgi_port' in kw:
        kw['fcgi_port'] = int(kw['fcgi_port'])
    if 'search_fcgi_port_starting':
        kw['search_fcgi_port_starting'] = int(kw['search_fcgi_port_starting'])
    kw.setdefault('php_options', {})
    for name, value in kw.items():
        if name.startswith('option '):
            name = name[len('option '):].strip()
            kw['php_options'][name] = value
            del kw[name]
    if 'base_dir' not in kw:
        raise ValueError(
            "base_dir option is required")
    return PHPApp(**kw)


from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='wphp',
      version=version,
      description="WSGI-to-PHP connector",
      long_description="""\
This module allows you to run PHP processes inside of Python, using a
WSGI gateway.  This way PHP applications can appear like normal Python
WSGI applications, and WSGI middleware routing and filters can all be
applied in front of them.  For instance, WSGI middleware-based
authentication or authorization, routing, deployment, or styling
filters (like `WSGIOverlay <http://pythonpaste.org/wsgioverlay/>`_).

You can use it like::

    from wphp import PHPApp
    my_php_app = PHPApp('/path/to/php-files',
                        php_options={'magic_quote_gpc': 'Off'})

And ``my_php_app`` will be a WSGI application you can embed in other
Python applications.

Available in a `Subversion repository
<http://http://svn.pythonpaste.org/Paste/wphp/trunk#egg=wphp-dev>`_,
or installation with ``easy_install wphp==dev``.  (No formal release
has been made yet)
""",
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Paste',
        'License :: OSI Approved :: MIT License',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
      ],
      keywords='wsgi php web',
      author='Ian Bicking',
      author_email='ianb@colorstudy.com',
      url='http://pythonpaste.org/wphp',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'flup',
        'Paste',
      ],
      entry_points="""
      [paste.app_factory]
      main = wphp:make_app
      """,
      )
      

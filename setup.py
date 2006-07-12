from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='wphp',
      version=version,
      description="WSGI-to-PHP connector",
      long_description="""\
""",
      classifiers=[], # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      keywords='wsgi php web',
      author='Ian Bicking',
      author_email='ianb@colorstudy.com',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      [paste.app_factory]
      main = wphp:make_app
      """,
      )
      

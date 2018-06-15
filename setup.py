#!/usr/bin/env python3

from distutils.core import setup

setup(name='lcm-mon',
    version='1.0',
    description='Monitor program for LCM',
    author='Siddharth Trehan',
    author_email='trehans@mit.edu',
    url='http://www.github.com/trehansiddharth/lcm-mon',
    packages=['lcm_mon'],
    install_requires=[
        "urwid",
        "lcm",
        "matplotlib",
        "numpy"
    ],
    scripts=["bin/lcm-mon"]
)

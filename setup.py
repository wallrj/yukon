# Copyright Richard Wall.
# See LICENSE for details.

from setuptools import setup, find_packages
setup(
    name="yukon",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'click',
        'constantly',
        'pyrsistent',
    ],
    entry_points={
        'console_scripts': [
            'yukon = yukon:main',
        ],
    },
)

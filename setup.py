"""Travis bot for Discord."""

from os import path
from setuptools import setup, find_packages


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='discord-travisbot',
    version='0.0.1.dev20170515',  # see PEP-0440
    author='Yoan Blanc',
    author_email='yoan@dosimple.ch',
    homepage='https://github.com/greut/travisbot',
    license='https://opensource.org/licenses/BSD-3-Clause',
    description=__doc__,
    long_description=long_description,
    packages=find_packages(exclude=('contrib', 'docs', 'tests')),
    keywords='discord asyncio bot',
    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Education',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
    ),
    install_requires=(
        'aiohttp>=2.0.0'
    ),
    extras_requires={
        'fast': ('cchardet', 'aiodns'),  # making it faster (recommended)
        'qa': ('flake8', 'isort', 'pycodestyle', 'pydocstyle', 'rstcheck'),
    }
)

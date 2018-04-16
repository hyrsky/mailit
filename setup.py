import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "mailit",
    version = "0.0.1",
    license = "MIT",
    author = "Santeri Hurnanen",
    author_email = "santeri@oikeuttaelaimille.fi",
    description = ("Simple mandill API wrapper."),
    url = "https://github.com/hyrsky/mailit",
    packages=["mailit"],
    entry_points={
        "console_scripts": [
            "mailit=mailit.__main__:main"
        ]
    },
    long_description=read("README.md"),
    install_requires=["mandrill"],
    tests_require=["pytest"],
)

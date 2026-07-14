# mainproject/setup.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="Ariel Encryption Extension",
    ext_modules=cythonize(
        "prospero/ariel/encryption.py",
        compiler_directives={"language_level": "3", "always_allow_keywords": True},
    ),
)

from setuptools import setup, Extension
from Cython.Build import cythonize
import glob

vterm_sources = glob.glob("vendor/libvterm/src/*.c")

extensions = [
    Extension(
        "pyqterminal.cyvterm",
        sources=["pyqterminal/cyvterm.pyx"] + vterm_sources,
        include_dirs=["vendor/libvterm/include"],
        extra_compile_args=["-std=c99", "-O3", "-march=native", "-flto"],
        extra_link_args=["-O3", "-flto"],
    )
]

setup(
    name="pyqterminal",
    packages=["pyqterminal"],
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
            'initializedcheck': False,
        }
    ),
)

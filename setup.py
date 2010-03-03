from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext

mod1 = Extension('speedstack', sources=['speedstack.c'])
#mod2 = Extension('FileWriteBuffer', sources=['writefile.c'])

setup(name="pyrd", version="0.1", description='what', ext_modules=[mod1])


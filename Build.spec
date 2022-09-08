# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import gooey
gooey_root = os.path.dirname(gooey.__file__)
gooey_assets = Tree(os.path.join(gooey_root, 'assets'), prefix = 'gooey/assets')

a = Analysis(['main.py'],
             pathex=[],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             )
pyz = PYZ(a.pure)

options = [('u', None, 'OPTION')]

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          options,
          gooey_languages, # Add them in to collected files
          gooey_images, # Same here.
          name='main',
          debug=False,
          strip=None,
          upx=True,
          console=False,
          icon=os.path.join(gooey_root, 'assets', 'GameIcon.bmp'))

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='NetTools')

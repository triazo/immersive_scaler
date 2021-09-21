# (global-set-key (kbd "C-c b") (lambda () (interactive) (shell-command "\"C:/Program Files/7-Zip/7z.exe\" a -tzip ../armature_tweak.zip ../armature_tweak")))
#
#

import importlib
importlib.invalidate_caches()

import armature_tweak.operations as atops
import armature_tweak.ui as atui

# from .operations import ops_register
# from .operations import ops_unregister
# from .ui import ui_register
# from .ui import ui_unregister


bl_info = {
    "name": "Armature tuning",
    "category": "3D View",
    'author': 'triazo',
    'version': (0, 2),
    'blender': (2, 80, 0),
    'location': 'View3D',
    # 'warning': '',
}

def register():
    print(__name__)
    importlib.reload(atops)
    importlib.reload(atui)
    atui.ui_register()
    atops.ops_register()

def unregister():
    atui.ui_unregister()
    atops.ops_unregister()

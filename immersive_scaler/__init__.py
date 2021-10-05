# (global-set-key (kbd "C-c b") (lambda () (interactive) (shell-command "\"C:/Program Files/7-Zip/7z.exe\" a -tzip ../immersive_scaler.zip ../immersive_scaler")))
#
#

import importlib
importlib.invalidate_caches()

import immersive_scaler.operations as atops
import immersive_scaler.ui as atui

# from .operations import ops_register
# from .operations import ops_unregister
# from .ui import ui_register
# from .ui import ui_unregister


bl_info = {
    "name": "Immersive Scaler",
    "category": "3D View",
    'author': 'triazo',
    'version': (0, 2, 5),
    'blender': (2, 81, 0),
    'location': 'View3D',
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

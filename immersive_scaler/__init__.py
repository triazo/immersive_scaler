# Currently built with
#
# (global-set-key (kbd "C-c b") (lambda () (interactive) (shell-command "zip -r ../immersive_scaler.zip ../immersive_scaler")))
#
# Or for blender 4.2+
#
# (global-set-key (kbd "C-c b") (lambda () (interactive) (shell-command "zip -r ../immersive_scaler_4-2.zip .")))


import importlib

importlib.invalidate_caches()

# import immersive_scaler.operations as imops
# import immersive_scaler.ui as imui

from . import ui as imui
from . import operations as imops
from . import bones as bones
from . import spread_fingers as spread_fingers
from . import align as align
from . import bones as bones

# from .operations import ops_register
# from .operations import ops_unregister
# from .ui import ui_register
# from .ui import ui_unregister


bl_info = {
    "name": "Immersive Scaler",
    "category": "3D View",
    "author": "pager",
    "version": (0, 5, 1),
    "blender": (2, 81, 0),
    "location": "View3D",
}


def register():
    print(__name__)
    importlib.reload(imui)
    importlib.reload(imops)
    importlib.reload(bones)
    importlib.reload(spread_fingers)
    importlib.reload(align)
    imui.ui_register()
    imops.ops_register()
    spread_fingers.ops_register()
    align.ops_register()
    bones.ops_register()


def unregister():
    imui.ui_unregister()
    imops.ops_unregister()
    spread_fingers.ops_unregister()
    align.ops_unregister()

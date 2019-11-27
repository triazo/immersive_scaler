from .operations import ops_register
from .operations import ops_unregister
from .ui import ui_register
from .ui import ui_unregister

bl_info = {
    "name": "Armature tuning",
    "category": "Armature",
    'author': 'triazo',
    'version': (0, 1),
    'blender': (2, 80, 0),
    'location': 'View3D',
    # 'warning': '',
}

def register():
    ops_register()
    ui_register()

def unregister():
    ops_unregister()
    ui_unregister()

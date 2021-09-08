import bpy

from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty
from bpy.types import Scene

def make_annotations(cls):
    bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)
    return cls

def set_properties():

    Scene.target_height = FloatProperty(
        name = "Target Height",
        description = "Desired height of the highest vertex in the model",
        default = 1.61,
        step = 0.01,
        precision = 2,
        soft_min = 0,
        soft_max = 3,
        subtype = 'DISTANCE'
    )

    Scene.arm_to_legs = FloatProperty(
        name = "Arm to Leg Ratio",
        description = "Ratio of Leg:Arm scaling to perform to scale the avatar for vrchat",
        default = 0.7,
        step = 0.01,
        precision = 2,
        soft_min = 0,
        soft_max = 1,
        subtype = 'FACTOR'
    )

    Scene.limb_thickness = FloatProperty(
        name = "Limb Thickness",
        description = "How much leg thickness should be kept when scaling",
        default = 1,
        step = 0.01,
        precision = 2,
        soft_min = 0,
        soft_max = 1,
        subtype = 'FACTOR'
    )

    Scene.extra_leg_length = FloatProperty(
        name = "Extra Leg Length",
        description = "How far beneath the real floor should the model's legs go - how far below the real floor should the vrchat floor be",
        default = 0,
        step = 0.01,
        precision = 2,
        soft_min = -1,
        soft_max = 1,
        subtype = 'DISTANCE'
    )

    Scene.scale_hand = BoolProperty(
        name = "Scale hand",
        description = "Should the hand be scaled along with the arm",
        default = False
        )

class ArmatureTweakMenu(bpy.types.Panel):
    bl_label = 'Armature Tweak Menu'
    bl_idname = "VIEW3D_PT_vrcat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ArmatureTweak"

    def draw(self, context):
        scn = context.scene
        layout = self.layout

        box = layout.box()
        col=box.column(align=True)
        col.label(text="Legacy Armature Rescale")

        row = col.row(align=True)
        row.prop(bpy.context.scene, 'target_height', expand=True)
        row = col.row(align=True)
        row.prop(bpy.context.scene, 'arm_to_legs', expand=True)
        row = col.row(align=True)
        row.prop(bpy.context.scene, 'limb_thickness', expand=True)
        row = col.row(align=True)
        row.prop(bpy.context.scene, 'extra_leg_length', expand=True)
        row = col.row(align=True)
        row.prop(bpy.context.scene, 'scale_hand', expand=True)

        row = col.row(align=True)
        row.scale_y=1.1
        op = row.operator("armature.rescale", text="Rescale Armature")


        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y=1.1
        row.operator("armature.enforce", text="Enforce Armature")

        box = layout.box()
        col=box.column(align=True)
        row = col.row(align=True)
        row.scale_y=1.1
        #row.prop(context.scene, 'spare_thumb')
        row.operator("armature.spreadfingers", text="Spread Fingers")

        return None


def ui_register():
    set_properties()
    make_annotations(ArmatureTweakMenu)
    bpy.utils.register_class(ArmatureTweakMenu)

def ui_unregister():
    bpy.utils.unregister_class(ArmatureTweakMenu)

if __name__ == "__main__":
    register()

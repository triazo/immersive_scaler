import bpy

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

class ArmatureTweakMenu(bpy.types.Panel):
    bl_label = 'Armature Tweak Menu'
    bl_idname = "VAT_Main_Menu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ArmatureTweak"

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        box = layout.box()
        col=box.column(align=True)
        row = col.row(align=True)
        row.scale_y=1.1
        row.prop(context.scene, 'arm_to_leg_ratio')
        row.operator("armature.rescale", text="Rescale Armature")

        box = layout.box()
        col=box.column(align=True)
        row = col.row(align=True)
        row.scale_y=1.1
        row.prop(context.scene, 'spare_thumb')
        row.operator("armature.spreadfingers", text="Spread Fingers")


def ui_register():
    make_annotations(ArmatureTweakMenu)
    bpy.utils.register_class(ArmatureTweakMenu)

def ui_unregister():
    bpy.utils.unregister_class(ArmatureTweakMenu)

if __name__ == "__main__":
    register()

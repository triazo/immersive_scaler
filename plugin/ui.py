import bpy

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


if __name__ == "__main__":
    bpy.utils.register_class(ArmatureTweakMenu)

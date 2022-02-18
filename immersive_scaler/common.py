import bpy

def get_objects():
    return bpy.context.scene.objects

def get_armature(armature_name=None):
    if not armature_name:
        armature_name = bpy.context.scene.armature
    if armature_name == None or armature_name == '':
        armature_name = "Armature"
    for obj in get_objects():
        if obj.type == 'ARMATURE' and obj.name == armature_name:
            return obj
    return None

import bpy
import mathutils

bl_info = {
    "name": "Armature tuning",
    "category": "Armature"
}

def get_objects():
    return bpy.context.scene.objects



def get_armature(armature_name=None):
    if not armature_name:
        armature_name = bpy.context.scene.armature
    for obj in get_objects():
        if obj.type == 'ARMATURE' and obj.name == armature_name:
            return obj
    return None

def measure_wingspan(obj):
    # TODO: enforce T-Pose, and reset
    bone_list = ['{} wrist',
                 '{} elbow',
                 '{} arm',
                 '{} shoulder',
                 'Chest']
    l_bone_list = [b.format("Left") for b in bone_list]
    r_bone_list = [b.format("Right") for b in bone_list]

    pose_bones = obj.pose.bones

    length = 0
    for l in (l_bone_list, r_bone_list):
        for i in range(len(l)-1):
            bone_gap = (pose_bones[l[i]].head - pose_bones[l[i+1]].tail).length
            bone_length = pose_bones[l[i]].length
            length += bone_gap + bone_length
    print(length)

    # Naieve implementaiton, just assumes t-pose
    left_hand = pose_bones['Left wrist']
    right_hand = pose_bones['Right wrist']
    print((left_hand.head - right_hand.head).length)

def get_lowest_point():
    body = bpy.data.objects['Body']
    mesh = body.data
    lowest_vertex = mesh.vertices[0]
    for v in mesh.vertices:
        if v.co[2] < lowest_vertex.co[2]:
            lowest_vertex = v

    return(lowest_vertex.co[2])

def get_highest_point():
    # Almost the same as get_lowest_point for obvious reasons
    body = bpy.data.objects['Body']
    mesh = body.data
    highest_vertex = mesh.vertices[0]
    for v in mesh.vertices:
        if v.co[2] > highest_vertex.co[2]:
            highest_vertex = v

    return(highest_vertex.co[2])

def get_view_y(obj):
    # Gets the in-vrchat virtual height that the view will be at,
    # relative to your actual floor.
    rhandpos = obj.pose.bones['Right wrist'].head
    headpos = obj.pose.bones['Head'].head


    # Magic that somebody posted in discord. I'm going to just assume
    # these constants are correct.
    view_y = ((headpos - rhandpos).length / .4537) + .005
    print("View coord is %f"%view_y)
    return view_y

def get_eye_height(obj):
    pose_bones = obj.pose.bones
    left_eye = pose_bones['LeftEye']
    right_eye = pose_bones['RightEye']
    eye_average = (left_eye.head + right_eye.head) / 2

    return eye_average[2]

def get_lowest_point():
    body = bpy.data.objects['Body']
    mesh = body.data
    lowest_vertex = mesh.vertices[0]
    for v in mesh.vertices:
        if v.co[2] < lowest_vertex.co[2]:
            lowest_vertex = v

    return(lowest_vertex.co[2])

def get_leg_length(obj):
    # Assumes exact symmetry between right and left legs
    return obj.pose.bones['Left leg'].head[2] - get_lowest_point()

def scale_legs_to_floor():
    obj = bpy.data.objects['Armature']
    # bo_context(bpy, bpy.ops.object.mode_set, mode='POSE', toggle = False)
    bpy.ops.cats_manual.start_pose_mode()
    arm = get_armature()

    view_y = get_view_y(obj)
    eye_y = get_eye_height(obj)

    # Compensate for the difference in in-game view and actual view with leg height
    leg_adjust = eye_y - view_y
    leg_length = get_leg_length(obj)

    leg_scale_ratio = (leg_length - leg_adjust) / leg_length
    print("Scaling legs by a factor of %f" % leg_scale_ratio)

    for leg in ["Left leg", "Right leg"]:
        obj.pose.bones[leg].scale = (1, leg_scale_ratio, 1)

    try:
        bpy.ops.cats_manual.pose_to_rest()
    except AttributeError as e:
        print("Stuff's still broken here but whatever it's working well enough enough: %s"%str(e))

def move_to_floor():
    obj = bpy.data.objects['Body']
    dz = get_lowest_point()
    hp = get_highest_point()

    newOrigin = (0, 0, dz)

    print("Moving origin down by %f"%dz)
    print("Highest point is %f"%hp)

    bpy.context.view_layer.objects.active = obj
    obj.select = True
    bpy.context.scene.cursor.location = newOrigin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    # This actually does the moving of the body
    print("Previous location: {}".format(obj.location))
    obj.location = (0,0,0)
    print("New location: {}".format(obj.location))

    arm = bpy.data.objects['Armature']
    bpy.context.view_layer.objects.active  = arm
    arm.select = True
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)
    for bone in arm.data.edit_bones:
        bone.transform(mathutils.Matrix.Translation((0, 0, -dz)))
    bpy.ops.object.mode_set(mode='EDIT', toggle = True)

    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def scale_to_height(new_height):
    obj = bpy.data.objects['Armature']
    old_height = get_highest_point()

    print("Old height is %f"%old_height)

    scale_ratio = new_height / old_height
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.transform.resize( value = (scale_ratio, scale_ratio, scale_ratio) )
    bpy.ops.object.transform_apply(location = True, scale = True,  rotation = True)


class ArmatureLegsToFloor(bpy.types.Operator):
    """Script to scale an armature's frame so that the floor lines up in vrchat"""
    bl_idname = "armature.scale_legs_to_floor"
    bl_label = "Scale Legs to Floor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scale_legs_to_floor()

        return {'FINISHED'}

class ArmatureMoveToFloor(bpy.types.Operator):
    """Script to move an armature to the ground so that the lowest point in the associated mesh is at height 0"""
    bl_idname = "armature.move_to_floor"
    bl_label = "Move Armature to Floor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        move_to_floor()

        return {'FINISHED'}

class ArmatureScaleToHeight(bpy.types.Operator):
    """Script to scale an armature so that the highest point is at a certian height"""
    bl_idname = "armature.scale_to_height"
    bl_label = "Scale Armature to Height"
    bl_options = {'REGISTER', 'UNDO'}

    target_height: bpy.props.FloatProperty(name="Target Height", default=1.61)

    def execute(self, context):
        scale_to_height(self.target_height)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(ArmatureLegsToFloor)
    bpy.utils.register_class(ArmatureMoveToFloor)
    bpy.utils.register_class(ArmatureScaleToHeight)
    print("Registering Armature tuning add-on")

def unregister():
    print("Attempting to unregister armature turing add-on")
    bpy.utils.unregister_class(ArmatureLegsToFloor)
    bpy.utils.unregister_class(ArmatureMoveToFloor)
    bpy.utils.unregister_class(ArmatureScaleToHeight)
    print("Unregistering Armature tuning add-on")

if __name__ == "__main__":
    register()

import bpy

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
    arm = get_armature(bpy)

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



class ArmatureLegsToFloor(bpy.types.Operator):
    """Script to scale an armature's frame so that the floor lines up in vrchat"""
    bl_idname = "armature.legs_to_floor"
    bl_label = "Scale Legs to Floor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scale_legs_to_floor()

        return {'FINISHED'}

def register():
    bpy.utils.register_class(ArmatureLegsToFloor)
    print("Registering Armature tuning add-on")

def unregister():
    print("Attempting to unregister armature turing add-on")
    bpy.utils.unregister_class(ArmatureLegsToFloor)
    print("Unregistering Armature tuning add-on")

if __name__ == "__main__":
    register()

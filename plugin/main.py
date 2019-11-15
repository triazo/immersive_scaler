import bpy
import mathutils
import math

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

    left_hand = pose_bones['Left wrist']
    right_hand = pose_bones['Right wrist']

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
    # VRC uses the distance between the head bone and right hand in
    # t-pose as the basis for world scale. Enforce t-pose locally to
    # grab this number
    bpy.ops.object.mode_set(mode='POSE', toggle = False)

    # Gets the in-vrchat virtual height that the view will be at,
    # relative to your actual floor.

    # Magic that somebody posted in discord. I'm going to just assume
    # these constants are correct. Testing shows it's at least pretty
    # darn close
    view_y = (head_to_hand(obj) / .4537) + .005
    bpy.ops.object.mode_set(mode='POSE', toggle = True)

    return view_y

def head_to_hand(obj):
    # Since arms might not be flat, add the length of the arm to the x
    # coordinate of the shoulder
    headpos = obj.pose.bones['Head'].head
    shoulder = obj.pose.bones['Right arm'].head
    arm_length = (obj.pose.bones['Right arm'].head - obj.pose.bones['Right wrist'].head).length
    arm_length = (obj.pose.bones['Right arm'].length + obj.pose.bones['Right elbow'].length)
    t_hand_pos = mathutils.Vector((shoulder[0] - arm_length, shoulder[1], shoulder[2]))
    print(t_hand_pos)
    bpy.context.scene.cursor.location = t_hand_pos
    return (headpos - t_hand_pos).length

def calculate_arm_rescaling(obj, head_arm_change):
    # Calculates the percent change in arm length needed to create a
    # given change in head-hand length.

    bpy.ops.object.mode_set(mode='POSE', toggle = False)

    rhandpos = obj.pose.bones['Right wrist'].head
    rarmpos = obj.pose.bones['Right arm'].head
    headpos = obj.pose.bones['Head'].head

    # Reset t-pose to whatever it was before since we have the data we
    # need
    bpy.ops.object.mode_set(mode='POSE', toggle = True)

    total_length = head_to_hand(obj)
    arm_length = (rarmpos - rhandpos).length
    neck_length = abs((headpos[2] - rarmpos[2]))

    # Sanity check - compare the difference between head_to_hand and manual
    # print("")
    # print("-------head_to_hand: %f" %total_length)
    # print("-------manual, assuming t-pose: %f" %(headpos - rhandpos).length)
    # print("")

    # Also derived using sympy. See below.
    shoulder_length = math.sqrt((total_length - neck_length) * (total_length + neck_length)) - arm_length

    # funky equation for all this - derived with sympy:
    # solveset(Eq(a * x, sqrt((c * b + s)**2 + y**2)), b)
    # where
    # x is total length
    # c is arm length
    # y is neck length
    # a is head_arm_change
    # s is shoulder_length
    # Drawing a picture with the arm and neck as a right triangle is necessary to understand this

    arm_change = (math.sqrt((head_arm_change * total_length - neck_length) * (head_arm_change * total_length + neck_length)) / arm_length) - (shoulder_length / arm_length)

    return arm_change


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

def scale_to_floor(arm_to_legs, limb_thickness, extra_leg_length, scale_hand):
    obj = bpy.data.objects['Armature']
    arm = get_armature()

    view_y = get_view_y(obj) + extra_leg_length
    eye_y = get_eye_height(obj)

    # TODO: add an option for people who *want* their legs below the floor.
    #
    # weirdos
    rescale_ratio = eye_y / view_y
    leg_height_portion = get_leg_length(obj) / eye_y

    # Enforces: rescale_leg_ratio * rescale_arm_ratio = rescale_ratio
    rescale_leg_ratio = rescale_ratio ** arm_to_legs
    rescale_arm_ratio = rescale_ratio ** (1-arm_to_legs)

    leg_scale_ratio = 1 - (1 - (1/rescale_leg_ratio)) / leg_height_portion
    arm_scale_ratio = calculate_arm_rescaling(obj, rescale_arm_ratio)

    print("Total required scale factor is %f" % rescale_ratio)
    print("Scaling legs by a factor of %f" % leg_scale_ratio)
    print("Scaling arms by a factor of %f" % arm_scale_ratio)

    bpy.ops.cats_manual.start_pose_mode()

    leg_thickness = limb_thickness + leg_scale_ratio * (1 - limb_thickness)
    arm_thickness = limb_thickness + arm_scale_ratio * (1 - limb_thickness)

    for leg in ["Left leg", "Right leg"]:
        obj.pose.bones[leg].scale = (leg_thickness, leg_scale_ratio, leg_thickness)
    for arm in ["Left arm", "Right arm"]:
        obj.pose.bones[arm].scale = (arm_thickness, arm_scale_ratio, arm_thickness)
    if not scale_hand:
        for hand in ["Left wrist", "Right wrist"]:
            obj.pose.bones[hand].scale = (1 / arm_thickness, 1 / arm_scale_ratio, 1 / arm_thickness)

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

    # TODO: This apply only seems to affect the top level object -
    # points in the mesh don't get scaled correctly and running this
    # prevents running the script again. Maybe I can just call out to
    # CATS again?
    bpy.ops.object.transform_apply(location = True, scale = True,  rotation = True)

def rescale_main(new_height, arm_to_legs, limb_thickness, extra_leg_length, scale_hand):
    scale_to_floor(arm_to_legs, limb_thickness, extra_leg_length, scale_hand)
    move_to_floor()
    scale_to_height(new_height)


def point_bone(bone, point):
    v1 = (bone.tail - bone.head).normalized()
    v2 = (bone.head - point).normalized()

    # Need to transform the global rotation between the twe vectors
    # into the local space of the bone
    #
    # Essentially, R_l = B @ R_g @ B^-1
    # where
    # R is the desired rotation (rotation_quat_pose)
    #  R_l is the local rotaiton
    #  R_g is the global rotation
    #  B is the bone's global rotation
    #  B^-1 is the inverse of the bone's rotation
    rotation_quat_pose = v1.rotation_difference(v2)
    bm = bone.matrix.to_quaternion()
    bm.rotate(rotation_quat_pose)
    bm.rotate(bone.matrix.inverted())

    bone.rotation_quaternion = bm

def spread_fingers():
    obj = bpy.data.objects['Armature']
    bpy.ops.cats_manual.start_pose_mode()
    for hand_name in ['Right wrist', 'Left wrist']:
        hand = obj.pose.bones[hand_name]
        for finger in hand.children:
            point_bone(finger, hand.head)
    bpy.ops.cats_manual.pose_to_rest()


class ArmatureRescale(bpy.types.Operator):
    """Script to scale most aspects of an armature for use in vrchat"""
    bl_idname = "armature.rescale"
    bl_label = "Rescale Armature"
    bl_options = {'REGISTER', 'UNDO'}

    target_height: bpy.props.FloatProperty(name="Target Height", default=1.61)
    arm_to_legs: bpy.props.FloatProperty(name="Arm to Leg ratio", default=1.0, soft_min=0, soft_max=1.0)
    limb_thickness: bpy.props.FloatProperty(name="Limb Thickness", default=1.0, soft_min=0, soft_max=1.0)
    extra_leg_length: bpy.props.FloatProperty(name="Extra leg Length", default = 0)
    scale_hand: bpy.props.BoolProperty(name="Scale Hand", default = False)

    def execute(self, context):
        rescale_main(self.target_height, self.arm_to_legs, self.limb_thickness, self.extra_leg_length, self.scale_hand)

        return {'FINISHED'}

class ArmatureSpreadFingers(bpy.types.Operator):
    """Spreads the fingers on a humanoiod avatar"""
    bl_idname = "armature.spreadfingers"
    bl_label = "Spread Fingers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        spread_fingers()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ArmatureRescale)
    bpy.utils.register_class(ArmatureSpreadFingers)
    print("Registering Armature tuning add-on")

def unregister():
    print("Attempting to unregister armature turing add-on")
    bpy.utils.unregister_class(ArmatureForceT)
    bpy.utils.unregister_class(ArmatureSpreadFingers)
    print("Unregistering Armature tuning add-on")

if __name__ == "__main__":
    register()

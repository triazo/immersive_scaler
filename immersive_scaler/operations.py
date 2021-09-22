import bpy
import mathutils
import math

from .ui import set_properties

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

def get_body_meshes(armature_name=None):
    arm = get_armature(armature_name)
    meshes = []
    for c in arm.children:
        if len(c.users_scene) == 0:
            continue
        if c.type == 'MESH':
            meshes.append(c)
    return meshes


def unhide_obj(obj):
    if not 'hide_states' in dir(unhide_obj):
        unhide_obj.hide_states = {}
    if not obj in unhide_obj.hide_states:
        print("Storing hide state of {} as {}".format(obj.name, obj.hide_get()))
        unhide_obj.hide_states[obj] = obj.hide_get()
    obj.hide_set(False)


def rehide_obj(obj):
    if not 'hide_states' in dir(unhide_obj):
        return
    if not obj in unhide_obj.hide_states:
        return
    print("Setting hide state of {} to {}".format(obj.name, unhide_obj.hide_states[obj]))
    obj.hide_set(unhide_obj.hide_states[obj])
    del(unhide_obj.hide_states[obj])


def hide_reset():
    del unhide_obj.hide_states


bone_names = {
    "right_arm": ["Right arm", "Arm.R", "R_Arm", "r_arm"],
    "right_shoulder": ["Right shoulder", "Shoulder.R", "R_Shoulder"],
    "right_elbow": ["Right elbow", "Elbow.R", "R_elbow", "Elbow.r", "r_elbow", "R_Elbow"],
    "right_wrist": ["Right wrist", "Wrist.R", "R_wrist", "Wrist.r", "r_wrist", "R_Wrist"],
    "left_arm": ["Left arm", "Arm.R", "R_Arm", "r_arm"],
    "left_shoulder": ["Left shoulder", "Shoulder.L", "L_Shoulder"],
    "left_elbow": ["Left elbow", "Elbow.L", "L_elbow", "Elbow.l", "l_elbow", "L_Elbow"],
    "left_wrist": ["Left wrist", "Wrist.L", "L_wrist", "Wrist.l", "l_wrist", "L_Wrist"],
    "left_leg": ["Left leg", "Leg.L", "L_Leg", "L_leg", "leg.l"],
    "right_leg": ["Right leg", "Leg.R", "R_Leg", "R_leg", "leg.r"],
    "left_knee": ["Left knee", "Knee.L", "L_Knee", "L_knee", "knee.l"],
    "right_knee": ["Right knee", "Knee.R", "R_Knee", "R_knee", "knee.r"],
    "left_ankle": ["Left ankle", "Ankle.L", "L_Ankle", "L_ankle", "ankle.l"],
    "right_ankle": ["Right ankle", "Ankle.R", "R_Ankle", "R_ankle", "ankle.r"]
}

def get_bone(name, arm):
    name_list = bone_names[name]
    for n in name_list:
        if n in arm.pose.bones:
            return arm.pose.bones[n]
    return arm.pose.bones[name]

def get_lowest_point():
    meshes = get_body_meshes()
    lowest_vertex = meshes[0].data.vertices[0]
    for o in meshes:
        mesh = o.data
        for v in mesh.vertices:
            if v.co[2] < lowest_vertex.co[2]:
                lowest_vertex = v
    return(lowest_vertex.co[2])


def get_highest_point():
    # Almost the same as get_lowest_point for obvious reasons
    meshes = get_body_meshes()
    highest_vertex = meshes[0].data.vertices[0]
    for o in meshes:
        mesh = o.data
        for v in mesh.vertices:
            if v.co[2] > highest_vertex.co[2]:
                highest_vertex = v

    return(highest_vertex.co[2])

def get_height():
    return get_highest_point() - get_lowest_point()

def get_view_y(obj):
    # VRC uses the distance between the head bone and right hand in
    # t-pose as the basis for world scale. Enforce t-pose locally to
    # grab this number
    unhide_obj(obj)
    bpy.context.view_layer.objects.active = obj
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
    shoulder = get_bone("right_arm", obj).head
    arm_length = (get_bone("right_arm",obj).head - get_bone("right_wrist", obj).head).length
    arm_length = (get_bone("right_arm",obj).length + get_bone("right_elbow", obj).length)
    t_hand_pos = mathutils.Vector((shoulder[0] - arm_length, shoulder[1], shoulder[2]))
    bpy.context.scene.cursor.location = t_hand_pos
    return (headpos - t_hand_pos).length


def calculate_arm_rescaling(obj, head_arm_change):
    # Calculates the percent change in arm length needed to create a
    # given change in head-hand length.

    unhide_obj(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='POSE', toggle = False)

    rhandpos = get_bone("right_wrist", obj).head
    rarmpos = get_bone("right_arm", obj).head
    headpos = obj.pose.bones['Head'].head

    # Reset t-pose to whatever it was before since we have the data we
    # need
    bpy.ops.object.mode_set(mode='POSE', toggle = True)

    total_length = head_to_hand(obj)
    print("Arm length is {}".format(total_length))
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

    l_eye_list = ['Eye_L', 'Eye_l', 'LeftEye', 'EyeLeft', 'lefteye', 'eyeleft', 'eye_l', 'Lefteye', 'leftEye']
    r_eye_list = ['Eye_R', 'Eye_r', 'RightEye', 'EyeRight', 'righteye', 'eyeright', 'eye_r', 'Righteye', 'rightEye']

    left_eye = None
    right_eye = None

    for n in l_eye_list:
        if n in pose_bones:
            left_eye = pose_bones[n]
            break
    for n in r_eye_list:
        if n in pose_bones:
            right_eye = pose_bones[n]
            break
    if left_eye == None or right_eye == None:
        raise(Error('Two eye bones required'))

    eye_average = (left_eye.head + right_eye.head) / 2

    return eye_average[2]

def get_leg_length(arm):
    # Assumes exact symmetry between right and left legs
    return get_bone("left_leg", arm).head[2] - get_lowest_point()

def get_leg_proportions(arm):
    # Gets the relative lengths of each portion of the leg
    l = [
        (get_bone('left_leg', arm).head[2] + get_bone('right_leg', arm).head[2]) / 2,
        (get_bone('left_knee', arm).head[2] + get_bone('right_knee', arm).head[2]) / 2,
        (get_bone('left_ankle', arm).head[2] + get_bone('right_ankle', arm).head[2]) / 2,
        get_lowest_point()
    ]

    total = l[0] - l[3]
    nl = list([1 - i/total for i in l])
    return nl, total

def bone_direction(bone):
    return (bone.tail - bone.head).normalized()

def angle(v1, v2, acute = True):
    angle = acos(v1.dot(v2) / (v1.normalize * v2.normalize))
    if (acute == True):
        return angle
    else:
        return 2 * math.pi - angle

def scale_legs(arm, leg_scale_ratio, leg_thickness, scale_foot, thigh_percentage):

    leg_points, total_length = get_leg_proportions(arm)

    starting_portions = list([leg_points[i+1]-leg_points[i] for i in range(3)])
    print("starting_portions: {}".format(starting_portions))

    # Foot scale is the percentage of the final it'll take up.
    foot_portion = ((1 - leg_points[2]) * leg_thickness / leg_scale_ratio)
    if scale_foot:
        foot_portion = (1 - leg_points[2]) * leg_thickness

    leg_portion = 1 - foot_portion

    # TODO: Add switch for maintaining existing thigh/calf proportions, make default(?)
    thigh_portion = leg_portion * thigh_percentage
    calf_portion = leg_portion - thigh_portion

    print("calculated desired leg portions: {}".format([thigh_portion, calf_portion, foot_portion]))

    final_thigh_scale = (thigh_portion / starting_portions[0]) * leg_scale_ratio
    final_calf_scale = (calf_portion / starting_portions[1]) * leg_scale_ratio
    final_foot_scale = (foot_portion / starting_portions[2]) * leg_scale_ratio

    # Disable scaling from parent for bones
    scale_bones = ["left_knee", "right_knee", "left_ankle", "right_ankle"]
    saved_bone_inherit_scales = {}
    for b in scale_bones:
        bone = get_bone(b, arm)
        saved_bone_inherit_scales[b] = arm.data.bones[bone.name].inherit_scale
        arm.data.bones[bone.name].inherit_scale = "NONE"

    print("Calculated final scales: thigh {} calf {} foot {}".format(final_thigh_scale, final_calf_scale, final_foot_scale))

    for leg in [get_bone("left_leg", arm), get_bone("right_leg", arm)]:
        leg.scale = (leg_thickness, final_thigh_scale, leg_thickness)
    for knee in [get_bone("left_knee", arm), get_bone("right_knee", arm)]:
        knee.scale = (leg_thickness, final_calf_scale, leg_thickness)
    for foot in [get_bone("left_ankle", arm), get_bone("right_ankle", arm)]:
        foot.scale = (final_foot_scale, final_foot_scale, final_foot_scale)

    result_final_points, result_total_legs = get_leg_proportions(arm)
    print("Implemented leg portions: {}".format(result_final_points))
    # restore saved bone scaling states
    # for b in scale_bones:
    #     arm.data.bones[b].inherit_scale = saved_bone_inherit_scales[b]

def scale_to_floor(arm_to_legs, arm_thickness, leg_thickness, extra_leg_length, scale_hand, thigh_percentage):
    arm = get_armature()

    view_y = get_view_y(arm) + extra_leg_length
    eye_y = get_eye_height(arm)

    # TODO: add an option for people who *want* their legs below the floor.
    #
    # weirdos
    rescale_ratio = eye_y / view_y
    leg_height_portion = get_leg_length(arm) / eye_y

    # Enforces: rescale_leg_ratio * rescale_arm_ratio = rescale_ratio
    rescale_leg_ratio = rescale_ratio ** arm_to_legs
    rescale_arm_ratio = rescale_ratio ** (1-arm_to_legs)

    leg_scale_ratio = 1 - (1 - (1/rescale_leg_ratio)) / leg_height_portion
    arm_scale_ratio = calculate_arm_rescaling(arm, rescale_arm_ratio)

    print("Total required scale factor is %f" % rescale_ratio)
    print("Scaling legs by a factor of %f to %f" % (leg_scale_ratio, leg_scale_ratio * get_leg_length(arm)))
    print("Scaling arms by a factor of %f" % arm_scale_ratio)

    unhide_obj(arm)
    bpy.ops.cats_manual.start_pose_mode()

    leg_thickness = leg_thickness + leg_scale_ratio * (1 - leg_thickness)
    arm_thickness = arm_thickness + arm_scale_ratio * arm_thickness


    scale_foot = False
    scale_legs(arm, leg_scale_ratio, leg_thickness, scale_foot, thigh_percentage)

    # This kept getting me - make sure arms are set to inherit scale
    for b in ["left_elbow", "right_elbow", "left_wrist", "right_wrist"]:
        bone_name = get_bone(b, arm).name
        arm.data.bones[bone_name].inherit_scale = "FULL"

    for armbone in [get_bone("left_arm", arm), get_bone("right_arm", arm)]:
        armbone.scale = (arm_thickness, arm_scale_ratio, arm_thickness)

    if not scale_hand:
        for hand in [get_bone("left_wrist", arm), get_bone("right_wrist", arm)]:
            hand.scale = (1 / arm_thickness, 1 / arm_scale_ratio, 1 / arm_thickness)

            result_final_points, result_total_legs = get_leg_proportions(arm)
    print("Implemented leg portions: {}".format(result_final_points))
    try:
        bpy.ops.cats_manual.pose_to_rest()
    except AttributeError as e:
        print("Stuff's still broken here but whatever it's working well enough enough: %s"%str(e))


def move_to_floor():

    arm = get_armature()
    unhide_obj(arm)
    dz = get_lowest_point()

    aloc = get_armature().location
    newOrigin = (aloc[0], aloc[1], dz)

    # print("New origin point: {}".format(newOrigin))
    # print("Moving origin down by %f"%dz)
    # print("Highest point is %f"%hp)

    meshes = get_body_meshes()
    for obj in meshes:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
        bpy.context.scene.cursor.location = newOrigin
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        # This actually does the moving of the body
        obj.location = (aloc[0],aloc[1],0)
        obj.select_set(False)

    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)
    before_zs = {b.name: (b.head.z, b.tail.z) for b in arm.data.edit_bones}
    for bone in arm.data.edit_bones:
        #bone.transform(mathutils.Matrix.Translation((0, 0, -dz)))
        bone.head.z = before_zs[bone.name][0] - dz
        bone.tail.z = before_zs[bone.name][1] - dz
        # for b in arm.data.edit_bones:
        #     if b.name != bone.name and b.head.z != before_zs[b.name]:

        #         print("ERROR: Bone %s also changed bone %s: %f to %f"%(bone.name, b.name, before_zs[b.name], b.head.z))
        #print("%s: %f -> %f: %f"%(bone.name, bz, az, bz - az))
    bpy.ops.object.mode_set(mode='EDIT', toggle = True)

    bpy.context.scene.cursor.location = (aloc[0],aloc[1],0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    arm.select_set(False)

def recursive_object_mode(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
    for c in obj.children:
        if len(c.users_scene) == 0:
            continue
        if 'scale' in dir(c):
            recursive_object_mode(c)

def recursive_scale(obj):
    bpy.context.scene.cursor.location = obj.location
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    print("Scaling {} by {}".format(obj.name, 1 / obj.scale[0]))
    bpy.ops.object.transform_apply(scale = True, location = False, rotation = False, properties = False)

    for c in obj.children:
        if len(c.users_scene) == 0:
            continue
        if 'scale' in dir(c):
            recursive_scale(c)


def scale_to_height(new_height):
    obj = get_armature()
    unhide_obj(obj)
    old_height = get_highest_point() - get_lowest_point()

    print("Old height is %f"%old_height)

    scale_ratio = new_height / old_height
    print("Scaling by %f to achieve target height" % scale_ratio)
    bpy.context.scene.cursor.location = obj.location
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    obj.scale = obj.scale * scale_ratio

    recursive_object_mode(obj)
    recursive_scale(obj)

    rehide_obj(obj)

def center_model():
    arm = get_armature()
    arm.location = (0,0,0)


def rescale_main(new_height, arm_to_legs, arm_thickness, leg_thickness, extra_leg_length, scale_hand, thigh_percentage):
    s = bpy.context.scene


    if not s.debug_no_adjust:
        scale_to_floor(arm_to_legs, arm_thickness, leg_thickness, extra_leg_length, scale_hand, thigh_percentage)
    if not s.debug_no_floor:
        move_to_floor()

    result_final_points, result_total_legs = get_leg_proportions(get_armature())
    print("Final Implemented leg portions: {}".format(result_final_points))

    if not s.debug_no_scale:
        scale_to_height(new_height)

    if s.center_model:
        center_model()

    bpy.ops.object.select_all(action='DESELECT')

def point_bone(bone, point):
    v1 = (bone.tail - bone.head).normalized()
    v2 = (bone.head - point).normalized()

    # Need to transform the global rotation between the two vectors
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

def spread_fingers(spare_thumb):
    obj = get_armature()
    bpy.ops.cats_manual.start_pose_mode()
    for hand in [get_bone("right_wrist", obj), get_bone("left_wrist", obj)]:
        for finger in hand.children:
            if "thumb" in finger.name.lower() and spare_thumb:
                continue
            point_bone(finger, hand.head)
    bpy.ops.cats_manual.pose_to_rest()
    bpy.ops.object.select_all(action='DESELECT')

def shrink_hips():
    arm = get_armature()

    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)

    left_leg_name = get_bone('left_leg', arm).name
    right_leg_name = get_bone('right_leg', arm).name
    leg_start = (arm.data.edit_bones[left_leg_name].head[2] +arm.data.edit_bones[right_leg_name].head[2]) / 2
    spine_start = arm.data.edit_bones['Spine'].head[2]

    # Make the hip tiny - 90 of the way between the start of the legs
    # and the start of the spine

    arm.data.edit_bones['Hips'].head[2] = leg_start + (spine_start - leg_start) * .9
    arm.data.edit_bones['Hips'].head[1] = arm.data.edit_bones['Spine'].head[1]
    arm.data.edit_bones['Hips'].head[0] = arm.data.edit_bones['Spine'].head[0]

    bpy.ops.object.mode_set(mode='EDIT', toggle = True)
    bpy.ops.object.select_all(action='DESELECT')


class ArmatureRescale(bpy.types.Operator):
    """Script to scale most aspects of an armature for use in vrchat"""
    bl_idname = "armature.rescale"
    bl_label = "Rescale Armature"
    bl_options = {'REGISTER', 'UNDO'}

    set_properties()
    target_height: bpy.types.Scene.target_height
    arm_to_legs: bpy.types.Scene.arm_to_legs
    arm_thickness: bpy.types.Scene.arm_thickness
    leg_thickness: bpy.types.Scene.leg_thickness
    extra_leg_length: bpy.types.Scene.extra_leg_length
    scale_hand: bpy.types.Scene.scale_hand
    thigh_percentage: bpy.types.Scene.thigh_percentage

    def execute(self, context):

        rescale_main(self.target_height, self.arm_to_legs, self.arm_thickness, self.leg_thickness, self.extra_leg_length, self.scale_hand, self.thigh_percentage)
        return {'FINISHED'}

    def invoke(self, context, event):
        s = context.scene
        self.target_height = s.target_height
        self.arm_to_legs = s.arm_to_legs
        self.arm_thickness = s.arm_thickness
        self.leg_thickness = s.leg_thickness
        self.extra_leg_length = s.extra_leg_length
        self.scale_hand = s.scale_hand
        self.thigh_percentage = s.thigh_percentage

        return self.execute(context)


class ArmatureSpreadFingers(bpy.types.Operator):
    """Spreads the fingers on a humanoid avatar"""
    bl_idname = "armature.spreadfingers"
    bl_label = "Spread Fingers"
    bl_options = {'REGISTER', 'UNDO'}

    spare_thumb: bpy.types.Scene.spare_thumb

    def execute(self, context):
        spread_fingers(self.spare_thumb)
        return {'FINISHED'}

    def invoke(self, context, event):
        s = context.scene
        self.spare_thumb = s.spare_thumb

        return self.execute(context)

class ArmatureShrinkHip(bpy.types.Operator):
    """Shrinks the hip bone in a humaniod avatar to be much closer to the spine location"""
    bl_idname = "armature.shrink_hips"
    bl_label = "Shrink Hips"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        shrink_hips()
        return {'FINISHED'}


def ops_register():
    print("Registering Armature tuning add-on")
    bpy.utils.register_class(ArmatureRescale)
    make_annotations(ArmatureRescale)

    bpy.utils.register_class(ArmatureSpreadFingers)
    make_annotations(ArmatureSpreadFingers)

    bpy.utils.register_class(ArmatureShrinkHip)
    make_annotations(ArmatureShrinkHip)

    print("Registering Armature tuning add-on")

def ops_unregister():
    print("Attempting to unregister armature turing add-on")
    bpy.utils.unregister_class(ArmatureRescale)
    bpy.utils.unregister_class(ArmatureSpreadFingers)
    bpy.utils.unregister_class(ArmatureShrinkHip)
    print("Unregistering Armature tuning add-on")

if __name__ == "__main__":
    register()
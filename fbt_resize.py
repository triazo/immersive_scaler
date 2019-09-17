import time

import mathutils

def get_objects(bpy):
    return bpy.context.scene.objects

def get_armature(bpy, armature_name=None):
    if not armature_name:
        armature_name = bpy.context.scene.armature
    for obj in get_objects(bpy):
        if obj.type == 'ARMATURE' and obj.name == armature_name:
            return obj
    return None

def bo_context(bpy, bo, *args, **kwargs):
    context = bpy.context
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            override = bpy.context.copy()
            override["space_data"] = area.spaces[0]
            #override["space_data"].transform_manipulators = {'TRANSLATE'}
            override["area"] = area
            arm = get_armature(bpy)
            if arm:
                print("Armature mode is %s" % arm.mode)
                print("Calling %s" % bo)
            print("Poll result is %s"%str(bo.poll(override)))
            print(override)
            return bo(override, *args, **kwargs)


def reparent_skirt(bpy):
    obj = bpy.data.objects['Armature']
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)
    edit_bones = obj.data.edit_bones
    hips = edit_bones['Hips']
    skirt = edit_bones.new('Skirt')
    ht = hips.tail
    skirt.tail = ht
    skirt.head = (ht[0],ht[1],ht[2]+.00001)
    skirt.parent = hips

    for bone in edit_bones.keys():
        if "Skirt_0" not in bone:
            continue
        edit_bones[bone].parent = skirt

def measure_wingspan(obj):
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

    # Naieve implementaiton, just assumes
    left_hand = pose_bones['Left wrist']
    right_hand = pose_bones['Right wrist']
    print((left_hand.head - right_hand.head).length)

def get_leg_length(bpy, obj):
    # Assumes exact symmetry between right and left legs
    return obj.pose.bones['Left leg'].head[2] - get_lowest_point(bpy)


def get_lowest_point(bpy):
    body = bpy.data.objects['Body']
    mesh = body.data
    lowest_vertex = mesh.vertices[0]
    for v in mesh.vertices:
        if v.co[2] < lowest_vertex.co[2]:
            lowest_vertex = v

    return(lowest_vertex.co[2])

def get_highest_point(bpy):
    # Almost the same as get_lowest_point for obvious reasons
    body = bpy.data.objects['Body']
    mesh = body.data
    highest_vertex = mesh.vertices[0]
    for v in mesh.vertices:
        if v.co[2] > highest_vertex.co[2]:
            highest_vertex = v

    return(highest_vertex.co[2])

def get_eye_height(bpy, obj):
    pose_bones = obj.pose.bones
    left_eye = pose_bones['LeftEye']
    right_eye = pose_bones['RightEye']
    eye_average = (left_eye.head + right_eye.head) / 2

    return eye_average[2]


def measure_height(bpy):
    # TODO: return partial values, so that say, the legs can be
    # resized vertically without the feet
    obj = bpy.data.objects['Armature']
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)

    edit_bones = obj.data.edit_bones
    left_eye = edit_bones['LeftEye']
    right_eye = edit_bones['RightEye']
    left_foot = edit_bones['Left ankle']
    right_foot = edit_bones['Right ankle']
    eye_average = (left_eye.head + right_eye.head) / 2
    foot_average = (left_foot.head + right_foot.head) / 2

    bpy.ops.object.mode_set(mode='EDIT', toggle = True)

    print((eye_average - foot_average).length)
    print(eye_average[2] - get_lowest_point(bpy))


def get_view_y(bpy, obj):
    # Gets the in-vrchat virtual height that the view will be at,
    # relative to your actual floor.
    rhandpos = obj.pose.bones['Right wrist'].head
    headpos = obj.pose.bones['Head'].head


    # Magic that somebody posted in discord. I'm going to just assume
    # these constants are correct.
    view_y = ((headpos - rhandpos).length / .4537) + .005
    print("View coord is %f"%view_y)
    return view_y

def shrink_neck(bpy):
    # TODO:
    #
    # 1) shrink neck bone to almost nothing in pose mode
    # 2) move head bone to encompass the neck bone
    # 3) make all vertex weights of the head equal to it's weight of the head plus the neck
    #
    # v.weight['head'] = v.weight['head'] + v.weight['neck']
    pass


def move_to_floor(bpy):
    obj = bpy.data.objects['Body']
    dz = get_lowest_point(bpy)

    newOrigin = (0, 0, dz)

    print("Moving origin down by %f"%dz)

    bpy.context.scene.objects.active = obj
    obj.select = True
    bpy.context.scene.cursor_location = newOrigin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    # This actually does the moving of the body
    obj.location = (0,0,0)

    arm = bpy.data.objects['Armature']
    bpy.context.scene.objects.active = arm
    arm.select = True
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)
    for bone in arm.data.edit_bones:
        bone.transform(mathutils.Matrix.Translation((0, 0, -dz)))
    bpy.ops.object.mode_set(mode='EDIT', toggle = True)

    bpy.context.scene.cursor_location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')



def scale_legs_to_floor(bpy):
    obj = bpy.data.objects['Armature']
    # bo_context(bpy, bpy.ops.object.mode_set, mode='POSE', toggle = False)
    bo_context(bpy, bpy.ops.cats_manual.start_pose_mode)
    arm = get_armature(bpy)

    view_y = get_view_y(bpy, obj)
    eye_y = get_eye_height(bpy, obj)

    # Compensate for the difference in in-game view and actual view with leg height
    leg_adjust = eye_y - view_y
    leg_length = get_leg_length(bpy, obj)

    leg_scale_ratio = (leg_length - leg_adjust) / leg_length
    print("Scaling legs by a factor of %f" % leg_scale_ratio)

    for leg in ["Left leg", "Right leg"]:
        obj.pose.bones[leg].scale = (1, leg_scale_ratio, 1)

    try:
        bo_context(bpy, bpy.ops.cats_manual.pose_to_rest)
    except AttributeError as e:
        print("Stuff's still broken here but whatever it's working well enough enough: %s"%str(e))

    move_to_floor(bpy)


def scale_to_height(bpy, new_height):
    obj = bpy.data.objects['Armature']
    old_height = get_highest_point(bpy)

    print("Old height is %f"%old_height)

    scale_ratio = new_height / old_height
    bpy.context.scene.cursor_location = (0, 0, 0)
    obj.scale = (scale_ratio, scale_ratio, scale_ratio)




def wrap(f, bpy):
    obj = bpy.data.objects['Armature']
    bpy.ops.object.mode_set(mode='POSE', toggle = False)
    r = f(obj)
    bpy.ops.object.mode_set(mode='POSE', toggle = True)
    return r

# view_y = ((HeadPos - HandPos)/0.4537)+0.005

def main(bpy):
    scale_legs_to_floor(bpy)
    move_to_floor(bpy)
    scale_to_height(bpy, 1.58)
    return
    # get_view_y(bpy)
    # return
    # scale_arms(bpy)
    # print("Height:")
    # measure_height(bpy)
    # print("Wingspan")
    # wrap(measure_wingspan, bpy)

# fbt_resize.scale_legs_to_floor(bpy)
# fbt_resize.move_to_floor(bpy)
# fbt_resize.scale_to_height(bpy, 1.58)

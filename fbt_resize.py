

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

def get_lowest_point(bpy):
    body = bpy.data.objects['Body']
    mesh = body.data
    lowest_vertex = mesh.vertices[0]
    for v in mesh.vertices:
        if v.co[2] < lowest_vertex.co[2]:
            lowest_vertex = v

    print(lowest_vertex.co)
    print(lowest_vertex.co[2])
    return(lowest_vertex.co[2])


def measure_height(bpy):
    # TODO: return partial values, so that say, the legs can be
    # resized vertically without the feet
    obj = bpy.data.objects['Armature']
    bpy.ops.object.mode_set(mode='EDIT', toggle = False)

    edit_bones = obj.data.edit_bones
    left_eye = edit_bones['Eye_L']
    right_eye = edit_bones['Eye_R']
    left_foot = edit_bones['Left ankle']
    right_foot = edit_bones['Right ankle']
    eye_average = (left_eye.head + right_eye.head) / 2
    foot_average = (left_foot.head + right_foot.head) / 2

    bpy.ops.object.mode_set(mode='EDIT', toggle = True)

    print((eye_average - foot_average).length)
    print(eye_average[2] - get_lowest_point(bpy))

def scale_arms(bpy):
    obj = bpy.data.objects['Armature']
    bpy.ops.object.mode_set(mode='POSE', toggle = False)

    print(dir(obj.pose.bones['Left arm']))
    print(obj.pose.bones['Left arm'].scale)

    bpy.ops.object.mode_set(mode='POSE', toggle = True)

def wrap(f, bpy):
    obj = bpy.data.objects['Armature']
    bpy.ops.object.mode_set(mode='POSE', toggle = False)
    r = f(obj)
    bpy.ops.object.mode_set(mode='POSE', toggle = True)
    return r

def main(bpy):
    scale_arms(bpy)
    print("Height:")
    measure_height(bpy)
    print("Wingspan")
    wrap(measure_wingspan, bpy)

import bpy
import mathutils
import math
import importlib
import numpy as np
from typing import List, Iterable

from . import common
from . import posemode
from . import bones

importlib.reload(common)
importlib.reload(bones)
importlib.reload(posemode)

from .common import (
    get_armature,
    op_override,
    children_recursive,
    ArmatureOperator,
    get_body_meshes,
    obj_in_scene,
    temp_ensure_enabled,
)

from .bones import *
from .posemode import *


def get_bone_worldspace_z(name, arm):
    """get_lowest_point() and get_highest_point() return positions in worldspace, sometimes we need to measure between
    these points and bones, which requires that the bone positions are also in worldspace.
    This convenience method will return the worldspace z position of the head of a bone.
    """
    return (arm.matrix_world @ get_bone(name, arm).head).z


if hasattr(bpy.types.bpy_prop_array, "foreach_get") and bpy.app.version < (4, 1):
    # Fast accessor method was added in Blender 2.83. While it's about 50 times slower without the fast accessor method,
    # a bounding box is only an 8x3 array, so it's not going to make much difference.
    def bound_box_to_co_array(obj: bpy.types.Object):
        # Note that bounding boxes of objects correspond to the object with shape keys and modifiers applied
        # Bounding boxes are 2D bpy_prop_array, each bounding box is represented by 8 (x, y, z) rows. Since this is a
        # bpy_prop_array, the dtype must match the internal C type, otherwise an error is raised.
        bb_co = np.empty((8, 3), dtype=np.single)

        # Temporarily disabling modifiers to get a more accurate bounding box of the mesh and then re-enabling the
        # modifiers would be far too performance heavy. Changing active shape key might be too heavy too. Though, even
        # if we change the active shape key or modifiers in code, the bounding box doesn't seem to update right away.
        obj.bound_box.foreach_get(bb_co)

        return bb_co

else:

    def bound_box_to_co_array(obj: bpy.types.Object):
        return np.array(obj.bound_box, dtype=np.single)


def _get_global_z_from_co_ndarray(v_co: np.ndarray, wm: mathutils.Matrix, func):
    if v_co.dtype != np.single:
        # The dtype isn't too important when not using foreach_set/foreach_get. Given another float type it would just
        # mean we're doing math with more (or less) precision than existed in the first place.
        raise ValueError("co array should be single precision float")
    if len(wm.row) != 4 or len(wm.col) != 4:
        raise ValueError("matrix must be 4x4")
    # Create a view of the array so that when we set the shape, we set the shape of the view rather than the original
    # array
    v_co = v_co.view()
    # Convert mathutils.Matrix to an np.ndarray and remove the translation.
    # Since every vertex will be translated the same amount, we can add the translation on at the end. This means that
    # we only need to do 3d matrix multiplication instead of 4d, which would also have required us to extend v_co to
    # 4d. The end result is that the function runs faster.
    wm3x3 = np.array(wm.to_3x3(), dtype=np.single)

    # Change the shape we view the data with so that each element corresponds to a single vertex's (x,y,z)
    v_co.shape = (-1, 3)
    # To multiply the matrix (3, 3) by each vector in (num_verts, 3), we can transpose the entire array to turn it
    # on its side and treat it as one giant matrix whereby each column is one vector. Note that with numpy, the
    # transpose of an ndarray is a view, no data is copied.
    # ┌a, b, c┐   ┌x1, y1, z1┐    ┌a, b, c┐   ┌x1, x2, x3, …, xn┐
    # │e, f, g│ ? │x2, y2, z2│ -> │e, f, g│ @ │y1, y2, y3, …, yn│
    # └i, j, k┘   │x3, y3, z3│    └i, j, k┘   └z1, z2, z3, …, zn┘
    #             ┊ …,  …,  …┊
    #             └xn, yn, zn┘
    # This gives us a result with the shape (3, num_verts). The alternative would be to transpose the matrix instead
    # and do `vco_4 @ wm.T`, which would give us the transpose of the first result with the shape (num_verts, 3).
    v_co4_global_t = wm3x3 @ v_co.T
    # We only care about the z values, which will all currently be in index 2
    global_z_only = v_co4_global_t[2]

    # We've ignored the z translation up to this point. Instead of adding it to every value, just add it to the result
    # of the min/max function, since it doesn't affect which value is the min/max.
    return func(global_z_only) + wm.translation.z


def get_global_min_z_from_co_ndarray(v_co: np.ndarray, wm: mathutils.Matrix):
    return _get_global_z_from_co_ndarray(v_co, wm, np.min)


def get_global_max_z_from_co_ndarray(v_co: np.ndarray, wm: mathutils.Matrix):
    return _get_global_z_from_co_ndarray(v_co, wm, np.max)


def get_lowest_point():
    """Get the lowest z coordinate of all vertices of all meshes of the avatar, in worldspace"""
    arm = get_armature()
    bones = set()
    for bone in (get_bone("left_ankle", arm), get_bone("right_ankle", arm)):
        bones.add(bone.name)
        bones.update(b.name for b in bone.children_recursive)

    meshes = []
    for o in get_body_meshes():
        # Get minimum worldspace z component. This is exceedingly likely to be lower or the same as the lowest vertex in
        # the mesh.
        likely_lowest_possible_vertex_z = get_global_min_z_from_co_ndarray(
            bound_box_to_co_array(o), o.matrix_world
        )
        # Add the minimum z component along with the mesh object
        meshes.append((likely_lowest_possible_vertex_z, o))
    # Sort meshes by lowest bounding box first, that way, we can stop checking meshes once we get to a mesh whose lowest
    # corner of the bounding box is higher than the current lowest vertex
    meshes.sort(key=lambda t: t[0])

    lowest_vertex_z = math.inf
    lowest_foot_z = math.inf

    for likely_lowest_possible_vertex_z, o in meshes:
        mesh = o.data
        if not mesh.vertices:
            # Immediately skip if there's no vertices
            continue

        found_feet_previously = lowest_foot_z < math.inf
        if found_feet_previously and likely_lowest_possible_vertex_z > lowest_foot_z:
            # Lowest possible vertex of this mesh is exceedingly likely to be higher than the current lowest found.
            # Since the meshes are sorted by lowest possible vertex first, any subsequent meshes will be the same, so we
            # don't need to check them.
            break

        foot_group_indices = {
            idx for idx, vg in enumerate(o.vertex_groups) if vg.name in bones
        }
        if not foot_group_indices:
            if found_feet_previously:
                # Vertices belonging to feet were found previously, but the current mesh doesn't have any vertex groups
                # that correspond to feet, so skip the mesh
                continue
            elif likely_lowest_possible_vertex_z > lowest_vertex_z:
                # Vertices belonging to feet have yet to be found, but the current mesh doesn't have any vertex groups
                # that correspond to feet and its lowest possible vertex is exceedingly likely to be higher than the
                # current lowest found. Since we could still find a mesh with vertices assigned to feet, we can't stop
                # iteration here, but we can skip the current mesh at least.
                continue

        if mesh.shape_keys:
            # Exiting edit mode synchronizes a mesh's vertex and 'basis' (reference) shape key positions, but if one of
            # them is modified outside of edit mode without the other being modified in the same way also, the two can
            # become desynchronized. What users see in the 3D view corresponds to the reference shape key, so we'll
            # assume that has the correct positions.
            num_verts = len(mesh.vertices)
            # vertex positions ('co') are (x,y,z) vectors, but get flattened when using foreach_get/set, so the
            # resulting array is 3 times the number of vertices
            v_co = np.empty(num_verts * 3, dtype=np.single)
            # Directly copy the 'co' of the reference shape key into the v_cos array (type must match the internal C
            # type for a direct copy)
            mesh.shape_keys.reference_key.data.foreach_get("co", v_co)
            # Directly paste the 'co' copied from the reference shape key into the 'co' of the vertices
            mesh.vertices.foreach_set("co", v_co)
        else:
            v_co = None

        wm = o.matrix_world
        foot_v_indices = []
        if foot_group_indices:
            # There are unfortunately no fast methods for getting all vertex weights, so we must resort to iteration.
            # We expect most vertices to not be weighted to feet, so it's generally slightly faster to get the
            # .index of each vertex we need rather than to use enumerate
            for vert in mesh.vertices:
                # For performance, we want to do as little as possible within the main loop because the slowest part of
                # the loop is Python itself, getting the attributes, calling functions etc. All we'll do is append the
                # indices of the vertices that are weighted to feet to a list and then let numpy handle everything else.
                for group in vert.groups:
                    # .group is the index of the vertex_group
                    # .weight is a 'truthy' value whenever it is not zero
                    if group.group in foot_group_indices and group.weight:
                        foot_v_indices.append(vert.index)
                        break
        found_feet = bool(foot_v_indices)
        # If there are no indices found that are weighted to feet, but we've previously found vertices that are
        # weighted to feet, we can ignore this mesh.
        # Otherwise:
        #   if we've found vertices weighted to feet, update lowest_foot_z with those vertices,
        #   else if we've not found vertices weighted to feet, update lowest_vertex_z with all vertices.
        if found_feet or not found_feet_previously:
            if v_co is None:
                # Get v_co array
                v_co = np.empty(len(mesh.vertices) * 3, dtype=np.single)
                mesh.vertices.foreach_get("co", v_co)
            # View the array with each element being a single (x,y,z) vector
            v_co.shape = (-1, 3)

            if found_feet:
                # Numpy lets us index a numpy array with a list or array of indices (this creates a copy rather than
                # a view)
                v_co_feet_only = v_co[foot_v_indices]
                lowest_foot_z = min(
                    lowest_foot_z, get_global_min_z_from_co_ndarray(v_co_feet_only, wm)
                )
            else:
                # No vertices weighted to feet were found and feet have not been found previously
                lowest_vertex_z = min(
                    lowest_vertex_z, get_global_min_z_from_co_ndarray(v_co, wm)
                )
    if lowest_foot_z == math.inf:
        if lowest_vertex_z == math.inf:
            raise RuntimeError("No mesh data found")
        else:
            return lowest_vertex_z
    return lowest_foot_z


def get_highest_point():
    # Almost the same as get_lowest_point for obvious reasons, but only using numpy since we don't need to check vertex
    # weights
    meshes = []
    for o in get_body_meshes():
        # Get maximum worldspace z component. This is exceedingly likely to be higher or the same as the highest vertex
        # in the mesh.
        likely_highest_possible_vertex_z = get_global_max_z_from_co_ndarray(
            bound_box_to_co_array(o), o.matrix_world
        )
        # Add the maximum z component along with the mesh object
        meshes.append((likely_highest_possible_vertex_z, o))
    # Sort meshes by highest bounding box first, that way, we can stop checking meshes once we get to a mesh whose
    # highest corner of the bounding box is lower than the current highest vertex
    meshes.sort(key=lambda t: t[0], reverse=True)

    minimum_value = -math.inf
    highest_vertex_z = minimum_value
    for likely_highest_possible_vertex_z, o in meshes:
        wm = o.matrix_world
        mesh = o.data

        # Sometimes the 'basis' (reference) shape key and mesh vertices can become desynchronized. If a mesh has shape
        # keys, then the reference shape key is what users will see in Blender, so get vertex positions from that.
        vertices = (
            mesh.shape_keys.reference_key.data if mesh.shape_keys else mesh.vertices
        )
        num_verts = len(vertices)
        if num_verts == 0:
            continue

        if likely_highest_possible_vertex_z < highest_vertex_z:
            # Highest possible vertex of this mesh is exceedingly likely to be lower than the current highest found.
            # Since the meshes are sorted by highest possible vertex first, any subsequent meshes will be the same, so
            # we don't need to check them.
            break

        v_co = np.empty(num_verts * 3, dtype=np.single)
        vertices.foreach_get("co", v_co)
        # Get the maximum value global vertex z value
        max_global_z = get_global_max_z_from_co_ndarray(v_co, wm)
        # Compare against the current highest vertex z and set it to whichever is greatest
        highest_vertex_z = max(highest_vertex_z, max_global_z)
    if highest_vertex_z == minimum_value:
        raise RuntimeError("No mesh data found")
    else:
        return highest_vertex_z


def get_view_z(obj, custom_scale_ratio=0.4537):
    # VRC uses the distance between the head bone and right hand in
    # t-pose as the basis for world scale.

    # Gets the in-vrchat virtual height that the view will be at,
    # relative to your actual floor.

    # Magic that somebody posted in discord. I'm going to just assume
    # these constants are correct. Testing shows it's at least pretty
    # darn close
    view_z = (head_to_hand(obj) / custom_scale_ratio) + 0.005

    return view_z


def get_current_scaling(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="POSE", toggle=False)

    # TODO: What's the minus .005 on the end? I'm going to assume it's intended to be in worldspace
    ratio = head_to_hand(obj) / (get_eye_height(obj) - 0.005 - get_lowest_point())

    bpy.ops.object.mode_set(mode="POSE", toggle=True)
    return ratio


def get_upper_body_portion(arm):
    eye_z = (
        get_bone_worldspace_z("left_eye", arm) + get_bone_worldspace_z("right_eye", arm)
    ) / 2
    neck_z = get_bone_worldspace_z("neck", arm)
    leg_average_z = (
        get_bone_worldspace_z("left_leg", arm) + get_bone_worldspace_z("right_leg", arm)
    ) / 2
    lowest_point = get_lowest_point()

    return 1 - (leg_average_z - lowest_point) / (eye_z - lowest_point)


def get_arm_length(obj, worldspace=True):
    """Get the length of the (right) arm as if its bones are fully straightened"""
    upper_arm = get_bone("right_arm", obj).head
    elbow = get_bone("right_elbow", obj).head
    wrist = get_bone("right_wrist", obj).head
    # Unity bones are from joint to joint, ignoring whatever the tail may be in Blender
    if worldspace:
        # Since the translation by the matrix will be the same for all the vectors, and we're only calculating length,
        # we can ignore the translation and work solely with 3d vector math (instead of 4d).
        #
        # Notes on working with 4d vector math:
        #   To work with 4d vector math, we would have to extend the 3d vectors to 4d with their w components set to
        #   1.0. This means that subtracting one vector from another will result in a vector with a w component of 0.0.
        #
        #   Note that attempting to multiply a 4x4 matrix by a 3d vector will automatically extend the vector to 4d with
        #   w set to 1.0, perform the multiplication and then remove the w component from the final result. This is fine
        #   for multiplying a matrix by a single 3d vector position, but if the vector being multiplied is added, or
        #   subtracted with another vector beforehand, then the result will be wrong, because the automatic w component
        #   of 1.0 will not be the correct value.
        wm = obj.matrix_world.to_3x3()
        # Length from upper_arm joint to elbow joint
        upper_arm_length = (wm @ (upper_arm - elbow)).length
        # Length from elbow joint to wrist joint
        lower_arm_length = (wm @ (elbow - wrist)).length
    else:
        # Length from upper_arm joint to elbow joint
        upper_arm_length = (upper_arm - elbow).length
        # Length from elbow joint to wrist joint
        lower_arm_length = (elbow - wrist).length

    return upper_arm_length + lower_arm_length


def head_to_hand(obj, worldspace=True):
    """Get the length from the head to the start of the wrist bone as if the armature was in t-pose"""
    # Since arms might not be flat, add the length of the arm to the x
    # coordinate of the upper arm

    """
    head_to_hand is the distance from headpos to (upper_arm - (arm_length, 0, 0))
    (please excuse the poorly drawn triangles)

    Avatar as seen from the front:
                                      head_to_hand   ¸ . o headpos
                                           ¸ . - ' `    /
    (upper_arm - (arm_length, 0, 0)) o ' ` - - - - - - o upper_arm
                                              ¦
                                          arm_length

    Subtract upper_arm from each point for simplicity
                         head_to_hand   ¸ . o (headpos - upper_arm)
                              ¸ . - ' `    /
    (-arm_length, 0, 0) o ' ` - - - - - - o (0,0,0)

    head_to_hand
     = ((headpos - upper_arm) - (-arm_length, 0, 0)).length
    Could be further simplified:
     = (headpos.x - upper_arm.x + arm_length, headpos.y - upper_arm.y, headpos.z - upper_arm.z).length
     = sqrt(
                (headpos.x - upper_arm.x + arm_length) ** 2
                + (headpos.y - upper_arm.y) ** 2
                + (headpos.z - upper_arm.z) ** 2
            )
    """
    headpos = get_bone("head", obj).head
    upper_arm = get_bone("right_arm", obj).head

    upper_arm_to_head = headpos - upper_arm
    if worldspace:
        # translation by the world matrix would be the same for both vectors, and we're only returning a length, so we
        # can ignore translation and use only the 3x3 part, the scale and rotation.
        upper_arm_to_head = obj.matrix_world.to_3x3() @ upper_arm_to_head

    arm_length = get_arm_length(obj, worldspace)

    # We're working with the right arm, which is on the -x side in Blender, so arm_length will be negative
    t_hand_pos = mathutils.Vector((-arm_length, 0, 0))

    return (upper_arm_to_head - t_hand_pos).length


def calculate_arm_rescaling(obj, head_arm_change):
    # Calculates the percent change in arm length needed to create a
    # given change in head-hand length.

    # This function gets called before start_pose_mode_with_reset is called in scale_to_floor, so the current mode could
    # be EDIT mode, which could have changes that are not yet propagated to the pose data
    # Object.update_from_editmode() only seems to update the Bones of the armature and not the PoseBones of the armature
    # Object, so I don't think that can be used instead of swapping
    need_mode_swap = obj.mode == "EDIT"
    if need_mode_swap:
        # EDIT mode
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="POSE", toggle=False)

    rarmpos = get_bone("right_arm", obj).head
    headpos = get_bone("head", obj).head

    if need_mode_swap:
        # Restore original mode
        bpy.ops.object.mode_set(mode="POSE", toggle=True)

    total_length = head_to_hand(obj, worldspace=False)
    print("Head to hand length is {}".format(total_length))
    arm_length = get_arm_length(obj, worldspace=False)
    print(f"Arm length is {arm_length}")
    neck_length = abs((headpos[2] - rarmpos[2]))

    # Sanity check - compare the difference between head_to_hand and manual
    # print("")
    # print("-------head_to_hand: %f" %total_length)
    # print("-------manual, assuming t-pose: %f" %(headpos - rhandpos).length)
    # print("")

    # Also derived using sympy. See below.
    shoulder_length = (
        math.sqrt((total_length - neck_length) * (total_length + neck_length))
        - arm_length
    )

    # funky equation for all this - derived with sympy:
    # solveset(Eq(a * x, sqrt((c * b + s)**2 + y**2)), b)
    # where
    # x is total length
    # c is arm length
    # y is neck length
    # a is head_arm_change
    # s is shoulder_length
    # Drawing a picture with the arm and neck as a right triangle is basically necessary to understand this

    arm_change = (
        math.sqrt(
            (head_arm_change * total_length - neck_length)
            * (head_arm_change * total_length + neck_length)
        )
        / arm_length
    ) - (shoulder_length / arm_length)

    return arm_change


def get_eye_height(obj, worldspace=True):
    try:
        left_eye = get_bone("left_eye", obj)
        right_eye = get_bone("right_eye", obj)
    except KeyError as ke:
        raise RuntimeError(f"Cannot identify two eye bones: {ke}")

    eye_average = (left_eye.head + right_eye.head) / 2

    if worldspace:
        # By coincidence, multiplying the full, 4d matrix_world works with eye_average, since the w component of
        # eye_average would be (1.0 + 1.0) / 2 = 1 if it were to be calculated from 4d left_eye and 4d right_eye
        return (obj.matrix_world @ eye_average).z
    else:
        return eye_average.z


def get_leg_length(arm):
    """Assuming exact symmetry of both legs, gets vertical leg length, from the start of the upper leg bone to the
    lowest part of mesh weighted to feet or a child bone of the feet. If no mesh is weighted to the feet (or a child
    bone, the lowest mesh vertex is used instead).
    :return: Worldspace vertical leg length"""
    # Assumes exact symmetry between right and left legs
    return get_bone_worldspace_z("left_leg", arm) - get_lowest_point()


def get_leg_proportions(arm):
    """Get the relative lengths in the worldspace z direction of each portion of the leg starting from the top of the
    leg and ending at the lowest vertex of the avatar's feet (or lowest vertex of the avatar if no vertices are weighted
    to the feet bones or children of the feet bones).

    Returns a tuple of the list of relative lengths and the total length of the leg.

    :return: [0.0, relative_length_to_knee, relative_length_to_ankle, 1.0], leg_worldspace_z - lowest_point
    """
    leg_average_z = (
        get_bone_worldspace_z("left_leg", arm) + get_bone_worldspace_z("right_leg", arm)
    ) / 2
    knee_average_z = (
        get_bone_worldspace_z("left_knee", arm)
        + get_bone_worldspace_z("right_knee", arm)
    ) / 2
    ankle_average_z = (
        get_bone_worldspace_z("left_ankle", arm)
        + get_bone_worldspace_z("right_ankle", arm)
    ) / 2
    lowest_point = get_lowest_point()

    total = leg_average_z - lowest_point
    # The first point is leg_average_z, which always results in 0.0
    # 1 - (leg_average_z - lowest_point) / (leg_average_z - lowest_point)
    # = 1 - 1 = 0
    # The last point is lowest_point, which always results in 1.0
    # 1 - (lowest_point - lowest_point) / total
    # = 1 - 0 / total = 1 - 0 = 1
    nl = (
        [0.0]
        + [1 - (i - lowest_point) / total for i in (knee_average_z, ankle_average_z)]
        + [1.0]
    )
    return nl, total


def scale_legs(arm, leg_scale_ratio, leg_thickness, scale_foot, thigh_percentage):
    leg_points, total_length = get_leg_proportions(arm)

    starting_portions = list([leg_points[i + 1] - leg_points[i] for i in range(3)])
    print("starting_portions: {}".format(starting_portions))

    # Foot scale is the percentage of the final it'll take up.
    foot_portion = (1 - leg_points[2]) * leg_thickness / leg_scale_ratio
    if scale_foot:
        foot_portion = (1 - leg_points[2]) * leg_thickness
    print("Foot portion: {}".format(foot_portion))
    print(
        "Leg thickness: {}, leg_scale_ratio: {}, leg_points: {}".format(
            leg_thickness, leg_scale_ratio, leg_points
        )
    )

    leg_portion = 1 - foot_portion

    # TODO: Add switch for maintaining existing thigh/calf proportions, make default(?)
    thigh_portion = leg_portion * thigh_percentage
    calf_portion = leg_portion - thigh_portion

    print(
        "calculated desired leg portions: {}".format(
            [thigh_portion, calf_portion, foot_portion]
        )
    )

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

    print(final_foot_scale)
    print(
        "Calculated final scales: thigh {} calf {} foot {}".format(
            final_thigh_scale, final_calf_scale, final_foot_scale
        )
    )

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


# def scale_absolute(upper_body_percent, arm_thickness_change, leg_thickness_change, scale_hand, thigh_percentage, custom_scale_ratio):
#     # Similar in purpose to scale_to_floor, now looking at torso size too.
#     #
#     arm = get_armature()

#     start_pose_mode_with_reset(arm)

#     lowest_point = get_lowest_point()

#     view_z = get_view_z(arm, custom_scale_ratio)
#     eye_z = get_eye_height(arm) - lowest_point

#     rescale_ratio = eye_z / view_z

#     leg_portion = get_leg_length(arm) / eye_z

#     # This is where it starts to differ from scale_to_floor
#     # Find how much the legs need to scale by to meet the target
#     leg_scale_ratio = upper_body_percent / get_upper_body_percentage(arm)

#     rescale_leg_ratio = 1 / (leg_portion * leg_scale_ratio)
#     rescale_arm_ratio = rescale_ratio / rescale_leg_ratio

#     arm_scale_ratio = calculate_arm_rescaling(arm, rescale_arm_ratio)


def scale_torso(arm, torso_scale_ratio):
    # The final distance measured is from the leg bones to the eyes,
    # but the distance lengthened is only from the leg bone roots to
    # the chest or upper chest

    if check_bone("upperchest", arm):
        scaled_top = get_bone_worldspace_z("upperchest", arm)
    else:
        scaled_top = get_bone_worldspace_z("chest", arm)

    scaled_bottom = (
        get_bone_worldspace_z("left_leg", arm) + get_bone_worldspace_z("right_leg", arm)
    ) / 2

    total_height = get_eye_height(arm) - scaled_bottom
    scaled_height = scaled_top - scaled_bottom

    print("Total height: {}, scaled height: {}".format(total_height, scaled_height))
    scale_ratio = 1 + ((total_height / scaled_height) * (torso_scale_ratio - 1))

    # Mark boundry bones as not inheriting scale
    boundry_bones = list(
        b.name
        for b in get_bone("hips", arm).children
        if b.name != get_bone("spine", arm).name
    )
    if check_bone("upperchest", arm):
        boundry_bones += [get_bone("upperchest", arm).name]
    else:
        boundry_bones += [get_bone("chest", arm).name]

    saved_bone_inherit_scales = {}
    for b in boundry_bones:
        # Every bone here either comes from a lookup or directly from
        # the armature, so it should be safe to referece pose.bones
        # directly without looking at overrides in this step
        bone = arm.pose.bones[b]
        saved_bone_inherit_scales[b] = arm.data.bones[bone.name].inherit_scale

        print("Disabling inherit scale on bone {}".format(b))
        arm.data.bones[bone.name].inherit_scale = "NONE"

    print("Scaling hip by {}".format(scale_ratio))
    get_bone("hips", arm).scale = (1, scale_ratio, 1)

    # Check that it worked as expected
    if check_bone("upperchest", arm):
        new_scaled_top = get_bone_worldspace_z("upperchest", arm)
    else:
        new_scaled_top = get_bone_worldspace_z("chest", arm)

    new_scaled_bottom = (
        get_bone_worldspace_z("left_leg", arm) + get_bone_worldspace_z("right_leg", arm)
    ) / 2

    new_total_height = get_eye_height(arm) - scaled_bottom
    print(
        "Torso Scaling Expected height: {}, actual height: {}".format(
            total_height * torso_scale_ratio, new_total_height
        )
    )

    # for b in boundry_bones:
    #     arm.data.bones[b].inherit_scale = saved_bone_inherit_scales[b]


def scale_to_floor(
    arm_to_legs,
    arm_thickness,
    leg_thickness,
    extra_leg_length,
    scale_hand,
    thigh_percentage,
    custom_scale_ratio,
    scale_relative,
    keep_head_size,
    upper_body_portion,
):
    arm = get_armature()

    # Possibly for these scale calculation parts, before we adjust any bones, we could change the armature pose to
    # 'REST' instead of resetting the pose and then taking measurements
    start_pose_mode_with_reset(arm)

    lowest_point = get_lowest_point()

    view_z = get_view_z(arm, custom_scale_ratio) + extra_leg_length
    eye_z = get_eye_height(arm) - lowest_point

    # TODO: add an option for people who *want* their legs below the floor.
    #
    # weirdos
    rescale_ratio = eye_z / view_z
    leg_height_portion = get_leg_length(arm) / eye_z

    if scale_relative:
        # This uses the arm_to_legs parameter, the method below doesn't
        rescale_leg_ratio = rescale_ratio**arm_to_legs
        rescale_arm_ratio = rescale_ratio ** (1 - arm_to_legs)
        leg_scale_ratio = 1 - (1 - (1 / rescale_leg_ratio)) / leg_height_portion
    elif keep_head_size:
        # To keep the head size the same, every bit of length taken
        # from the legs needs to be added to the torso, making their
        # scalings the inverse of each other. Note that the division
        # between upper and lower body is determined from the eyes
        current_ubp = get_upper_body_portion(arm)

        print(
            "current ubp: {}, desired ubp: {}".format(current_ubp, upper_body_portion)
        )
        torso_scale_ratio = upper_body_portion / current_ubp
        leg_scale_ratio = (1 - upper_body_portion) / (1 - current_ubp)

        # torso_scale_ratio = (1 + torso_scale_ratio) / 2
        # leg_scale_ratio = (1 + leg_scale_ratio) / 2

        # For debugging, get new scales
        eye_z = get_eye_height(arm)
        lowest_point = get_lowest_point()
        leg_average_z = (
            get_bone_worldspace_z("left_leg", arm)
            + get_bone_worldspace_z("right_leg", arm)
        ) / 2

        ntl = (eye_z - leg_average_z) * torso_scale_ratio
        ns = ntl / (ntl + ((leg_average_z - lowest_point) * leg_scale_ratio))

        print("Expected New scale: {}".format(ns))

        print("Torso scale ratio: {}".format(torso_scale_ratio))
        print("Leg scale ratio: {}".format(leg_scale_ratio))
        # If the chest isn't scaled, the shoulders shouldn't move at
        # all in this mode, so the entirety of the proportion scaling
        # happens in the arm lengthening
        rescale_arm_ratio = rescale_ratio

    else:
        # This uses the upper_body_portion parameter as the primary
        ubp = get_upper_body_portion(arm)
        ub_scale_ratio = ubp / upper_body_portion
        leg_scale_ratio = ub_scale_ratio + (
            (ub_scale_ratio * ubp - ubp) / (leg_height_portion)
        )
        rescale_leg_ratio = 1 / (leg_height_portion * (leg_scale_ratio - 1) + 1)
        rescale_arm_ratio = rescale_ratio / rescale_leg_ratio

    arm_scale_ratio = calculate_arm_rescaling(arm, rescale_arm_ratio)

    print("Total required scale factor is %f" % rescale_ratio)
    print(
        "Scaling legs by a factor of %f to %f"
        % (leg_scale_ratio, leg_scale_ratio * get_leg_length(arm))
    )
    print("Scaling arms by a factor of %f" % arm_scale_ratio)

    leg_thickness = leg_thickness + leg_scale_ratio * (1 - leg_thickness)
    arm_thickness = arm_thickness + arm_scale_ratio * arm_thickness

    scale_foot = False
    scale_legs(arm, leg_scale_ratio, leg_thickness, scale_foot, thigh_percentage)

    if keep_head_size:
        scale_torso(arm, torso_scale_ratio)

    # This kept getting me - make sure arms are set to inherit scale
    for b in ["left_elbow", "right_elbow", "left_wrist", "right_wrist"]:
        get_bone(b, arm).bone.inherit_scale = "FULL"

    for armbone in [get_bone("left_arm", arm), get_bone("right_arm", arm)]:
        armbone.scale = (arm_thickness, arm_scale_ratio, arm_thickness)

    if not scale_hand:
        for hand in [get_bone("left_wrist", arm), get_bone("right_wrist", arm)]:
            hand.scale = (1 / arm_thickness, 1 / arm_scale_ratio, 1 / arm_thickness)

            result_final_points, result_total_legs = get_leg_proportions(arm)
        print("Implemented leg portions: {}".format(result_final_points))

    # Apply the pose as rest pose, updating the meshes and their shape keys if they have them
    apply_pose_to_rest()


def move_to_floor():
    """Move the avatar down so that its lowest_point is at z=0 and set the origin of the armature and meshes to
    (armature_x, armature_y, z=0)"""
    # Currently, the meshes have their origin set to the same as the armature, but it might be better to not touch the
    # origins of the meshes, in-case there is a modifier on an Object that is using the position of one of the meshes,
    # e.g. if one of the meshes is off to one side of the avatar and has a mirror modifier that hasn't been applied.

    # Move armature object down by get_lowest_point() (also moving the meshes, since they must be parented to the
    # armature)
    arm = get_armature()
    # arm.location is unreliable if the armature has a parent. The armature *shouldn't* be parented to something else,
    # but in-case it is, we can get worldspace location from the translation part of its .matrix_world
    arm_location_world = arm.matrix_world.translation
    # Updating a component of the matrix_world's translation will automatically update the armature Object's location,
    # so we can simply subtract get_lowest_point() from the z component to move the armature down so that the lowest
    # part of the avatar's meshes is at z=0 in worldspace.
    arm_location_world.z -= get_lowest_point()

    # Set origin of armature and each mesh to (worldspace_arm_x, worldspace_arm_y, 0)
    new_origin = arm_location_world.copy()
    new_origin.z = 0
    # Cursor location is always in worldspace
    bpy.context.scene.cursor.location = new_origin

    # Get all meshes and append the armature since we're setting the origin for all of them
    all_objects = get_body_meshes()
    all_objects.append(arm)

    # While bpy.ops.object.origin_set doesn't raise an error when encountering multi-user data, changing the origin of
    # one such object will also change the origin of all other objects sharing the same data, but if the objects were in
    # different places, they won't have their origins set to the same place.
    for obj in all_objects:
        if obj.data.users > 1:
            # Replace multi-user data with single-user copies
            obj.data = obj.data.copy()

    # Using a context override means we don't have to actually go and select the objects we want to run the operator on
    # (or deselect the objects we don't want to run the operator on).
    #
    # bpy.ops.object.origin_set gets the objects to act on from selected_editable_objects.
    # It will set the origin of each object in the order that they are in the list, though order doesn't seem to matter
    # for type='ORIGIN_CURSOR'. Alternatively, if active_object is set to an Object in the override and that Object is
    # in selected_editable_objects, it will be moved to the start of the list.
    #
    # To find this information about the operator, you have to find the operator in Blender's C source code and read the
    # code to figure out which attributes of the context it uses in both its 'exec' and 'poll' callbacks. You can get
    # the C name of an operator from its idname function: bpy.ops.object.origin_set.idname() -> 'OBJECT_OT_origin_set'.
    override = dict(active_object=None, selected_editable_objects=all_objects)
    op_override(bpy.ops.object.origin_set, override, type="ORIGIN_CURSOR")


def recursive_object_mode(objects: Iterable[bpy.types.Object]):
    """Set objects into OBJECT mode"""
    # If an object is already in OBJECT mode, we'll skip it
    objects = [o for o in objects if o.mode != "OBJECT"]
    if objects:
        op_mode_set = bpy.ops.object.mode_set
        with temp_ensure_enabled(*objects):
            for o in objects:
                # poll checks that the active_object is 'editable' (hide_viewport or hide_viewport inherited from parent
                # or collection is False, it's not from a linked library and is not a non-editable library override
                # object)
                override = dict(active_object=o)
                op_override(op_mode_set, override, mode="OBJECT", toggle=False)


def recursive_scale(objects: Iterable[bpy.types.Object]):
    """Apply scale transforms to objects, assumes the objects are already in OBJECT mode"""
    scene_objects = bpy.context.scene.objects
    objects = [o for o in objects if o.name in scene_objects]
    # poll checks that the active object is in OBJECT mode and is in the current scene
    # exec runs on selected_editable_objects
    if objects:
        override = dict(active_object=objects[0], selected_editable_objects=objects)
        op_override(
            bpy.ops.object.transform_apply,
            override,
            scale=True,
            location=False,
            rotation=False,
            properties=False,
        )


def scale_to_height(new_height, scale_eyes):
    obj = get_armature()
    if scale_eyes:
        old_height = get_eye_height(obj) - get_lowest_point()
    else:
        old_height = get_highest_point() - get_lowest_point()

    print("Old height is %f" % old_height)

    scale_ratio = new_height / old_height
    print("Scaling by %f to achieve target height" % scale_ratio)
    bpy.context.scene.cursor.location = obj.matrix_world.translation
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    obj.scale = obj.scale * scale_ratio

    obj_and_all_children = children_recursive(obj) + [obj]

    recursive_object_mode(obj_and_all_children)
    recursive_scale(obj_and_all_children)


def center_model(worldspace=True):
    arm = get_armature()
    if worldspace:
        # Move to world origin
        arm.matrix_world.translation = (0, 0, 0)
    else:
        # Move to parent object (or world origin if not parented)
        arm.matrix_local.translation = (0, 0, 0)


def rescale_main(
    new_height,
    arm_to_legs,
    arm_thickness,
    leg_thickness,
    extra_leg_length,
    scale_hand,
    thigh_percentage,
    custom_scale_ratio,
    scale_eyes,
    scale_relative,
    keep_head_size,
    upper_body_percent,
):
    context = bpy.context
    s = context.scene

    if not s.debug_no_adjust:
        scale_to_floor(
            arm_to_legs,
            arm_thickness,
            leg_thickness,
            extra_leg_length,
            scale_hand,
            thigh_percentage,
            custom_scale_ratio,
            scale_relative,
            keep_head_size,
            upper_body_percent,
        )
    if not s.debug_no_floor:
        move_to_floor()

    result_final_points, result_total_legs = get_leg_proportions(get_armature())
    print("Final Implemented leg portions: {}".format(result_final_points))

    if not s.debug_no_scale:
        scale_to_height(new_height, scale_eyes)

    if s.center_model:
        center_model()

    if context.mode != "OBJECT":
        # Ensure we go to OBJECT mode so that object.select_all can be called
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


def shrink_hips():
    arm = get_armature()

    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT", toggle=False)

    left_leg_name = get_bone("left_leg", arm).name
    right_leg_name = get_bone("right_leg", arm).name
    leg_start = (
        arm.data.edit_bones[left_leg_name].head[2]
        + arm.data.edit_bones[right_leg_name].head[2]
    ) / 2
    spine_start = arm.data.edit_bones["Spine"].head[2]

    # Make the hip tiny - 90 of the way between the start of the legs
    # and the start of the spine

    arm.data.edit_bones["Hips"].head[2] = leg_start + (spine_start - leg_start) * 0.9
    arm.data.edit_bones["Hips"].head[1] = arm.data.edit_bones["Spine"].head[1]
    arm.data.edit_bones["Hips"].head[0] = arm.data.edit_bones["Spine"].head[0]

    bpy.ops.object.mode_set(mode="EDIT", toggle=True)
    bpy.ops.object.select_all(action="DESELECT")


class ArmatureRescale(ArmatureOperator):
    """Script to scale most aspects of an armature for use in vrchat"""

    bl_idname = "armature.rescale"
    bl_label = "Rescale Armature"
    bl_options = {"REGISTER", "UNDO"}

    # set_properties()
    # target_height: bpy.types.Scene.target_height
    # arm_to_legs: bpy.types.Scene.arm_to_legs
    # arm_thickness: bpy.types.Scene.arm_thickness
    # leg_thickness: bpy.types.Scene.leg_thickness
    # extra_leg_length: bpy.types.Scene.extra_leg_length
    # scale_hand: bpy.types.Scene.scale_hand
    # thigh_percentage: bpy.types.Scene.thigh_percentage
    # scale_eyes: bpy.types.Scene.scale_eyes

    def execute_main(self, context, arm, meshes):
        rescale_main(
            self.target_height,
            self.arm_to_legs / 100.0,
            self.arm_thickness / 100.0,
            self.leg_thickness / 100.0,
            self.extra_leg_length,
            self.scale_hand,
            self.thigh_percentage / 100.0,
            self.custom_scale_ratio,
            self.scale_eyes,
            self.scale_upper_body,
            self.keep_head_size,
            self.upper_body_percentage / 100,
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        s = context.scene
        self.target_height = s.target_height
        self.arm_to_legs = s.arm_to_legs
        self.arm_thickness = s.arm_thickness
        self.leg_thickness = s.leg_thickness
        self.extra_leg_length = s.extra_leg_length
        self.scale_hand = s.scale_hand
        self.thigh_percentage = s.thigh_percentage
        self.custom_scale_ratio = s.custom_scale_ratio
        self.scale_eyes = s.scale_eyes
        self.scale_upper_body = s.imscale_scale_upper_body
        self.keep_head_size = s.imscale_keep_head_size
        self.upper_body_percentage = s.upper_body_percentage

        return self.execute(context)


class ArmatureShrinkHip(ArmatureOperator):
    """Shrinks the hip bone in a humaniod avatar to be much closer to the spine location"""

    bl_idname = "armature.shrink_hips"
    bl_label = "Shrink Hips"
    bl_options = {"REGISTER", "UNDO"}

    def execute_main(self, context, arm, meshes):
        shrink_hips()
        return {"FINISHED"}


class UIGetCurrentHeight(ArmatureOperator):
    """Sets target height based on the current height"""

    bl_idname = "armature.get_avatar_height"
    bl_label = "Get Current Avatar Height"
    bl_options = {"REGISTER", "UNDO"}

    def execute_main(self, context, arm, meshes):
        height = 1.5  # Placeholder
        lowest_point = get_lowest_point()
        if context.scene.scale_eyes:
            height = get_eye_height(arm) - lowest_point
        else:
            height = get_highest_point() - lowest_point
        context.scene.target_height = height
        return {"FINISHED"}


class UIGetScaleRatio(ArmatureOperator):
    """Gets the custom scaling ratio based on the current avatar's proportions"""

    bl_idname = "armature.get_scale_ratio"
    bl_label = "Get Current Avatar Scale Ratio"
    bl_options = {"REGISTER", "UNDO"}

    def execute_main(self, context, arm, meshes):
        scale = get_current_scaling(arm)
        context.scene.custom_scale_ratio = scale
        return {"FINISHED"}


class UIGetCurrentUpperLegPercent(ArmatureOperator):
    """Sets the Upper Leg Percent based on the current leg proportions"""

    bl_idname = "armature.get_avatar_upper_leg_percent"
    bl_label = "Get Current Avatar Upper Leg Percent"
    bl_options = {"REGISTER", "UNDO"}

    def execute_main(self, context, arm, meshes):
        # [0.0, <to knee joint>, <to ankle joint>, 1.0]
        proportions, _total_length = get_leg_proportions(arm)
        current_thigh_percentage = proportions[1] / proportions[2]
        context.scene.thigh_percentage = current_thigh_percentage * 100.0
        return {"FINISHED"}


class UIGetUpperBodyPercent(ArmatureOperator):
    """Gets the percent of the avatars height used by upper body - from eyes to legs"""

    bl_idname = "armature.get_upper_body_percentage"
    bl_label = "Get Current Avatar Upper Body Percentage"
    bl_options = {"REGISTER", "UNDO"}

    def execute_main(self, context, arm, meshes):
        scale = get_upper_body_portion(arm) * 100
        context.scene.upper_body_percentage = scale
        return {"FINISHED"}


_register, _unregister = bpy.utils.register_classes_factory(
    [
        ArmatureRescale,
        ArmatureShrinkHip,
        UIGetCurrentHeight,
        UIGetScaleRatio,
        UIGetCurrentUpperLegPercent,
        UIGetUpperBodyPercent,
    ]
)


def ops_register():
    print("Registering Armature tuning add-on")
    _register()
    print("Registering Armature tuning add-on")


def ops_unregister():
    print("Attempting to unregister armature turing add-on")
    _unregister()
    print("Unregistering Armature tuning add-on")


if __name__ == "__main__":
    register()

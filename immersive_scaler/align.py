import bpy
import mathutils
import importlib
import statistics

from . import common
from . import posemode
from . import bones
from . import spread_fingers

importlib.reload(common)
importlib.reload(posemode)
importlib.reload(bones)
importlib.reload(spread_fingers)

from .common import (
    get_all_armatures,
    get_body_meshes,
    ArmatureOperator,
    temp_ensure_enabled,
)
from .posemode import start_pose_mode_with_reset, apply_pose_to_rest
from .bones import get_bone, bone_lookup, check_bone
from .spread_fingers import point_bone


def scale_torso(context, ref_arm, scale_arm):
    # Match scale to ref's neck and upper legs

    scale_leg_center = (
        get_bone("left_leg", scale_arm).head + get_bone("right_leg", scale_arm).head
    ) / 2
    ref_leg_center = (
        get_bone("left_leg", ref_arm).head + get_bone("right_leg", ref_arm).head
    ) / 2

    translation = ref_leg_center - scale_leg_center
    hips = get_bone("hips", scale_arm)
    translation.rotate(hips.bone.matrix_local.to_quaternion().inverted())
    hips.location = translation

    # Translations aren't reflected in coordinates unless the pose
    # mode is applied
    apply_pose_to_rest(arm=scale_arm)
    start_pose_mode_with_reset(scale_arm)

    # get the bones again since the pose bone objects only last as
    # long as pose mode does
    scale_leg_center = (
        get_bone("left_leg", scale_arm).head + get_bone("right_leg", scale_arm).head
    ) / 2
    ref_leg_center = (
        get_bone("left_leg", ref_arm).head + get_bone("right_leg", ref_arm).head
    ) / 2

    scale_shoulder_center = (
        get_bone("left_shoulder", scale_arm).head
        + get_bone("right_shoulder", scale_arm).head
    ) / 2

    ref_shoulder_center = (
        get_bone("left_shoulder", ref_arm).head
        + get_bone("right_shoulder", ref_arm).head
    ) / 2

    # scale_neck = get_bone("neck", scale_arm)
    # ref_neck = get_bone("neck", ref_arm)

    scale_torso = (scale_shoulder_center - ref_leg_center).length
    ref_torso = (ref_shoulder_center - ref_leg_center).length

    base_scaling = ref_torso / scale_torso

    get_bone("hips", scale_arm).scale = mathutils.Vector(
        (base_scaling, base_scaling, base_scaling)
    )

    # The scaling is reletive to the hips but the movement made the
    # bones line up. Easier to just line it up again
    apply_pose_to_rest(arm=scale_arm)
    start_pose_mode_with_reset(scale_arm)

    scale_leg_center = (
        get_bone("left_leg", scale_arm).head + get_bone("right_leg", scale_arm).head
    ) / 2
    ref_leg_center = (
        get_bone("left_leg", ref_arm).head + get_bone("right_leg", ref_arm).head
    ) / 2

    translation = ref_leg_center - scale_leg_center
    hips = get_bone("hips", scale_arm)
    translation.rotate(hips.bone.matrix_local.to_quaternion().inverted())
    hips.location = translation

    # Correction for lining up the knees and shoulders. If the base is
    # the same it should be a no-op
    hip_scale = (
        get_bone("left_leg", ref_arm).head - get_bone("right_leg", ref_arm).head
    ).length / (
        get_bone("left_leg", scale_arm).head - get_bone("right_leg", scale_arm).head
    ).length
    get_bone("hips", scale_arm).scale = (hip_scale, 1.0, 1.0)
    bpy.context.view_layer.update()

    chest_scale = (
        get_bone("left_shoulder", ref_arm).head
        - get_bone("right_shoulder", ref_arm).head
    ).length / (
        get_bone("left_shoulder", scale_arm).head
        - get_bone("right_shoulder", scale_arm).head
    ).length

    get_bone("left_shoulder", scale_arm).parent.scale = (chest_scale, 1.0, 1.0)
    # Try not to scale the head
    if check_bone("neck", scale_arm):
        get_bone("neck", scale_arm).scale = (1 / (hip_scale * chest_scale), 1.0, 1.0)

    apply_pose_to_rest(arm=scale_arm)
    start_pose_mode_with_reset(scale_arm)

    # Attempt to move the shoulders back a little bit by rotating the
    # whole model, counter rotating the neck so the head is still
    # as vertical as it was before

    scale_shoulder_center = (
        get_bone("left_shoulder", scale_arm).head
        + get_bone("right_shoulder", scale_arm).head
    ) / 2

    ref_shoulder_center = (
        get_bone("left_shoulder", ref_arm).head
        + get_bone("right_shoulder", ref_arm).head
    ) / 2

    spine = get_bone("hips", scale_arm)
    v1 = (ref_shoulder_center - spine.head).normalized()
    v2 = (scale_shoulder_center - spine.head).normalized()

    sq = spine.matrix.to_quaternion()
    sq.rotate(spine.matrix.inverted())
    sq.rotate(v2.rotation_difference(v1))
    spine.rotation_quaternion = sq

    if check_bone("neck", scale_arm):
        neck = get_bone("neck", scale_arm)
        nq = neck.matrix.to_quaternion()
        nq.rotate(neck.matrix.inverted())
        nq.rotate(v1.rotation_difference(v2))
        neck.rotation_quaternion = nq

    apply_pose_to_rest(arm=scale_arm)
    start_pose_mode_with_reset(scale_arm)

    return base_scaling


def get_scaling_rotations(ref_bone, scale_bone):
    # Scaling should prioritize having children line up. For every set
    # of matching children, find the transform needed to the parent to
    # get the children to line up, then perform the one that makes the
    # most line up.
    child_target_scales = []
    child_target_rotations = []
    for s_child in scale_bone.children:
        for r_child in ref_bone.children:
            if s_child.name == r_child.name or (
                bone_lookup(s_child.name) == bone_lookup(r_child.name)
                and bone_lookup(r_child.name) != None
            ):

                # Find ideal scale
                scale = (r_child.head - ref_bone.head).length / (
                    s_child.head - scale_bone.head
                ).length
                child_target_scales.append(scale)

                # I'm not sure if it's possible to get a vector scale
                # *and* rotation, there are too many degrees of
                # freedom and they will overlap if calculated separately.

                # find rotation difference between s_child.head -> scale_bone.head -> r_child.head
                # Vectors should be in the space of scale_bone
                v1 = (s_child.head - scale_bone.head).normalized()
                v2 = (r_child.head - scale_bone.head).normalized()
                child_target_rotations.append(v1.rotation_difference(v2))

                # For the wrist bone, always scale to the middle
                # finger if it's available
                if "wrist" in bone_lookup(scale_bone.name) and "middle" in bone_lookup(
                    s_child.name
                ):
                    starting_rotation = v1.rotation_difference(v2)
                    return [scale], [starting_rotation]

    return child_target_scales, child_target_rotations


def align_bones(ref_bone, scale_bone, arm_thickness, leg_thickness, parent_scale):
    # Special case - for now don't scale the hands. There's too much
    # variation in finger finger bone positions. Maybe something to
    # make into a toglge?
    # if (
    #     bone_lookup(scale_bone.name) == "right_wrist"
    #     or bone_lookup(scale_bone.name) == "left_wrist"
    # ):
    #     pass

    # Check that the starting position is the same, partially as a
    # sanity check. Continuing to align when it's off to start will
    # throw off every child way more
    ref_oloc = ref_bone.matrix.decompose()[0]
    scale_oloc = (
        scale_bone.matrix @ mathutils.Matrix.Translation(scale_bone.location)
    ).decompose()[0]
    if (ref_oloc - scale_oloc).length > 0.01:
        print(
            "Bone {} is off by {}, skipping".format(
                scale_bone.name, ref_oloc - scale_oloc
            )
        )
        return

    child_target_scales, child_target_rotations = get_scaling_rotations(
        ref_bone, scale_bone
    )

    # Default to not changing scaling if there are no children
    scale_vector = scale_bone.scale

    if len(child_target_scales) > 0:
        sf = statistics.median(child_target_scales)
        scale_vector = (sf, sf, sf)

    # Inherit scale should be on, so if the bone is a root of the arm
    # or leg, use the scale factor
    def lerp(a, b, f):
        return (1 - f) * a + f * b

    if bone_lookup(scale_bone.name) in ["left_leg", "right_leg"]:
        scale_vector = (
            lerp(scale_bone.scale[0], scale_vector[0], leg_thickness),
            scale_vector[1],
            lerp(scale_bone.scale[2], scale_vector[2], leg_thickness),
        )

    if bone_lookup(scale_bone.name) in ["left_arm", "right_arm"]:
        scale_vector = (
            lerp(scale_bone.scale[0], scale_vector[0], arm_thickness),
            scale_vector[1],
            lerp(scale_bone.scale[2], scale_vector[2], arm_thickness),
        )

    if bone_lookup(scale_bone.name) in ["left_wrist", "right_wrist"]:
        scale_vector = tuple(1.0 / ps for ps in parent_scale)

    print("Scaling bone {} by factor {}".format(scale_bone.name, scale_vector))
    scale_bone.scale = scale_vector
    bpy.context.view_layer.update()

    if len(child_target_rotations) > 0:
        bq = scale_bone.matrix.to_quaternion()
        bq.rotate(child_target_rotations[-1])
        bq.rotate(scale_bone.matrix.inverted())
        scale_bone.rotation_quaternion = bq

    bpy.context.view_layer.update()

    # Recurse to children with matchinng ames
    for s_child in scale_bone.children:
        for r_child in ref_bone.children:
            if s_child.name == r_child.name or (
                bone_lookup(s_child.name) != None
                and bone_lookup(s_child.name) == bone_lookup(r_child.name)
            ):
                if not bone_lookup(s_child.name):
                    print(
                        "bone {} not a main human armature bone, skipping".format(
                            s_child.name
                        )
                    )
                    continue
                align_bones(
                    r_child,
                    s_child,
                    arm_thickness,
                    leg_thickness,
                    tuple(
                        scale_vector[i] * parent_scale[i]
                        for i in range(len(scale_vector))
                    ),
                )


def align_armatures(
    context, arm_ref_name, arm_scaling_name, arm_thickness, leg_thickness
):
    # TODO: completely rewrite or something
    ref_arm = context.scene.objects.get(arm_ref_name)
    scale_arm = context.scene.objects.get(arm_scaling_name)

    if ref_arm == scale_arm:
        # Should probably be an error
        return

    start_pose_mode_with_reset(scale_arm)

    base_scale = scale_torso(context, ref_arm, scale_arm)

    # Special case for Hips, optional?
    # Leave out for now, it would break spine weighting
    # For now, better to stretch?

    # Base case set the hip position
    # get_bone("hips", scale_arm).matrix = get_bone("hips", ref_arm).matrix

    # A view layer update doesn't cut it for matching hip position,
    # fortunately this is the only time we need to apply and reset in
    # the middle
    apply_pose_to_rest(arm=scale_arm)
    start_pose_mode_with_reset(scale_arm)

    # Recursive call to scale each of the limbs
    for limb_start in ["right_leg", "left_leg", "right_shoulder", "left_shoulder"]:
        pass
        align_bones(
            get_bone(limb_start, ref_arm),
            get_bone(limb_start, scale_arm),
            arm_thickness,
            leg_thickness,
            (1.0, 1.0, 1.0),
        )

    apply_pose_to_rest(arm=scale_arm)


class ArmatureAlign(ArmatureOperator):
    """Takes one armature and aligns it to another"""

    bl_idname = "armature.imscale_align"
    bl_label = "Align Armatures"
    bl_options = {"REGISTER", "UNDO"}

    def execute_main(self, context, arm, meshes):
        ra = context.scene.objects.get(self.scale_armature_ref)
        sa = context.scene.objects.get(self.scale_armature_arm)
        meshes = get_body_meshes(sa)
        with temp_ensure_enabled(sa, ra, *meshes):
            align_armatures(
                context,
                self.scale_armature_ref,
                self.scale_armature_arm,
                self.arm_thickness / 100.0,
                self.leg_thickness / 100.0,
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        s = context.scene

        self.scale_armature_ref = s.imscale_scale_armature_ref
        self.scale_armature_arm = s.imscale_scale_armature_arm
        self.arm_thickness = s.arm_thickness
        self.leg_thickness = s.leg_thickness
        return self.execute(context)


## Ui operators
class SearchMenuOperator_scale_armature_ref(bpy.types.Operator):
    bl_description = "Select the armature to use as a reference for scaling"
    bl_idname = "scene.search_menu_scale_armature_ref"
    bl_label = "Scale Armature Reference"
    bl_property = "my_enum"

    my_enum: bpy.props.EnumProperty(
        name="Scaling Reference Armature",
        description="Target armature for scaling",
        items=get_all_armatures,
    )

    def execute(self, context):
        context.scene.imscale_scale_armature_ref = self.my_enum
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {"FINISHED"}


class SearchMenuOperator_scale_armature_arm(bpy.types.Operator):
    bl_description = "Select the armature to scale"
    bl_idname = "scene.search_menu_scale_armature_arm"
    bl_label = "Scale Armature"
    bl_property = "my_enum"

    my_enum: bpy.props.EnumProperty(
        name="Scaling Active Armature",
        description="Active Armature to scale",
        items=get_all_armatures,
    )

    def execute(self, context):
        context.scene.imscale_scale_armature_arm = self.my_enum
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {"FINISHED"}


_register, _unregister = bpy.utils.register_classes_factory(
    [
        ArmatureAlign,
        SearchMenuOperator_scale_armature_ref,
        SearchMenuOperator_scale_armature_arm,
    ]
)


def ops_register():
    print("Registering Armature Aligning add-on")
    _register()


def ops_unregister():
    print("Deregistering Armature Aligning add-on")
    _unregister()


if __name__ == "__main__":
    _register()

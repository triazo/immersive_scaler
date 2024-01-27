import bpy
import importlib
import numpy as np

from typing import cast

from . import common

importlib.reload(common)

from .common import get_armature, get_body_meshes, op_override


_ZERO_ROTATION_QUATERNION = np.array([1, 0, 0, 0], dtype=np.single)


def start_pose_mode_with_reset(arm):
    """Replacement for Cats 'start pose mode' operator"""
    vl_objects = bpy.context.view_layer.objects
    if vl_objects.active != arm:
        if bpy.context.mode != "OBJECT":
            # Exit to OBJECT mode with whatever is the currently active object
            bpy.ops.object.mode_set(mode="OBJECT")
        # Set the armature as the active object
        vl_objects.active = arm

    if arm.mode != "POSE":
        # Open the armature in pose mode
        bpy.ops.object.mode_set(mode="POSE")

    # Clear the current pose of the armature (doesn't require POSE mode, just must not be in EDIT mode)
    reset_current_pose(arm.pose.bones)
    # Ensure that the armature data is set to pose position, otherwise setting a pose has no effect
    arm.data.pose_position = "POSE"


def reset_current_pose(pose_bones):
    """Resets the location, scale and rotation of each pose bone to the rest pose."""
    num_bones = len(pose_bones)
    # 3 components: X, Y, Z, set each bone to (0,0,0)
    pose_bones.foreach_set("location", np.zeros(num_bones * 3, dtype=np.single))
    # 3 components: X, Y, Z, set each bone to (1,1,1)
    pose_bones.foreach_set("scale", np.ones(num_bones * 3, dtype=np.single))
    # 4 components: W, X, Y, Z, set each bone to (1, 0, 0, 0)
    pose_bones.foreach_set(
        "rotation_quaternion", np.tile(_ZERO_ROTATION_QUATERNION, num_bones)
    )


def _create_armature_mod_for_apply(armature_obj, mesh_obj, preserve_volume):
    armature_mod = cast(
        bpy.types.ArmatureModifier,
        mesh_obj.modifiers.new("IMScalePoseToRest", "ARMATURE"),
    )
    armature_mod.object = armature_obj
    # Rotating joints tends to scale down neighboring geometry, up to nearly zero at 180 degrees from rest position. By
    # enabling Preserve Volume, this no longer happens, but there is a 'gap', a discontinuity when going past 180
    # degrees (presumably the rotation effectively jumps to negative when going past 180 degrees)
    # This does have an effect when scaling bones, but it's unclear if it's a beneficial effect or even noticeable in
    # most cases.
    armature_mod.use_deform_preserve_volume = preserve_volume
    return armature_mod


def _apply_armature_to_mesh_with_no_shape_keys(armature_obj, mesh_obj, preserve_volume):
    armature_mod = _create_armature_mod_for_apply(
        armature_obj, mesh_obj, preserve_volume
    )
    me = mesh_obj.data
    if me.users > 1:
        # Can't apply modifiers to multi-user data, so make a copy of the mesh and set it as the object's data
        me = me.copy()
        mesh_obj.data = me
    # In the unlikely case that there was already a modifier with the same name as the new modifier, the new
    # modifier will have ended up with a different name
    mod_name = armature_mod.name
    # Context override to let us run the modifier operators on mesh_obj, even if it's not the active object
    context_override = {"object": mesh_obj}
    # Moving the modifier to the first index will prevent an Info message about the applied modifier not being
    # first and potentially having unexpected results.
    if bpy.app.version >= (2, 90, 0):
        # modifier_move_to_index was added in Blender 2.90
        op_override(
            bpy.ops.object.modifier_move_to_index,
            context_override,
            modifier=mod_name,
            index=0,
        )
    else:
        # The newly created modifier will be at the bottom of the list
        armature_mod_index = len(mesh_obj.modifiers) - 1
        # Move the modifier up until it's at the top of the list
        for _ in range(armature_mod_index):
            op_override(
                bpy.ops.object.modifier_move_up, context_override, modifier=mod_name
            )
    op_override(bpy.ops.object.modifier_apply, context_override, modifier=mod_name)


def _apply_armature_to_mesh_with_shape_keys(armature_obj, mesh_obj, preserve_volume):
    # The active shape key will be changed, so save the current active index, so it can be restored afterwards
    old_active_shape_key_index = mesh_obj.active_shape_key_index

    # Shape key pinning shows the active shape key in the viewport without blending; effectively what you see when
    # in edit mode. Combined with an armature modifier, we can use this to figure out the correct positions for all
    # the shape keys.
    # Save the current value, so it can be restored afterwards.
    old_show_only_shape_key = mesh_obj.show_only_shape_key
    mesh_obj.show_only_shape_key = True

    # Temporarily remove vertex_groups from and disable mutes on shape keys because they affect pinned shape keys
    me = mesh_obj.data
    if me.users > 1:
        # Imagine two objects in different places with the same mesh data. Both objects can move different amounts
        # (they can even have completely different vertex groups), but we can only apply the movement to one of these
        # objects, so create a copy and set that copy as mesh_obj's data.
        me = me.copy()
        mesh_obj.data = me
    shape_key_vertex_groups = []
    shape_key_mutes = []
    key_blocks = me.shape_keys.key_blocks
    for shape_key in key_blocks:
        shape_key_vertex_groups.append(shape_key.vertex_group)
        shape_key.vertex_group = ""
        shape_key_mutes.append(shape_key.mute)
        shape_key.mute = False

    # Temporarily disable all modifiers from showing in the viewport so that they have no effect
    mods_to_reenable_viewport = []
    for mod in mesh_obj.modifiers:
        if mod.show_viewport:
            mod.show_viewport = False
            mods_to_reenable_viewport.append(mod)

    # Temporarily add a new armature modifier
    armature_mod = _create_armature_mod_for_apply(
        armature_obj, mesh_obj, preserve_volume
    )

    # cos are xyz positions and get flattened when using the foreach_set/foreach_get functions, so the array length
    # will be 3 times the number of vertices
    co_length = len(me.vertices) * 3
    # We can re-use the same array over and over
    eval_verts_cos_array = np.empty(co_length, dtype=np.single)

    # The first shape key will be the first one we'll affect, so set it as active before we get the depsgraph to avoid
    # having to update the depsgraph
    mesh_obj.active_shape_key_index = 0
    # depsgraph lets us evaluate objects and get their state after the effect of modifiers and shape keys
    # Get the depsgraph
    depsgraph = bpy.context.evaluated_depsgraph_get()
    # Evaluate the mesh
    evaluated_mesh_obj = mesh_obj.evaluated_get(depsgraph)

    # The cos of the vertices of the evaluated mesh include the effect of the pinned shape key and all the
    # modifiers (in this case, only the armature modifier we added since all the other modifiers are disabled in
    # the viewport).
    # This combination gives the same effect as if we'd applied the armature modifier to a mesh with the same
    # shape as the active shape key, so we can simply set the shape key to the evaluated mesh position.
    #
    # Get the evaluated cos
    evaluated_mesh_obj.data.vertices.foreach_get("co", eval_verts_cos_array)
    # Set the 'basis' (reference) shape key
    key_blocks[0].data.foreach_set("co", eval_verts_cos_array)
    # And also set the mesh vertices to ensure that the two remain in sync
    me.vertices.foreach_set("co", eval_verts_cos_array)

    # For the remainder of the shape keys, we only need to update the shape key itself
    for i, shape_key in enumerate(key_blocks[1:], start=1):
        # As shape key pinning is enabled, when we change the active shape key, it will change the state of the mesh
        mesh_obj.active_shape_key_index = i

        # In order for the change to the active shape key to take effect, the depsgraph has to be updated
        depsgraph.update()

        # Get the cos of the vertices from the evaluated mesh
        evaluated_mesh_obj.data.vertices.foreach_get("co", eval_verts_cos_array)
        # And set the shape key to those same cos
        shape_key.data.foreach_set("co", eval_verts_cos_array)

    # Restore temporarily changed attributes and remove the added armature modifier
    for mod in mods_to_reenable_viewport:
        mod.show_viewport = True
    mesh_obj.modifiers.remove(armature_mod)
    for shape_key, vertex_group, mute in zip(
        me.shape_keys.key_blocks, shape_key_vertex_groups, shape_key_mutes
    ):
        shape_key.vertex_group = vertex_group
        shape_key.mute = mute
    mesh_obj.active_shape_key_index = old_active_shape_key_index
    mesh_obj.show_only_shape_key = old_show_only_shape_key


def apply_pose_to_rest(preserve_volume=False, arm=None):
    """Apply pose to armature and meshes, taking into account shape keys on the meshes.
    The armature must be in Pose mode."""
    if not arm:
        arm = get_armature()
    meshes = get_body_meshes(arm)
    for mesh_obj in meshes:
        me = cast(bpy.types.Mesh, mesh_obj.data)
        if me:
            if me.shape_keys and me.shape_keys.key_blocks:
                # The mesh has shape keys
                shape_keys = me.shape_keys
                key_blocks = shape_keys.key_blocks
                if len(key_blocks) == 1:
                    # The mesh only has a basis shape key, so we can remove it and then add it back afterwards
                    # Get basis shape key
                    basis_shape_key = key_blocks[0]
                    # Save the name of the basis shape key
                    original_basis_name = basis_shape_key.name
                    # Remove the basis shape key so there are now no shape keys
                    mesh_obj.shape_key_remove(basis_shape_key)
                    # Apply the pose to the mesh
                    _apply_armature_to_mesh_with_no_shape_keys(
                        arm, mesh_obj, preserve_volume
                    )
                    # Add the basis shape key back with the same name as before
                    mesh_obj.shape_key_add(name=original_basis_name)
                else:
                    # Apply the pose to the mesh, taking into account the shape keys
                    _apply_armature_to_mesh_with_shape_keys(
                        arm, mesh_obj, preserve_volume
                    )
            else:
                # The mesh doesn't have shape keys, so we can easily apply the pose to the mesh
                _apply_armature_to_mesh_with_no_shape_keys(
                    arm, mesh_obj, preserve_volume
                )
    # Once the mesh and shape keys (if any) have been applied, the last step is to apply the current pose of the
    # bones as the new rest pose.
    #
    # From the poll function, armature_obj must already be in pose mode, but it's possible it might not be the
    # active object e.g., the user has multiple armatures opened in pose mode, but a different armature is currently
    # active. We can use an operator override to tell the operator to treat armature_obj as if it's the active
    # object even if it's not, skipping the need to actually set armature_obj as the active object.
    op_override(bpy.ops.pose.armature_apply, {"active_object": arm})

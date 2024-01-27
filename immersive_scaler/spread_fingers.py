import bpy
import importlib
import numpy as np

from . import common
from . import bones
from . import posemode

importlib.reload(common)
importlib.reload(bones)
importlib.reload(posemode)

from .common import (
    ArmatureOperator,
    get_body_meshes,
    get_armature,
    obj_in_scene,
    temp_ensure_enabled,
)
from .posemode import start_pose_mode_with_reset, apply_pose_to_rest
from .bones import get_bone


def point_bone(bone, point, spread_factor):
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

    newbm = bone.matrix.to_quaternion()

    # Run the actual rotation twice to give us more range on the
    # rotation. The slerp should exactly remove one of these by
    # default, basically letting us extrapolate a bit.
    newbm.rotate(rotation_quat_pose)
    newbm.rotate(rotation_quat_pose)

    newbm.rotate(bone.matrix.inverted())

    oldbm = bone.matrix.to_quaternion()
    oldbm.rotate(bone.matrix.inverted())

    finalbm = oldbm.slerp(newbm, spread_factor / 2)

    bone.rotation_quaternion = finalbm


def spread_fingers(spare_thumb, spread_factor):
    obj = get_armature()
    start_pose_mode_with_reset(obj)
    for hand in [get_bone("right_wrist", obj), get_bone("left_wrist", obj)]:
        for finger in hand.children:
            if "thumb" in finger.name.lower() and spare_thumb:
                continue
            point_bone(finger, hand.head, spread_factor)
    apply_pose_to_rest()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


class ArmatureSpreadFingers(ArmatureOperator):
    """Spreads the fingers on a humanoid avatar"""

    bl_idname = "armature.spreadfingers"
    bl_label = "Spread Fingers"
    bl_options = {"REGISTER", "UNDO"}

    # spare_thumb: bpy.types.Scene.spare_thumb
    # spread_factor: bpy.types.Scene.spread_factor

    def execute_main(self, context, arm, meshes):
        spread_fingers(self.spare_thumb, self.spread_factor)
        return {"FINISHED"}

    def invoke(self, context, event):
        s = context.scene
        self.spare_thumb = s.spare_thumb
        self.spread_factor = s.spread_factor

        return self.execute(context)


_register, _unregister = bpy.utils.register_classes_factory(
    [
        ArmatureSpreadFingers,
    ]
)


def ops_register():
    print("Registering Finger Spreading add-on")
    _register()


def ops_unregister():
    print("Attempting to Finger Spreading add-on")
    _unregister()


if __name__ == "__main__":
    _register()

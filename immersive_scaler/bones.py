import bpy
import importlib

from sys import intern

from . import common

importlib.reload(common)

from .common import get_armature

bone_names = {
    "right_shoulder": ["rightshoulder", "shoulderr", "rshoulder"],
    "right_arm": ["rightarm", "armr", "rarm", "upperarmr", "rightupperarm"],
    "right_elbow": [
        "rightelbow",
        "elbowr",
        "relbow",
        "lowerarmr",
        "rightlowerarm",
        "lowerarmr",
        "forearmr",
    ],
    "right_wrist": ["rightwrist", "wristr", "rwrist", "handr", "righthand"],
    "right_leg": [
        "rightleg",
        "legr",
        "rleg",
        "upperlegr",
        "thighr",
        "rightupperleg",
        "rupperleg",
    ],
    "right_knee": [
        "rightknee",
        "kneer",
        "rknee",
        "lowerlegr",
        "calfr",
        "rightlowerleg",
        "shinr",
    ],
    "right_ankle": [
        "rightankle",
        "ankler",
        "rankle",
        "rightfoot",
        "footr",
        "rightfoot",
    ],
    "right_eye": ["eyer", "righteye", "eyeright", "righteye001"],
    "left_shoulder": ["leftshoulder", "shoulderl", "lshoulder"],
    "left_arm": ["leftarm", "arml", "larm", "upperarml", "leftupperarm"],
    "left_elbow": [
        "leftelbow",
        "elbowl",
        "lelbow",
        "lowerarml",
        "leftlowerarm",
        "lowerarml",
        "forearml",
    ],
    "left_wrist": ["leftwrist", "wristl", "lwrist", "handl", "lefthand"],
    "left_leg": [
        "leftleg",
        "legl",
        "lleg",
        "upperlegl",
        "thighl",
        "leftupperleg",
        "lupperleg",
    ],
    "left_knee": [
        "leftknee",
        "kneel",
        "lknee",
        "lowerlegl",
        "calfl",
        "shinl",
        "leftlowerleg",
    ],
    "left_ankle": ["leftankle", "anklel", "lankle", "leftfoot", "footl", "leftfoot"],
    "left_eye": ["eyel", "lefteye", "eyeleft", "lefteye001"],
    "head": ["head"],
    "neck": ["neck"],
    "hips": ["hips", "hip", "pelvis", "root"],
    "spine": ["spine"],
    "chest": ["chest"],
    "upperchest": ["upperchest", "upper_chest"],
    "left_toes": ["toesl", "toel"],
    "right_toes": ["toesr", "toer"],
    "left_little_proximal": ["littleproximall", "leftpinkyproximal"],
    "left_ring_proximal": ["ringproximall", "leftringproximal"],
    "left_middle_proximal": ["middleproximall", "leftmiddleproximal"],
    "left_index_proximal": ["indexproximall", "leftindexproximal"],
    "left_thumb_proximal": ["thumbproximall", "leftthumbproximal"],
    "left_little_intermediate": ["littleintermediatel", "leftpinkyintermediate"],
    "left_ring_intermediate": ["ringintermediatel", "leftringintermediate"],
    "left_middle_intermediate": ["middleintermediatel", "leftmiddleintermediate"],
    "left_index_intermediate": ["indexintermediatel", "leftindexintermediate"],
    "left_thumb_intermediate": ["thumbintermediatel", "leftthumbintermediate"],
    "left_little_distal": ["littledistall", "leftpinkydistal"],
    "left_ring_distal": ["ringdistall", "leftringdistal"],
    "left_middle_distal": ["middledistall", "leftmiddledistal"],
    "left_index_distal": ["indexdistall", "leftindexdistal"],
    "left_thumb_distal": ["thumbdistall", "leftthumbdistal"],
    "right_little_proximal": ["littleproximalr", "rightpinkyproximal"],
    "right_ring_proximal": ["ringproximalr", "rightringproximal"],
    "right_middle_proximal": ["middleproximalr", "rightmiddleproximal"],
    "right_index_proximal": ["indexproximalr", "rightindexproximal"],
    "right_thumb_proximal": ["thumbproximalr", "rightthumbproximal"],
    "right_little_intermediate": ["littleintermediater", "rightpinkyintermediate"],
    "right_ring_intermediate": ["ringintermediater", "rightringintermediate"],
    "right_middle_intermediate": ["middleintermediater", "rightmiddleintermediate"],
    "right_index_intermediate": ["indexintermediater", "rightindexintermediate"],
    "right_thumb_intermediate": ["thumbintermediater", "rightthumbintermediate"],
    "right_little_distal": ["littledistalr", "rightpinkydistal"],
    "right_ring_distal": ["ringdistalr", "rightringdistal"],
    "right_middle_distal": ["middledistalr", "rightmiddledistal"],
    "right_index_distal": ["indexdistalr", "rightindexdistal"],
    "right_thumb_distal": ["thumbdistalr", "rightthumbdistal"],
}


def bone_lookup(name):
    # Now using overrides

    # Need to scan through every override and test if they reference
    # the bone in qeustion.
    for bone in bone_names:
        # Hopefully using the right context here. Is there a way you
        # could be using a different scene somehow?
        override = getattr(bpy.context.scene, "override_" + bone)
        if override == name:
            return bone

    lower_name = (
        name.lower().replace("_", "").replace("-", "").replace(" ", "").replace(".", "")
    )
    for token in bone_names:
        if lower_name in bone_names[token]:
            return token
    return None


def check_bone(name, arm):
    """To be used to check optional features that don't requrie a core bone to be present

    Returns True if the bone is present, otherwise False"""
    s = bpy.context.scene
    override = getattr(s, "override_" + name)
    if override != "_None" and name in arm.pose.bones:
        return True
    name_list = bone_names[name]
    bone_lookup = dict(
        [
            (bone.name.lower().translate(dict.fromkeys(map(ord, " _.-"))), bone)
            for bone in arm.pose.bones
        ]
    )
    for n in name_list:
        if n in bone_lookup:
            return True
    return False


def get_bone(name, arm):
    # First check that there's no override
    s = bpy.context.scene
    override = getattr(s, "override_" + name)
    if override != "_None":
        return arm.pose.bones[override]
    name_list = bone_names[name]
    bone_lookup = dict(
        [
            (bone.name.lower().translate(dict.fromkeys(map(ord, " _.-"))), bone)
            for bone in arm.pose.bones
        ]
    )
    for n in name_list:
        if n in bone_lookup:
            return bone_lookup[n]
    return arm.pose.bones[name]


class SearchMenuOperator_bone_selection(bpy.types.Operator):
    bl_description = "Select the bone for overriding"
    bl_idname = "scene.search_menu_bone_selection"
    bl_label = "Select Bone"
    bl_property = "my_enum"

    bone_name: bpy.props.StringProperty()

    def getbones(self, context):
        global _ENUM_CACHE
        choices = [("_None",) * 3]
        arm = get_armature()
        if arm is not None:
            # intern each string in the enum items to ensure Python has its own reference to it
            choices = choices + list((intern(b.name),) * 3 for b in arm.data.bones)
        # Storing the list of choices in bpy.types.Object.Enum doesn't seem to work properly for some reason, but we can
        # use our own cache fine
        _ENUM_CACHE = choices
        return choices

    my_enum: bpy.props.EnumProperty(
        name="Scaling Active Armature",
        description="Active Armature to scale",
        items=getbones,
    )

    def execute(self, context):
        setattr(context.scene, "override_" + self.bone_name, self.my_enum)
        # context.scene.imscale_scale_armature_barm = self.my_enum
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {"FINISHED"}


_register, _unregister = bpy.utils.register_classes_factory(
    [SearchMenuOperator_bone_selection]
)


def ops_register():
    print("Registering imscale bone selection")
    _register()


def ops_unregister():
    print("Deregistering imscale bone selection")
    _unregister()


if __name__ == "__main__":
    _register()

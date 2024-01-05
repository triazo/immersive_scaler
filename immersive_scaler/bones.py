import bpy

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
    "right_leg": ["rightleg", "legr", "rleg", "upperlegr", "thighr", "rightupperleg"],
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
    "left_leg": ["leftleg", "legl", "lleg", "upperlegl", "thighl", "leftupperleg"],
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
}


def get_bone(name, arm):
    # First check that there's no override
    s = bpy.context.scene
    override = getattr(s, "override_" + name)
    if override != "_None":
        return arm.pose.bones[override]
    name_list = bone_names[name]
    bone_lookup = dict(
        [
            (bone.name.lower().translate(dict.fromkeys(map(ord, " _."))), bone)
            for bone in arm.pose.bones
        ]
    )
    for n in name_list:
        if n in bone_lookup:
            return bone_lookup[n]
    return arm.pose.bones[name]

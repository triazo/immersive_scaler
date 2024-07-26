import bpy
from contextlib import contextmanager

from typing import Optional, Any, Set, Dict, List
from itertools import chain


def get_armature() -> Optional[bpy.types.Object]:
    context = bpy.context
    scene = context.scene
    # Get armature from Cats by default if Cats is loaded.
    # Cats stores its currently active armature in an 'armature' EnumProperty added to Scene objects
    # If Cats is loaded, this will always return a string, otherwise, the property won't (shouldn't) exist and None
    # will be returned.
    armature_name = getattr(scene, "armature", None)
    if armature_name:
        cats_armature = scene.objects.get(armature_name, None)
        if cats_armature and cats_armature.type == "ARMATURE":
            return cats_armature
        else:
            return None

    # Try to get the armature from the context, this is typically the active object
    obj = context.object
    if obj and obj.type == "ARMATURE":
        return obj

    # Try to the Object called "Armature"
    armature_name = "Armature"
    obj = scene.objects.get(armature_name, None)
    if obj and obj.type == "ARMATURE":
        return obj

    # Look through all armature objects, if there's only one, use that
    obj = None
    for o in scene.objects:
        if o.type == "ARMATURE":
            if obj is None:
                obj = o
            else:
                # There's more than one, we don't know which to use, so return None
                return None
    return obj


def get_all_armatures(self, context):
    return [
        (o.name, o.name, o.name)
        for o in context.view_layer.objects
        if o.type == "ARMATURE"
    ]


if bpy.app.version >= (3, 2):
    # Passing in context_override as a positional-only argument is deprecated as of Blender 3.2, replaced with
    # Context.temp_override
    def op_override(
        operator,
        context_override: dict[str, Any],
        context: Optional[bpy.types.Context] = None,
        execution_context: Optional[str] = None,
        undo: Optional[bool] = None,
        **operator_args
    ) -> set[str]:
        """Call an operator with a context override"""
        args = []
        if execution_context is not None:
            args.append(execution_context)
        if undo is not None:
            args.append(undo)

        if context is None:
            context = bpy.context
        with context.temp_override(**context_override):
            return operator(*args, **operator_args)

else:

    def op_override(
        operator,
        context_override: Dict[str, Any],
        context: Optional[bpy.types.Context] = None,
        execution_context: Optional[str] = None,
        undo: Optional[bool] = None,
        **operator_args
    ) -> Set[str]:
        """Call an operator with a context override"""
        if context is not None:
            context_base = context.copy()
            context_base.update(context_override)
            context_override = context_base
        args = [context_override]
        if execution_context is not None:
            args.append(execution_context)
        if undo is not None:
            args.append(undo)

        return operator(*args, **operator_args)


@contextmanager
def temp_ensure_enabled(*objs: bpy.types.Object):
    """Ensure that objs are enabled in the current scene by setting hide_viewport to False and adding then to the scene
    collection. Once done, clean up by restoring the hide_viewport value and removing objs from the scene collection if
    they were not already in the scene collection.
    It should be safe to delete or rename the objects and/or scene within the 'with' statement.
    """
    scene = bpy.context.scene

    # Remove any duplicates from the list of objects
    unique_objs = []
    found_objs = set()
    for obj in objs:
        if obj not in found_objs:
            unique_objs.append(obj)
            found_objs.add(obj)

    old_hide_viewports = [obj.hide_viewport for obj in unique_objs]

    added_to_collections = []
    try:
        objects = scene.collection.objects
        for obj in unique_objs:
            obj.hide_viewport = False
            if obj.name not in objects:
                objects.link(obj)
                added_to_collections.append(True)
            else:
                added_to_collections.append(False)
        yield
    finally:
        for obj, old_hide_viewport, added_to_collection in zip(
            unique_objs, old_hide_viewports, added_to_collections
        ):
            try:
                # While we could do `if old_hide_viewport: obj.hide_viewport = True`, this wouldn't always check that
                # obj is still a valid reference.
                obj.hide_viewport = old_hide_viewport

                if added_to_collection:
                    try:
                        objects = scene.collection.objects
                        if obj.name in objects:
                            objects.unlink(obj)
                    except ReferenceError:
                        # scene has been deleted
                        pass
            except ReferenceError:
                # obj has been deleted
                pass


def obj_in_scene(obj):
    for o in bpy.context.view_layer.objects:
        if o is obj:
            return True
    return False


def get_body_meshes(arm=None):
    if not arm:
        arm = get_armature()
    meshes = []
    for c in arm.children:
        if not obj_in_scene(c):
            continue
        if len(c.users_scene) == 0:
            continue
        if c.type == "MESH":
            meshes.append(c)
    return meshes


def child_constraints(objects: List[bpy.types.Object]):
    """Takes O(len(bpy.data.objects)) time, returns any objects that
    are childed to something in `objects`, along with the object or
    bone it is childed to"""
    constrained_objects = []
    for o in bpy.data.objects:
        if "Child Of" in o.constraints:
            constraint = o.constraints["Child Of"]

            if constraint.target in objects:
                target = constraint.target
                if constraint.subtarget == "":
                    constrained_objects.append((o, target))
                else:
                    # As far as I can tell the subtarget needs to be
                    # either a bone or vertex group which should both
                    # be valid
                    target_bone = target.pose.bones[constraint.subtarget]
                    constrained_objects.append((o, target_bone))
    return constrained_objects


def _children_recursive(obj: bpy.types.Object):
    """Takes O(len(bpy.data.objects)) time, just like Blender's implementation in 3.1+ (also in Python code, but can't
    just copy it due to it being GPLv2+)"""
    # Create dict from obj to its children
    obj_to_children = {}
    for o in bpy.data.objects:
        parent = o.parent
        if parent is not None:
            if parent in obj_to_children:
                obj_to_children[parent].append(o)
            else:
                obj_to_children[parent] = [o]
    children = []
    if obj in obj_to_children:
        # Iterate to find all the children instead of recursively calling a function
        children_iter = iter(obj_to_children[obj])
        try:
            while True:
                # Get next child and append it to the list we'll return
                # Once the iterator is exhausted, StopIteration will be raised
                child = next(children_iter)
                children.append(child)
                if child in obj_to_children:
                    # 'append' the children of the current child to the iterator by chaining the two together
                    children_iter = chain(children_iter, obj_to_children[child])
        except StopIteration:
            # Iteration is done
            pass
    return children


def children_recursive(obj: bpy.types.Object) -> List[bpy.types.Object]:
    # children_recursive seems to have been added in Blender 3.1, it has the same performance cost as Object.children
    # because they both have to iterate through every Object.
    if hasattr(bpy.types.Object, "children_recursive"):
        return obj.children_recursive
    else:
        return _children_recursive(obj)


class ArmatureOperator(bpy.types.Operator):
    # poll_message_set was added in 3.0
    if not hasattr(bpy.types.Operator, "poll_message_set"):

        @classmethod
        def poll_message_set(cls, message, *args):
            pass

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if get_armature() is None:
            cls.poll_message_set(
                "Armature not found. Select an armature as active or ensure an armature is set in Cats"
                " if you have Cats installed."
            )
            return False
        return True

    def execute_main(
        self,
        context: bpy.types.Context,
        arm: bpy.types.Object,
        meshes: List[bpy.types.Object],
    ):
        # To be overridden in subclasses
        return {"FINISHED"}

    def execute(self, context: bpy.types.Context):
        arm = get_armature()
        meshes = get_body_meshes()

        if context.mode != "OBJECT":
            # Make sure we leave any EDIT modes so that data from edit modes is up-to-date.
            bpy.ops.object.mode_set(mode="OBJECT")

        with temp_ensure_enabled(arm, *meshes):
            return self.execute_main(context, arm, meshes)

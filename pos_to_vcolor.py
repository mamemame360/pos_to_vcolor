bl_info = {
    "name": "",
    "author": "Daisuke Mizuma",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "View3D > ToolBar",
    "": "",
    "description": "",
    "category": "Mesh"
}


import re
import bpy
import bmesh
from mathutils import Vector


class SetVertexColorError(Exception):
    def __init__(self, message):
        self.message = message


def _get_bounds_from_object(obj):
    """get world Aabb from object"""
    if obj is None:
        return (Vector((-1, -1, -1)), Vector((1, 1, 1)))
    bmin = list(obj.matrix_world @ Vector(obj.bound_box[0]))
    bmax = list(bmin)
    for p in obj.bound_box:
        p = obj.matrix_world @ Vector(p)
        bmin[0] = min(bmin[0], p[0])
        bmin[1] = min(bmin[1], p[1])
        bmin[2] = min(bmin[2], p[2])
        bmax[0] = max(bmax[0], p[0])
        bmax[1] = max(bmax[1], p[1])
        bmax[2] = max(bmax[2], p[2])
    return (Vector(bmin), Vector(bmax))


def _normalize_bounds(value, normalize_by_bounds, bounds, axis):
    """helper for _get_value"""
    if not normalize_by_bounds:
        return value
    bmin = bounds[0][axis]
    bmax = bounds[1][axis]
    return (value - bmin) / (bmax - bmin)


def _get_axis_index(name):
    element = {
        'X': 0,
        'Y': 1,
        'Z': 2,
        'U': 0,
        'V': 1,
        'R': 0,
        'G': 1,
        'B': 2}
    key = name[-1:]
    return element[key]


def _extract_layer_name(enum_name, prefix):
    return enum_name[len(prefix):-2]


def _get_uv_value(mesh, enum_name, loop):
    layer_name = _extract_layer_name(enum_name, 'UVMAP.')
    index = _get_axis_index(enum_name)
    layer = mesh.loops.layers.uv[layer_name]
    return loop[layer].uv[index]


def _set_uv_value(mesh, enum_name, loop, value, flip_vertical):
    layer_name = _extract_layer_name(enum_name, 'UVMAP.')
    index = _get_axis_index(enum_name)
    layer = mesh.loops.layers.uv[layer_name]
    if index == 1 and flip_vertical:
        value = 1.0 - value
    loop[layer].uv[index] = value


def _get_vcolor_value(mesh, enum_name, loop):
    layer_name = _extract_layer_name(enum_name, 'VCOLOR.')
    index = _get_axis_index(enum_name)
    layer = mesh.loops.layers.color[layer_name]
    return loop[layer][index]


def _set_vcolor_value(mesh, enum_name, loop, value):
    layer_name = _extract_layer_name(enum_name, 'VCOLOR.')
    index = _get_axis_index(enum_name)
    layer = mesh.loops.layers.color[layer_name]
    loop[layer][index] = value


class ActionExecuter:
    def __init__(self, bounds):
        self.context = None
        self.obj = None
        self.mesh = None
        self.cursor_pos = None
        self.bounds = bounds

    def get_action_source(self, loop, action):
        if action.source_name.startswith('VERTEX.'):
            vpos = self.obj.matrix_world @ loop.vert.co
            index = _get_axis_index(action.source_name)
            return _normalize_bounds(vpos[index], action.normalize_by_bounds, self.bounds, index)
        elif action.source_name.startswith('CURSOR.'):
            index = _get_axis_index(action.source_name)
            return _normalize_bounds(self.cursor_pos[index], action.normalize_by_bounds, self.bounds, index)
        elif action.source_name.startswith('UVMAP.'):
            return _get_uv_value(self.mesh, action.source_name, loop)
        elif action.source_name.startswith('VCOLOR'):
            return _get_vcolor_value(self.mesh, action.source_name, loop)
        elif action.source_name == 'CONSTANT':
            return action.constant
        else:
            return 0.0

    def set_action_target(self, loop, action, value):
        if action.target_name.startswith('UVMAP.'):
            _set_uv_value(self.mesh, action.target_name, loop, value, action.flip_vertical)
        elif action.target_name.startswith('VCOLOR.'):
            _set_vcolor_value(self.mesh, action.target_name, loop, value)
        elif action.target_name == 'CONSOLE':
            print('%s(%d) = %f' % (action.source_name, loop.index, value))

    def proc_actions(self, loop, actions):
        for action in actions:
            if action.source_name != 'KEEP':
                value = self.get_action_source(loop, action)
                self.set_action_target(loop, action, value)

    def execute(self, context, obj, actions):
        self.context = context
        self.obj = obj
        self.mesh = bmesh.from_edit_mesh(obj.data)
        self.cursor_pos = context.scene.cursor_location
        for face in self.mesh.faces:
            for loop in face.loops:
                if loop.vert.select:
                    self.proc_actions(loop, actions)
        bmesh.update_edit_mesh(self.obj.data)
        self.context = None
        self.obj = None
        self.mesh = None
        

def _get_layername_from_index(obj, target_name, index):
    if target_name.startswith('UVMAP'):
        if len(obj.data.uv_layers) > 0:
            return obj.data.uv_layers[index].name
    elif target_name.startswith('VCOLOR'):
        if len(obj.data.vertex_colors) > 0:
            return obj.data.vertex_colors[index].name
    return ""


_source_template = [
    ('KEEP', 'Keep', "keep current value"),
    ('CONSTANT', 'Constant Value', "set specified constant value"),
    ('VERTEX.X', 'Vertex Pos X', "set vertex position X"),
    ('VERTEX.Y', 'Vertex Pos Y', "set vertex position Y"),
    ('VERTEX.Z', 'Vertex Pos Z', "set vertex position Z"),
    ('CURSOR.X', 'Cursor Pos X', "set 3D cursor X"),
    ('CURSOR.Y', 'Cursor Pos Y', "set 3D cursor Y"),
    ('CURSOR.Z', 'Cursor Pos Z', "set 3D cursor Z")
]


def _source_enumrate_callback(scene, context):
    items = []
    for item in _source_template:
        items.append(item)
    obj = context.edit_object
    if obj is not None:
        for uv in obj.data.uv_layers:
            items.append(('UVMAP.' + uv.name + '.U', uv.name + '.U', ""))
            items.append(('UVMAP.' + uv.name + '.V', uv.name + '.V', ""))
        for vcolor in obj.data.vertex_colors:
            items.append(('VCOLOR.' + vcolor.name + '.R', vcolor.name + '.R', ""))
            items.append(('VCOLOR.' + vcolor.name + '.G', vcolor.name + '.G', ""))
            items.append(('VCOLOR.' + vcolor.name + '.B', vcolor.name + '.B', ""))
    return items
    

def _target_enumrate_callback(scene, context):
    items = []
    obj = context.edit_object
    if obj is not None:
        for uv in obj.data.uv_layers:
            items.append(('UVMAP.' + uv.name + '.U', uv.name + '.U', ""))
            items.append(('UVMAP.' + uv.name + '.V', uv.name + '.V', ""))
        for vcolor in obj.data.vertex_colors:
            items.append(('VCOLOR.' + vcolor.name + '.R', vcolor.name + '.R', ""))
            items.append(('VCOLOR.' + vcolor.name + '.G', vcolor.name + '.G', ""))
            items.append(('VCOLOR.' + vcolor.name + '.B', vcolor.name + '.B', ""))
    items.append(('CONSOLE', 'Console', "output value to console"))
    return items


def _is_position_source(source_name):
    return source_name.startswith('VERTEX') or source_name.startswith('CURSOR')


def _is_uvmap_v(name):
    return name.startswith('UVMAP.') and name.endswith('.V')


class PosToVColorActionProps(bpy.types.PropertyGroup):
    source_name: bpy.props.EnumProperty(items=_source_enumrate_callback, name="Source")
    constant: bpy.props.FloatProperty(name="Constant", default=0.0)
    normalize_by_bounds: bpy.props.BoolProperty(name="Normalize by Bounds", default=False)
    target_name: bpy.props.EnumProperty(items=_target_enumrate_callback, name="Target")
    flip_vertical: bpy.props.BoolProperty(name="Flip vertical", default=True, description="flip vertical(store 1-a to V)")


class PosToVColorToolProps(bpy.types.PropertyGroup):
    """
    Fake module like class
    bpy.context.window_manager.vertexcolortools
    """
    actions: bpy.props.CollectionProperty(type=PosToVColorActionProps)
    bounds_from_object: bpy.props.BoolProperty(name="Bounds from Object", default=False)
    bounds_object: bpy.props.PointerProperty(type=bpy.types.Object, name="Bounds Object")
    bounds_min: bpy.props.FloatVectorProperty(name="Bounds Min", default=(-1,-1,-1), unit='LENGTH')
    bounds_max: bpy.props.FloatVectorProperty(name="Bounds Max", default=(1,1,1), unit='LENGTH')


class POS_TO_VCOLOR_OT_PosToVColor(bpy.types.Operator):
    """Apply PosToVColor"""
    bl_idname = 'pos_to_vcolor.apply'
    bl_label = 'Apply'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.edit_object
    
    def execute(self, context):
        obj = context.edit_object
        tool = bpy.context.window_manager.vertexcolortools
        bounds = None
        if tool.bounds_from_object:
            bounds = _get_bounds_from_object(tool.bounds_object)
        else:
            bounds = (tool.bounds_min, tool.bounds_max)
        try:
            action_exec = ActionExecuter(bounds)
            action_exec.execute(context, obj, tool.actions)
        except SetVertexColorError as e:
            self.report({'ERROR'}, e.message)
            return {'CANCELLED'}
        return {'FINISHED'}


class POS_TO_VCOLOR_OT_AddActionOperator(bpy.types.Operator):
    """Add Action"""
    bl_idname = 'pos_to_vcolor.add_action'
    bl_label = 'Add Action'

    item_id: bpy.props.IntProperty(name="Item id")

    def execute(self, context):
        tool = bpy.context.window_manager.vertexcolortools
        item = tool.actions.add()
        return {'FINISHED'}


class POS_TO_VCOLOR_OT_RemoveActionOperator(bpy.types.Operator):
    """Remove Action"""
    bl_idname = 'pos_to_vcolor.remove_action'
    bl_label = 'Remove Action'

    item_id: bpy.props.IntProperty(name="Item id")

    def execute(self, context):
        tool = bpy.context.window_manager.vertexcolortools
        tool.actions.remove(self.item_id)
        return {'FINISHED'}


class VIEW3D_PT_PosToVColorTool(bpy.types.Panel):
    bl_label = 'PosToVColor'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tools'
    bl_context = 'mesh_edit'
    
    @classmethod
    def poll(cls, context):
        return context.edit_object
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = True
        obj = context.edit_object
        tool = bpy.context.window_manager.vertexcolortools
        prop = layout.operator('pos_to_vcolor.add_action')
        prop.item_id = len(tool.actions)
        for idx in range(0, len(tool.actions)):
            item = tool.actions[idx]
            box = layout.box()
            row = box.row()
            prop = row.operator('pos_to_vcolor.remove_action', icon='X', text='')
            prop.item_id = idx
            box = row.box()
            col = box.column()
            col.prop(item, 'source_name', text='Source')
            if item.source_name == 'CONSTANT':
                col.prop(item, 'constant')
            if _is_position_source(item.source_name):
                col.prop(item, 'normalize_by_bounds')
            col.prop(item, 'target_name', text='Target')
            if _is_uvmap_v(item.target_name):
                col.prop(item, 'flip_vertical')
        layout.separator()
        col = layout.column()
        col.prop(tool, 'bounds_from_object')
        col2 = col.column()
        col2.enabled = tool.bounds_from_object
        col2.prop(tool, 'bounds_object')

        col2 = col.column()
        if tool.bounds_from_object:
            col2.enabled = False
            (bmin, bmax) = _get_bounds_from_object(tool.bounds_object)
            tool.bounds_min = bmin
            tool.bounds_max = bmax
            col2.prop(tool, "bounds_min", text="Min")
            col2.prop(tool, "bounds_max", text="Max")
        else:
            col2.enabled = True
            col2.prop(tool, "bounds_min", text="Min")
            col2.prop(tool, "bounds_max", text="Max")
        col = layout.column()
        col.prop(bpy.context.scene, 'cursor_location')
        layout.operator('pos_to_vcolor.apply')

 
classes = (
    PosToVColorActionProps,
    PosToVColorToolProps,
    POS_TO_VCOLOR_OT_AddActionOperator,
    POS_TO_VCOLOR_OT_RemoveActionOperator,
    POS_TO_VCOLOR_OT_PosToVColor,
    VIEW3D_PT_PosToVColorTool,
    )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.vertexcolortools = bpy.props.PointerProperty(type=PosToVColorToolProps)
    

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        

try:
    del bpy.types.WindowManager.vertexcolortools
except Exception:
    pass


if __name__ == '__main__':        
    register()

bl_info = {
    "name": "PosToVColor",
    "author": "Daisuke Mizuma",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > ToolBar",
    "": "",
    "description": "Copy vertex position or cursor position to vertex color or uvmap"
                   "(For tricky shader technique)",
    "category": "Mesh"
}


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


def _normalize_bounds(value, bounds, axis):
    """helper for _get_value"""
    if bounds is None:
        return value
    bmin = bounds[0][axis]
    bmax = bounds[1][axis]
    return (value - bmin) / (bmax - bmin)


def _get_value(context, origin, vpos, vcolor, uv, data_source, bounds, constant):
    """helper for set_vertex_color"""
    if data_source == 'VERTEX_X':
        return _normalize_bounds(vpos.x, bounds, 0)
    elif data_source == 'VERTEX_Y':
        return _normalize_bounds(vpos.y, bounds, 1)
    elif data_source == 'VERTEX_Z':
        return _normalize_bounds(vpos.z, bounds, 2)
    elif data_source == 'CURSOR_X':
        return _normalize_bounds(context.scene.cursor_location.x, bounds, 0)
    elif data_source == 'CURSOR_Y':
        return _normalize_bounds(context.scene.cursor_location.y, bounds, 1)
    elif data_source == 'CURSOR_Z':
        return _normalize_bounds(context.scene.cursor_location.z, bounds, 2)
    elif data_source == 'VCOLOR_R':
        return vcolor[0]
    elif data_source == 'VCOLOR_G':
        return vcolor[1]
    elif data_source == 'VCOLOR_B':
        return vcolor[2]
    elif data_source == 'UVMAP_U':
        return uv[0]
    elif data_source == 'UVMAP_V':
        return uv[1]
    elif data_source == 'CONSTANT':
        return constant
    elif data_source == 'KEEP':
        return origin


def _check_data_sources(data_sources, prefix, count):
    """helper for set_vertex_color"""
    for i in range(0, count):
        if data_sources[i].startswith(prefix):
            return True
    return False


def set_vertex_color(context, obj, target, data_sources, bounds, constant, oneminus_v):
    """execute vertex value edit"""
    # get active vcolor
    vcol = obj.data.vertex_colors.active
    if vcol is None:
        if _check_data_sources(data_sources, 'VCOLOR', 3):
            raise SetVertexColorError('cannot found active vertex color')
        if target == 'VCOLOR':
            print('create new vertex color')
            vcol = obj.data.vertex_colors.new()
    # get active uvmap
    uvmap = obj.data.uv_layers.active
    if uvmap is None:
        if _check_data_sources(data_sources, 'UVMAP', 2):
            raise SetVertexColorError('cannot found active uvmap')
        if target == 'UVMAP':
            print('create new uvmap')
            uvmap = obj.data.uv_layers.new()
    # bmesh
    mesh = bmesh.from_edit_mesh(obj.data)
    vcol_layer = None if vcol is None else mesh.loops.layers.color[vcol.name]
    uv_layer = None if uvmap is None else mesh.loops.layers.uv[uvmap.name]
    # apply to selected loops
    for face in mesh.faces:
        for loop in face.loops:
            if loop.vert.select:
                vpos = obj.matrix_world @ loop.vert.co
                vcolor = (0, 0, 0) if vcol_layer is None else loop[vcol_layer]
                uv = (0, 0) if uv_layer is None else loop[uv_layer].uv
                if target == 'UVMAP':
                    loop[uv_layer].uv[0] = _get_value(context, loop[uv_layer].uv[0], vpos, vcolor, uv, data_sources[0], bounds, constant[0])
                    loop[uv_layer].uv[1] = _get_value(context, loop[uv_layer].uv[1], vpos, vcolor, uv, data_sources[1], bounds, constant[1])
                    if oneminus_v and data_sources[1] != 'KEEP':
                        loop[uv_layer].uv[1] = 1.0 - loop[uv_layer].uv[1]
                elif target == 'VCOLOR':
                    loop[vcol_layer][0] = _get_value(context, loop[vcol_layer][0], vpos, vcolor, uv, data_sources[0], bounds, constant[0])
                    loop[vcol_layer][1] = _get_value(context, loop[vcol_layer][1], vpos, vcolor, uv, data_sources[1], bounds, constant[1])
                    loop[vcol_layer][2] = _get_value(context, loop[vcol_layer][2], vpos, vcolor, uv, data_sources[2], bounds, constant[2])
    bmesh.update_edit_mesh(obj.data)


ENUM_TARGET = {
    ('UVMAP', 'UV Map', 'store data to UV Map'),
    ('VCOLOR', 'Vertex Color', 'store data to Vertex Color')
}

ENUM_DATA_SOURCE = [
    ('VERTEX_X', 'Vertex Pos X', "set vertex position X"),
    ('VERTEX_Y', 'Vertex Pos Y', "set vertex position Y"),
    ('VERTEX_Z', 'Vertex Pos Z', "set vertex position Z"),
    ('CURSOR_X', 'Cursor Pos X', "set 3D cursor X"),
    ('CURSOR_Y', 'Cursor Pos Y', "set 3D cursor Y"),
    ('CURSOR_Z', 'Cursor Pos Z', "set 3D cursor Z"),
    ('VCOLOR_R', 'Vertex Color R', "set current vertex color R"),
    ('VCOLOR_G', 'Vertex Color G', "set current vertex color G"),
    ('VCOLOR_B', 'Vertex Color B', "set current vertex color B"),
    ('UVMAP_U', 'UVMap U', "set current vertex uv U"),
    ('UVMAP_V', 'UVMap V', "set current vertex uv V"),
    ('CONSTANT', 'Constant Value', "set specified constant value"),
    ('KEEP', 'Keep', "keep current value")
]


class PosToVColorToolProps(bpy.types.PropertyGroup):
    """
    Fake module like class
    bpy.context.window_manager.vertexcolortools
    """
    target_layer: bpy.props.EnumProperty(items=ENUM_TARGET, name="Target", default='UVMAP')
    r_data_source: bpy.props.EnumProperty(items=ENUM_DATA_SOURCE, name="R", default="KEEP")
    g_data_source: bpy.props.EnumProperty(items=ENUM_DATA_SOURCE, name="G", default="KEEP")
    b_data_source: bpy.props.EnumProperty(items=ENUM_DATA_SOURCE, name="B", default="KEEP")
    constant: bpy.props.FloatVectorProperty(size=3, default=(0,0,0), name="constant")
    oneminus_v: bpy.props.BoolProperty(name="Flip vertical", default=True, description="flip vertical(store 1-a to V)")
    normalize_by_bounds: bpy.props.BoolProperty(name="Normalize by Bounds", default=False)
    bounds_from_object: bpy.props.BoolProperty(name="Bounds from Object", default=False)
    bounds_object: bpy.props.PointerProperty(type=bpy.types.Object, name="Bounds Object")
    bounds_min: bpy.props.FloatVectorProperty(name="Bounds Min", default=(-1,-1,-1), unit='LENGTH')
    bounds_max: bpy.props.FloatVectorProperty(name="Bounds Max", default=(1,1,1), unit='LENGTH')


class OBJECT_OT_PosToVColor(bpy.types.Operator):
    """Operator for PosToVColor"""
    bl_idname = 'object.pos_to_vcolor'
    bl_label = 'PosToVColor'
    bl_options = {'REGISTER', 'UNDO'}
    
    target_layer: bpy.props.EnumProperty(items=ENUM_TARGET, name="Target", default='UVMAP')
    r_data_source: bpy.props.EnumProperty(items=ENUM_DATA_SOURCE, name="R", default="KEEP")
    g_data_source: bpy.props.EnumProperty(items=ENUM_DATA_SOURCE, name="G", default="KEEP")
    b_data_source: bpy.props.EnumProperty(items=ENUM_DATA_SOURCE, name="B", default="KEEP")
    constant: bpy.props.FloatVectorProperty(size=3, default=(0,0,0), name="constant")
    oneminus_v: bpy.props.BoolProperty(name="Flip vertical", default=True)
    normalize_by_bounds: bpy.props.BoolProperty(name="Normalize by Bounds", default=False)
    bounds_min: bpy.props.FloatVectorProperty(name="Bounds Min", default=(-1,-1,-1), unit='LENGTH')
    bounds_max: bpy.props.FloatVectorProperty(name="Bounds Max", default=(1,1,1), unit='LENGTH')

    @classmethod
    def poll(cls, context):
        return context.edit_object
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'target_layer')
        if self.target_layer == 'UVMAP':
            layout.prop(self, 'r_data_source', text="U")
            layout.prop(self, 'g_data_source', text="V")
            layout.prop(self, 'oneminus_v')
        else:
            layout.prop(self, 'r_data_source')
            layout.prop(self, 'g_data_source')
            layout.prop(self, 'b_data_source')
        layout.prop(self, 'constant')
        layout.prop(self, 'normalize_by_bounds')
        col = layout.column()
        col.enabled = self.normalize_by_bounds
        col.prop(self, 'bounds_min')
        col.prop(self, 'bounds_max')

    def execute(self, context):
        obj = context.edit_object
        data_sources = (
            self.r_data_source,
            self.g_data_source,
            self.b_data_source
            )
        bounds = (self.bounds_min, self.bounds_max) if self.normalize_by_bounds else None
        try:
            set_vertex_color(context, obj, self.target_layer, data_sources, bounds, self.constant, self.oneminus_v)
        except SetVertexColorError as e:
            self.report({'ERROR'}, e.message)
            return {'CANCELLED'}
        return {'FINISHED'}
    
    def invoke(self, context, event):
        tool = bpy.context.window_manager.vertexcolortools
        self.target_layer = tool.target_layer
        self.r_data_source = tool.r_data_source
        self.g_data_source = tool.g_data_source
        self.b_data_source = tool.b_data_source
        self.constant = tool.constant
        self.oneminus_v = tool.oneminus_v
        self.bounds_min = tool.bounds_min
        self.bounds_max = tool.bounds_max
        self.normalize_by_bounds = tool.normalize_by_bounds
        if tool.bounds_from_object:
            (bmin, bmax) = _get_bounds_from_object(tool.bounds_object)
            self.bounds_min = bmin
            self.bounds_max = bmax
        else:
            self.bounds_min = tool.bounds_min
            self.bounds_max = tool.bounds_max
        return self.execute(context)


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
        tool = bpy.context.window_manager.vertexcolortools
        layout.prop(tool, "target_layer")
        if tool.target_layer == 'UVMAP':
            layout.prop(tool, "r_data_source", text="U")
            layout.prop(tool, "g_data_source", text="V")
            layout.prop(tool, "oneminus_v")
        else:
            layout.prop(tool, "r_data_source", text='R')
            layout.prop(tool, "g_data_source", text='G')
            layout.prop(tool, "b_data_source", text='B')
        col = layout.column()
        col.prop(tool, "constant")
        layout.prop(tool, "normalize_by_bounds")
        if tool.normalize_by_bounds:
            col = layout.column()
            col.enabled = tool.normalize_by_bounds
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
        layout.operator('object.pos_to_vcolor', text_ctxt="Execute")

 
classes = (
    OBJECT_OT_PosToVColor,
    VIEW3D_PT_PosToVColorTool,
    PosToVColorToolProps
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

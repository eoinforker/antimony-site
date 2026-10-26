# Node and mesh helpers, adapted from render-platform/platform_scene.py (technical reference only).
import bpy, numpy as np
SC = None
class S:
    """A float socket; arithmetic makes Math nodes."""
    def __init__(s, g, k): s.g, s.k = g, k
    def __add__(s, o): return s.g.m('ADD', s, o)
    def __radd__(s, o): return s.g.m('ADD', o, s)
    def __sub__(s, o): return s.g.m('SUBTRACT', s, o)
    def __rsub__(s, o): return s.g.m('SUBTRACT', o, s)
    def __mul__(s, o): return s.g.m('MULTIPLY', s, o)
    def __rmul__(s, o): return s.g.m('MULTIPLY', o, s)
    def __truediv__(s, o): return s.g.m('DIVIDE', s, o)
    def __rtruediv__(s, o): return s.g.m('DIVIDE', o, s)
    def __neg__(s): return s.g.m('MULTIPLY', s, -1.0)

class V:
    """A vector or colour socket."""
    def __init__(s, g, k): s.g, s.k = g, k

class G:
    def __init__(s, nt): s.nt = nt
    def new(s, t, **kw):
        n = s.nt.nodes.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def put(s, inp, val):
        if isinstance(val, (S, V)): s.nt.links.new(val.k, inp)
        elif isinstance(val, bpy.types.NodeSocket): s.nt.links.new(val, inp)
        elif isinstance(val, (tuple, list)):
            dv = inp.default_value
            val = tuple(val) + (1.0,) * (len(dv) - len(val))
            inp.default_value = val[:len(dv)]
        else: inp.default_value = val
    def m(s, op, a, b=None, c=None, clamp=False):
        n = s.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b, c)):
            if x is not None: s.put(n.inputs[i], x)
        return S(s, n.outputs[0])
    def floor(s, x): return s.m('FLOOR', x)
    def fract(s, x): return s.m('FRACT', x)
    def abs(s, x): return s.m('ABSOLUTE', x)
    def min(s, a, b): return s.m('MINIMUM', a, b)
    def max(s, a, b): return s.m('MAXIMUM', a, b)
    def sin(s, x): return s.m('SINE', x)
    def cos(s, x): return s.m('COSINE', x)
    def exp(s, x): return s.m('EXPONENT', x)
    def pow(s, a, b): return s.m('POWER', a, b)
    def clamp(s, x): return s.m('ADD', x, 0.0, clamp=True)
    def sm(s, e0, e1, x):
        n = s.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        s.put(n.inputs[0], x); s.put(n.inputs[1], e0); s.put(n.inputs[2], e1)
        s.put(n.inputs[3], 0.0); s.put(n.inputs[4], 1.0)
        return S(s, n.outputs[0])
    def lin(s, e0, e1, x):
        n = s.new('ShaderNodeMapRange', interpolation_type='LINEAR', clamp=True)
        s.put(n.inputs[0], x); s.put(n.inputs[1], e0); s.put(n.inputs[2], e1)
        s.put(n.inputs[3], 0.0); s.put(n.inputs[4], 1.0)
        return S(s, n.outputs[0])
    def band(s, a, b, x, soft=0.002): return s.sm(a - soft, a, x) * (1.0 - s.sm(b, b + soft, x))
    def comb(s, x, y, z):
        n = s.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)): s.put(n.inputs[i], v)
        return V(s, n.outputs[0])
    def sep(s, v):
        n = s.new('ShaderNodeSeparateXYZ'); s.put(n.inputs[0], v)
        return S(s, n.outputs[0]), S(s, n.outputs[1]), S(s, n.outputs[2])
    def vm(s, op, a, b=None, sc=None):
        n = s.new('ShaderNodeVectorMath', operation=op)
        s.put(n.inputs[0], a)
        if b is not None: s.put(n.inputs[1], b)
        if sc is not None: s.put(n.inputs[3], sc)
        o = n.outputs[1] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs[0]
        return (S if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else V)(s, o)
    def scale(s, v, f): return s.vm('SCALE', v, sc=f)
    def mix(s, a, b, f):
        n = s.new('ShaderNodeMix', data_type='RGBA')
        s.put(n.inputs[0], f); s.put(n.inputs[6], a); s.put(n.inputs[7], b)
        return V(s, n.outputs[2])
    def noise(s, vec, scale=1.0, detail=2.0, rough=0.5, w=None, dist=0.0):
        n = s.new('ShaderNodeTexNoise', noise_dimensions='4D' if w is not None else '3D')
        s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        s.put(n.inputs['Detail'], detail); s.put(n.inputs['Roughness'], rough)
        s.put(n.inputs['Distortion'], dist)
        if w is not None: s.put(n.inputs['W'], w)
        return S(s, n.outputs['Fac']), V(s, n.outputs['Color'])
    def white(s, vec):
        n = s.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D'); s.put(n.inputs['Vector'], vec)
        return S(s, n.outputs['Value']), V(s, n.outputs['Color'])
    def voronoi(s, vec, scale=1.0, feature='F1'):
        n = s.new('ShaderNodeTexVoronoi', feature=feature); s.put(n.inputs['Vector'], vec); s.put(n.inputs['Scale'], scale)
        return S(s, n.outputs['Distance']), V(s, n.outputs['Color'])
    def pos(s):
        n = s.new('ShaderNodeNewGeometry'); return V(s, n.outputs['Position']), V(s, n.outputs['Normal'])
    def uv(s):
        n = s.new('ShaderNodeTexCoord'); return V(s, n.outputs['UV'])
    def attr(s, name):
        n = s.new('ShaderNodeAttribute', attribute_name=name); return V(s, n.outputs['Color']), S(s, n.outputs['Fac'])
    def bump(s, h, strength=1.0, dist=1.0):
        n = s.new('ShaderNodeBump'); s.put(n.inputs['Strength'], strength); s.put(n.inputs['Distance'], dist); s.put(n.inputs['Height'], h)
        return V(s, n.outputs['Normal'])
    def principled(s, **kw):
        n = s.new('ShaderNodeBsdfPrincipled')
        for k, v in kw.items(): s.put(n.inputs[k.replace('_', ' ')], v)
        return n.outputs[0]
    def out(s, shader, volume=None):
        o = s.new('ShaderNodeOutputMaterial')
        if shader is not None: s.nt.links.new(shader, o.inputs['Surface'])
        if volume is not None: s.nt.links.new(volume, o.inputs['Volume'])
        return o

def material(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, G(m.node_tree)

# a scene-wide clock for the loop: 0 at frame 1, 1 at frame 73
class MB:
    def __init__(s): s.v, s.f, s.mi, s.uv, s.col = [], [], [], [], []
    def add(s, verts, faces, mat=0, uvs=None, col=None):
        o = len(s.v); s.v.extend(verts)
        for f in faces: s.f.append([i + o for i in f]); s.mi.append(mat)
        s.uv.extend(uvs if uvs is not None else [(0.0, 0.0)] * len(verts))
        s.col.extend([col or (1, 1, 1, 1)] * len(verts) if not (col and isinstance(col[0], (tuple, list))) else col)
    def box(s, x0, x1, y0, y1, z0, z1, mat=0):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        s.add(v, f, mat)
    def build(s, name, mats, smooth=False, uv=False, col=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(s.v, [], s.f)
        if uv:
            lay = me.uv_layers.new(name='UVMap'); vi = np.zeros(len(me.loops), dtype=np.int32)
            me.loops.foreach_get('vertex_index', vi)
            lay.data.foreach_set('uv', np.asarray(s.uv, dtype=np.float32)[vi].ravel())
        if col:
            a = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT')
            a.data.foreach_set('color', np.asarray(s.col, dtype=np.float32).ravel())
        me.polygons.foreach_set('material_index', np.asarray(s.mi, dtype=np.int32))
        me.polygons.foreach_set('use_smooth', np.full(len(s.f), smooth))
        me.update()
        for m in mats: me.materials.append(m)
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        return ob


"""제주도 탄생 애니메이션 (Blender 5.x, Cycles)

사용법 (프로젝트 폴더 C:\\vibe\\DAY4 에서):
  빌드     : blender -b -P jeju_birth.py -- build
  테스트   : blender -b jeju_birth.blend -P jeju_birth.py -- test 60 170 260 360
  렌더     : blender -b jeju_birth.blend -P jeju_birth.py -- gpu -s 1 -e 360 -a
  mp4 인코딩: blender -b -P jeju_birth.py -- encode
"""
import bpy, sys, os, gzip, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
HGT = os.path.join(HERE, "dem_dl", "N33E126.hgt.gz")
BLEND = os.path.join(HERE, "jeju_birth.blend")
FRAMES = os.path.join(HERE, "frames")
FPS, F_END = 24, 360
EX = 2.5          # 수직 과장 (1 Blender 단위 = 1 km)
BASE = -1.4       # 분화 전 해저 깊이(km)
DS = 2            # DEM 다운샘플 (30m x 2)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode = argv[0] if argv else "build"


# ---------------------------------------------------------------- GPU
def setup_gpu(sc=None):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for t in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type == t
                ok |= d.use
            if ok:
                break
        except Exception as e:
            print("gpu fail", t, e)
    (sc or bpy.context.scene).cycles.device = "GPU"
    print("devices:", [(d.name, d.type, d.use) for d in prefs.devices])


# ---------------------------------------------------------------- DEM
def load_dem():
    raw = gzip.open(HGT).read()
    a = np.frombuffer(raw, ">i2").reshape(3601, 3601).astype(np.float32)
    r0, r1 = int((34 - 33.60) * 3600), int((34 - 33.08) * 3600)
    c0, c1 = int(0.10 * 3600), int(1.00 * 3600)
    a = a[r0:r1, c0:c1]
    a[a < -1000] = 0
    h, w = (a.shape[0] // DS) * DS, (a.shape[1] // DS) * DS
    a = a[:h, :w].reshape(h // DS, DS, w // DS, DS).mean(axis=(1, 3))
    a[a < 3.0] = 0.0                      # 바다/잡음 제거
    lat = 33.60 - (np.arange(a.shape[0]) + 0.5) * DS / 3600.0
    lon = 126.10 + (np.arange(a.shape[1]) + 0.5) * DS / 3600.0
    return a / 1000.0, lat, lon          # km


def build_terrain():
    hk, lat, lon = load_dem()
    ny, nx = hk.shape
    lon0, lat0 = 126.55, 33.38
    x = (lon - lon0) * 111.32 * math.cos(math.radians(lat0))
    y = (lat - lat0) * 110.95
    X, Y = np.meshgrid(x, y)
    dx = abs(x[1] - x[0])

    # 해저 지형: 육지 마스크를 흐려 해안에서 멀수록 깊게
    mask = (hk > 0).astype(np.float32)
    fy = np.fft.fftfreq(ny, d=dx)[:, None]
    fx = np.fft.rfftfreq(nx, d=dx)[None, :]
    sig = 5.0
    ker = np.exp(-2 * math.pi ** 2 * sig ** 2 * (fx ** 2 + fy ** 2))
    s = np.fft.irfft2(np.fft.rfft2(mask) * ker, s=mask.shape).astype(np.float32)
    s = np.clip(s * 2.0, 0, 1)
    sea = -(0.03 + 1.25 * (1 - s) ** 1.5)
    final = np.where(hk > 0, hk * EX, sea).astype(np.float32)
    # 해안 직전 셀 매끄럽게
    base = np.full_like(final, BASE)

    # 메시 (위가 북쪽인 배열 → y 증가 순서로 flip)
    verts = np.stack([X, Y, base], -1).reshape(-1, 3).astype(np.float32)
    idx = np.arange(nx * ny).reshape(ny, nx)
    faces = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    mesh = bpy.data.meshes.new("JejuMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Jeju", mesh)
    bpy.context.scene.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = True

    obj.shape_key_add(name="Basis")
    sk = obj.shape_key_add(name="Birth")
    co = np.stack([X, Y, final], -1).reshape(-1, 3).astype(np.float32)
    sk.data.foreach_set("co", co.ravel())
    att = mesh.attributes.new("h", "FLOAT", "POINT")
    att.data.foreach_set("value", hk.ravel().astype(np.float32))

    iy, ix = np.unravel_index(np.argmax(hk), hk.shape)
    peak = (float(x[ix]), float(y[iy]), float(hk[iy, ix]))
    print("grid", nx, ny, "peak(km)", peak, "extent", x.min(), x.max(), y.min(), y.max())
    return obj, sk, peak


# ---------------------------------------------------------------- 노드 헬퍼
def N(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def L(nt, a, b, c=None):
    nt.links.new(a, b)


def key_node_value(nt, node, frames_vals, interp="BEZIER", out=True):
    path = f'nodes["{node.name}"].outputs[0].default_value'
    for f, v in frames_vals:
        node.outputs[0].default_value = v
        nt.keyframe_insert(data_path=path, frame=f)
    set_interp(nt, interp)


def key_input(nt, node, sock, frames_vals, interp="BEZIER"):
    path = f'nodes["{node.name}"].inputs["{sock}"].default_value'
    for f, v in frames_vals:
        node.inputs[sock].default_value = v
        nt.keyframe_insert(data_path=path, frame=f)
    set_interp(nt, interp)


def set_interp(idblock, interp):
    ad = idblock.animation_data
    if ad and ad.action:
        try:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = interp
        except Exception:
            try:  # Blender 5 layered actions
                for layer in ad.action.layers:
                    for strip in layer.strips:
                        for cb in strip.channelbags:
                            for fc in cb.fcurves:
                                for kp in fc.keyframe_points:
                                    kp.interpolation = interp
            except Exception as e:
                print("interp warn", e)


# ---------------------------------------------------------------- 재질
def terrain_material():
    m = bpy.data.materials.new("Terrain")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = N(nt, "ShaderNodeOutputMaterial")
    bs = N(nt, "ShaderNodeBsdfPrincipled")
    L(nt, bs.outputs[0], out.inputs[0])
    bs.inputs["Roughness"].default_value = 0.75

    cool = N(nt, "ShaderNodeValue", name="Cool", label="Cool")
    green = N(nt, "ShaderNodeValue", name="Green", label="Green")
    key_node_value(nt, cool, [(1, 0.0), (80, 0.0), (330, 1.0)], "LINEAR")
    key_node_value(nt, green, [(1, 0.0), (210, 0.0), (350, 1.0)], "LINEAR")

    att = N(nt, "ShaderNodeAttribute", attribute_name="h", attribute_type="GEOMETRY")
    tc = N(nt, "ShaderNodeTexCoord")
    nz1 = N(nt, "ShaderNodeTexNoise", noise_dimensions="3D")
    nz1.inputs["Scale"].default_value = 3.0
    nz1.inputs["Detail"].default_value = 8
    L(nt, tc.outputs["Object"], nz1.inputs["Vector"])
    nz2 = N(nt, "ShaderNodeTexNoise", noise_dimensions="3D")
    nz2.inputs["Scale"].default_value = 14
    L(nt, tc.outputs["Object"], nz2.inputs["Vector"])

    # 식생 / 암석 색 (고도별)
    ramp = N(nt, "ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.45, 0.40, 0.28, 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (0.35, 0.32, 0.30, 1)
    for p, c in [(0.004, (0.45, 0.40, 0.28, 1)), (0.03, (0.10, 0.22, 0.05, 1)),
                 (0.5, (0.07, 0.15, 0.04, 1)), (1.1, (0.14, 0.12, 0.08, 1)), (1.6, (0.25, 0.23, 0.22, 1))]:
        e = cr.elements.new(p)
        e.color = c
    L(nt, att.outputs["Fac"], ramp.inputs["Fac"])
    vmul = N(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    vmul.inputs[0].default_value = 0.35
    L(nt, ramp.outputs[0], vmul.inputs[6])
    L(nt, nz2.outputs["Color"], vmul.inputs[7])

    # 초목 허용 마스크: 낮은 고도일수록
    vm = N(nt, "ShaderNodeMapRange")
    vm.inputs["From Min"].default_value = 0.9
    vm.inputs["From Max"].default_value = 1.6
    vm.inputs["To Min"].default_value = 1.0
    vm.inputs["To Max"].default_value = 0.0
    L(nt, att.outputs["Fac"], vm.inputs["Value"])
    gm = N(nt, "ShaderNodeMath", operation="MULTIPLY")
    L(nt, vm.outputs[0], gm.inputs[0])
    L(nt, green.outputs[0], gm.inputs[1])

    basalt = N(nt, "ShaderNodeRGB")
    basalt.outputs[0].default_value = (0.03, 0.028, 0.027, 1)
    mixc = N(nt, "ShaderNodeMix", data_type="RGBA")
    L(nt, gm.outputs[0], mixc.inputs[0])
    L(nt, basalt.outputs[0], mixc.inputs[6])
    L(nt, vmul.outputs[2], mixc.inputs[7])

    # 용암 냉각 마스크: (노이즈 + 냉각 진행)  -> 0이면 아직 뜨거움
    add = N(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    L(nt, cool.outputs[0], add.inputs[0])
    add.inputs[1].default_value = 0.95
    nrm = N(nt, "ShaderNodeMapRange")
    nrm.inputs["From Min"].default_value = 0.35
    nrm.inputs["From Max"].default_value = 0.65
    L(nt, nz1.outputs["Fac"], nrm.inputs["Value"])
    L(nt, nrm.outputs[0], add.inputs[2])
    # 고도가 높을수록 오래 뜨겁게(새로 분출) -> 높이 보정
    hh = N(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    L(nt, att.outputs["Fac"], hh.inputs[0])
    hh.inputs[1].default_value = -0.25
    L(nt, add.outputs[0], hh.inputs[2])
    cm = N(nt, "ShaderNodeValToRGB")
    cm.color_ramp.elements[0].position = 0.88
    cm.color_ramp.elements[1].position = 0.97
    L(nt, hh.outputs[0], cm.inputs["Fac"])   # cm: 0=뜨거움 1=식음

    base = N(nt, "ShaderNodeMix", data_type="RGBA")
    L(nt, cm.outputs[0], base.inputs[0])
    base.inputs[6].default_value = (0.01, 0.008, 0.008, 1)
    L(nt, mixc.outputs[2], base.inputs[7])
    L(nt, base.outputs[2], bs.inputs["Base Color"])

    # 용암 발광 (갈라진 무늬)
    inv = N(nt, "ShaderNodeMath", operation="SUBTRACT")
    inv.inputs[0].default_value = 1.0
    L(nt, cm.outputs[0], inv.inputs[1])
    lav = N(nt, "ShaderNodeValToRGB")
    lav.color_ramp.elements[0].color = (1.0, 0.02, 0.0, 1)
    lav.color_ramp.elements[1].color = (1.0, 0.30, 0.02, 1)
    L(nt, nz2.outputs["Fac"], lav.inputs["Fac"])
    L(nt, lav.outputs[0], bs.inputs["Emission Color"])
    es = N(nt, "ShaderNodeMath", operation="MULTIPLY")
    es.inputs[1].default_value = 4.0
    L(nt, inv.outputs[0], es.inputs[0])
    L(nt, es.outputs[0], bs.inputs["Emission Strength"])
    return m


def ocean_material():
    m = bpy.data.materials.new("Ocean")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = N(nt, "ShaderNodeOutputMaterial")
    bs = N(nt, "ShaderNodeBsdfPrincipled")
    L(nt, bs.outputs[0], out.inputs[0])
    bs.inputs["Base Color"].default_value = (0.004, 0.035, 0.05, 1)
    bs.inputs["Roughness"].default_value = 0.025
    bs.inputs["IOR"].default_value = 1.333
    bs.inputs["Metallic"].default_value = 0.0

    tc = N(nt, "ShaderNodeTexCoord")
    layers = [  # (scale vector, noise scale, amplitude, w_speed_total)
        ((1.0, 2.2, 1.0), 0.28, 0.55, 5),
        ((1.0, 1.8, 1.0), 1.4, 0.30, 9),
        ((1.0, 1.5, 1.0), 6.0, 0.16, 16),
        ((1.0, 1.3, 1.0), 26.0, 0.09, 26),
        ((1.0, 1.0, 1.0), 110.0, 0.05, 40),
    ]
    acc = None
    for i, (sv, sc, amp, ws) in enumerate(layers):
        mp = N(nt, "ShaderNodeMapping")
        mp.inputs["Scale"].default_value = sv
        L(nt, tc.outputs["Object"], mp.inputs["Vector"])
        nz = N(nt, "ShaderNodeTexNoise", name=f"Wave{i}", noise_dimensions="4D")
        nz.inputs["Scale"].default_value = sc
        nz.inputs["Detail"].default_value = 3.0
        nz.inputs["Roughness"].default_value = 0.45
        L(nt, mp.outputs[0], nz.inputs["Vector"])
        key_input(nt, nz, "W", [(1, 0.0), (F_END, float(ws))], "LINEAR")
        mu = N(nt, "ShaderNodeMath", operation="MULTIPLY")
        mu.inputs[1].default_value = amp
        L(nt, nz.outputs["Fac"], mu.inputs[0])
        if acc is None:
            acc = mu
        else:
            ad = N(nt, "ShaderNodeMath", operation="ADD")
            L(nt, acc.outputs[0], ad.inputs[0])
            L(nt, mu.outputs[0], ad.inputs[1])
            acc = ad
    bump = N(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.02
    L(nt, acc.outputs[0], bump.inputs["Height"])
    L(nt, bump.outputs[0], bs.inputs["Normal"])
    return m


def plume_material():
    m = bpy.data.materials.new("Plume")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = N(nt, "ShaderNodeOutputMaterial")
    pv = N(nt, "ShaderNodeVolumePrincipled")
    L(nt, pv.outputs[0], out.inputs["Volume"])
    pv.inputs["Color"].default_value = (0.35, 0.30, 0.28, 1)
    pv.inputs["Anisotropy"].default_value = 0.3
    pv.inputs["Emission Color"].default_value = (1.0, 0.3, 0.05, 1)

    tc = N(nt, "ShaderNodeTexCoord")
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["Generated"], sep.inputs[0])
    gx = N(nt, "ShaderNodeMath", operation="SUBTRACT")
    L(nt, sep.outputs["X"], gx.inputs[0]); gx.inputs[1].default_value = 0.5
    gy = N(nt, "ShaderNodeMath", operation="SUBTRACT")
    L(nt, sep.outputs["Y"], gy.inputs[0]); gy.inputs[1].default_value = 0.5
    gx2 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, gx.outputs[0], gx2.inputs[0]); L(nt, gx.outputs[0], gx2.inputs[1])
    gy2 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, gy.outputs[0], gy2.inputs[0]); L(nt, gy.outputs[0], gy2.inputs[1])
    r2 = N(nt, "ShaderNodeMath", operation="ADD"); L(nt, gx2.outputs[0], r2.inputs[0]); L(nt, gy2.outputs[0], r2.inputs[1])
    r = N(nt, "ShaderNodeMath", operation="SQRT"); L(nt, r2.outputs[0], r.inputs[0])
    # 반경 한계: 높이에 따라 퍼지는 버섯구름
    lim = N(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    L(nt, sep.outputs["Z"], lim.inputs[0]); lim.inputs[1].default_value = 0.30; lim.inputs[2].default_value = 0.06
    diff = N(nt, "ShaderNodeMath", operation="SUBTRACT"); L(nt, lim.outputs[0], diff.inputs[0]); L(nt, r.outputs[0], diff.inputs[1])
    rm = N(nt, "ShaderNodeMapRange")
    rm.inputs["From Min"].default_value = 0.0; rm.inputs["From Max"].default_value = 0.12
    L(nt, diff.outputs[0], rm.inputs["Value"])
    # 위쪽 페이드
    zf = N(nt, "ShaderNodeMapRange")
    zf.inputs["From Min"].default_value = 0.92; zf.inputs["From Max"].default_value = 0.5
    zf.inputs["To Min"].default_value = 0.0; zf.inputs["To Max"].default_value = 1.0
    L(nt, sep.outputs["Z"], zf.inputs["Value"])
    # 노이즈
    nz = N(nt, "ShaderNodeTexNoise", name="PlumeNoise", noise_dimensions="4D")
    nz.inputs["Scale"].default_value = 5.0; nz.inputs["Detail"].default_value = 6.0
    L(nt, tc.outputs["Generated"], nz.inputs["Vector"])
    key_input(nt, nz, "W", [(1, 0.0), (F_END, 8.0)], "LINEAR")
    nr = N(nt, "ShaderNodeMapRange")
    nr.inputs["From Min"].default_value = 0.38; nr.inputs["From Max"].default_value = 0.72
    L(nt, nz.outputs["Fac"], nr.inputs["Value"])
    d1 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, rm.outputs[0], d1.inputs[0]); L(nt, zf.outputs[0], d1.inputs[1])
    d2 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, d1.outputs[0], d2.inputs[0]); L(nt, nr.outputs[0], d2.inputs[1])
    amt = N(nt, "ShaderNodeValue", name="PlumeAmt", label="PlumeAmt")
    key_node_value(nt, amt, [(1, 0.0), (20, 0.0), (80, 1.0), (170, 0.9), (290, 0.12), (340, 0.0)])
    d3 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, d2.outputs[0], d3.inputs[0]); L(nt, amt.outputs[0], d3.inputs[1])
    d4 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, d3.outputs[0], d4.inputs[0]); d4.inputs[1].default_value = 3.0
    L(nt, d4.outputs[0], pv.inputs["Density"])
    # 아래쪽은 붉게 발광
    ef = N(nt, "ShaderNodeMapRange")
    ef.inputs["From Min"].default_value = 0.0; ef.inputs["From Max"].default_value = 0.45
    ef.inputs["To Min"].default_value = 2.0; ef.inputs["To Max"].default_value = 0.0
    L(nt, sep.outputs["Z"], ef.inputs["Value"])
    e2 = N(nt, "ShaderNodeMath", operation="MULTIPLY"); L(nt, ef.outputs[0], e2.inputs[0]); L(nt, d3.outputs[0], e2.inputs[1])
    L(nt, e2.outputs[0], pv.inputs["Emission Strength"])
    return m


def text_obj(name, body, size, loc, frames, cam):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.0
    fp = r"C:\Windows\Fonts\malgunbd.ttf"
    if not os.path.exists(fp):
        fp = r"C:\Windows\Fonts\malgun.ttf"
    try:
        cu.font = bpy.data.fonts.load(fp)
        cu.font_bold = cu.font
    except Exception as e:
        print("font warn", e)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = cam
    ob.location = loc
    m = bpy.data.materials.new(name + "Mat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = N(nt, "ShaderNodeOutputMaterial")
    em = N(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.95, 0.85, 1)
    em.inputs["Strength"].default_value = 3.0
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    L(nt, tr.outputs[0], mx.inputs[1])
    L(nt, em.outputs[0], mx.inputs[2])
    L(nt, mx.outputs[0], out.inputs[0])
    f0, f1, f2, f3 = frames
    key_input(nt, mx, "Fac", [(max(f0 - 1, 0), 0.0), (f0, 0.0), (f1, 1.0), (f2, 1.0), (f3, 0.0)], "LINEAR")
    cu.materials.append(m)
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------- 빌드
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.frame_start, sc.frame_end = 1, F_END
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    cy = sc.cycles
    cy.samples = 96
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.max_bounces = 6
    cy.glossy_bounces = 4
    cy.volume_bounces = 1
    cy.volume_step_rate = 2.0
    cy.sample_clamp_indirect = 20
    sc.view_settings.view_transform = "AgX"
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(FRAMES, "f_")

    # 지형
    obj, sk, peak = build_terrain()
    obj.data.materials.append(terrain_material())
    sk.value = 0.0
    for f, v in [(1, 0.0), (40, 0.04), (110, 0.30), (200, 0.62), (290, 0.92), (350, 1.0)]:
        sk.value = v
        sk.keyframe_insert("value", frame=f)
    sk.id_data.animation_data.action  # noqa
    set_interp(sk.id_data, "BEZIER")

    # 바다 (무한 평면)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    sea = bpy.context.object
    sea.name = "Ocean"
    sea.scale = (3000, 3000, 1)
    sea.data.materials.append(ocean_material())
    # 객체 좌표계 노이즈가 scale에 영향받지 않도록 메시를 직접 확대
    bpy.ops.object.transform_apply(scale=True)

    # 분화 연기
    px, py, pz = peak
    bpy.ops.mesh.primitive_cube_add(size=1, location=(px, py, 11.0))
    pl = bpy.context.object
    pl.name = "Plume"
    pl.scale = (22, 22, 24)
    pl.data.materials.append(plume_material())
    pl.visible_shadow = False
    pl.display_type = "WIRE"

    # 하늘 + 태양
    w = bpy.data.worlds.new("Sky")
    w.use_nodes = True
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    bg = N(nt, "ShaderNodeBackground")
    ot = N(nt, "ShaderNodeOutputWorld")
    sky = N(nt, "ShaderNodeTexSky", sky_type="MULTIPLE_SCATTERING")
    sky.sun_disc = True
    sky.sun_size = math.radians(1.6)
    sky.sun_intensity = 1.0
    sky.air_density = 1.0
    sky.aerosol_density = 0.7
    sky.ozone_density = 1.0
    sky.sun_rotation = math.radians(SUN_AZ)
    L(nt, sky.outputs[0], bg.inputs[0])
    L(nt, bg.outputs[0], ot.inputs[0])
    sc.view_settings.exposure = -1.4
    for lk in ("Medium High Contrast", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = lk
            break
        except Exception:
            pass
    for f, e in [(1, 3.0), (180, 4.5), (360, 6.5)]:
        sky.sun_elevation = math.radians(e)
        sky.keyframe_insert("sun_elevation", frame=f)
    set_interp(nt, "LINEAR")

    # 카메라
    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 26
    cam_d.clip_start, cam_d.clip_end = 0.05, 4000
    cam = bpy.data.objects.new("Cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = bpy.data.objects.new("Target", None)
    sc.collection.objects.link(tgt)
    tc = cam.constraints.new("TRACK_TO")
    tc.target = tgt
    tc.track_axis, tc.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    cam_path = [(1, (-16, -46, 2.2)), (180, (-6, -40, 5.0)), (360, (14, -56, 15.0))]
    tgt_path = [(1, (px, py, 0.5)), (180, (px, py, 1.6)), (360, (px + 2, py + 8, 2.4))]
    for f, p in cam_path:
        cam.location = p
        cam.keyframe_insert("location", frame=f)
    for f, p in tgt_path:
        tgt.location = p
        tgt.keyframe_insert("location", frame=f)
    set_interp(cam, "BEZIER")
    set_interp(tgt, "BEZIER")

    # 자막
    caps = [
        ("T1", "약 180만 년 전\n얕은 바다 밑에서 화산이 깨어나다", 0.036, (1, 14, 56, 70)),
        ("T2", "끓어오르는 용암과 화산재가\n바다 위로 솟구치다", 0.036, (76, 90, 140, 156)),
        ("T3", "분출이 거듭되며 한라산을 중심으로\n화산섬이 자라나다", 0.036, (170, 184, 236, 252)),
        ("T4", "식어 굳은 용암 위에\n푸른 생명이 깃들다", 0.036, (262, 274, 305, 320)),
        ("T5", "제주도의 탄생", 0.085, (322, 334, 358, 360)),
    ]
    for nm, body, size, fr in caps:
        y = -0.20 if nm != "T5" else -0.05
        text_obj(nm, body, size, (0, y, -1.0), fr, cam)

    # 합성: 태양 글레어
    try:
        add_glare(sc)
    except Exception as e:
        print("glare skipped:", e)

    os.makedirs(FRAMES, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved", BLEND)


def add_glare(sc):
    tree = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    sc.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers")
    gl = tree.nodes.new("CompositorNodeGlare")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    go = tree.nodes.new("NodeGroupOutput")
    print("glare props:", [i.name for i in gl.inputs], gl.bl_rna.properties.keys())
    for nm, v in (("Type", "Fog Glow"), ("Quality", "High")):
        try:
            gl.inputs[nm].default_value = v
        except Exception as e:
            print("glare attr", nm, e)
    for nm, v in (("Threshold", 4.0), ("Strength", 0.35), ("Size", 0.45), ("Smoothness", 0.5)):
        if nm in gl.inputs:
            try:
                gl.inputs[nm].default_value = v
            except Exception:
                pass
    tree.links.new(rl.outputs["Image"], gl.inputs["Image"])
    tree.links.new(gl.outputs["Image"], go.inputs[0])


SUN_AZ = float(os.environ.get("SUN_AZ", "20"))


# ---------------------------------------------------------------- 테스트/인코딩
def test(frames):
    sc = bpy.context.scene
    setup_gpu(sc)
    sc.render.resolution_percentage = 50
    sc.cycles.samples = int(os.environ.get("TS", "48"))
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(HERE, f"test_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", f)


def encode():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    files = sorted(f for f in os.listdir(FRAMES) if f.endswith(".png"))
    im = bpy.data.images.load(os.path.join(FRAMES, files[0]))
    w, h = im.size
    sc.render.resolution_x, sc.render.resolution_y = w - w % 2, h - h % 2
    sc.render.resolution_percentage = 100
    sc.sequence_editor_create()
    seq = sc.sequence_editor
    strips = seq.strips if hasattr(seq, "strips") else seq.sequences
    st = strips.new_image("img", os.path.join(FRAMES, files[0]), channel=1, frame_start=1)
    for f in files[1:]:
        st.elements.append(f)
    sc.frame_start, sc.frame_end = 1, len(files)
    try:
        sc.render.image_settings.media_type = "VIDEO"
    except Exception:
        pass
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.ffmpeg.ffmpeg_preset = "GOOD"
    sc.render.filepath = os.path.join(HERE, "jeju_birth.mp4")
    bpy.ops.render.render(animation=True)


if mode == "build":
    build()
elif mode == "test":
    test([int(a) for a in argv[1:]])
elif mode == "gpu":
    setup_gpu()
    bpy.context.scene.render.resolution_percentage = int(os.environ.get("RES_PCT", "67"))
    bpy.context.scene.render.use_overwrite = False
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, F_END
    bpy.ops.render.render(animation=True)
elif mode == "encode":
    encode()

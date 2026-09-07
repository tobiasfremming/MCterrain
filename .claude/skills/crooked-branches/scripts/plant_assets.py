"""Write LSystemGrammarAsset and PlantProfile .asset files (plus .meta) for
Assets/TerrainGen/Config/Flora without the Editor.

Import this from a generator script that holds the grammar strings:

    from plant_assets import write_grammar, write_profile, ALONG, AGAINST
    write_grammar('MyTreeGrammar', GUID_G, GRAMMAR_TEXT, iterations=27)
    write_profile('MyTreePlant', GUID_P, GUID_G, seed=7, stem=(0.7,0.3,0.2),
                  initial_width=0.5, parts=[dict(symbol='L', shape='quad',
                  color=(0.2,0.5,0.2), scale=(0.5,1,1), euler=ALONG)])

GUIDs are fixed per asset by the caller (32 hex chars, unique). Regenerating
with the same GUIDs keeps every scene reference valid.

Part keys: symbol, shape (none capsule sphere cube cylinder quad prefab cone
funnel dome), color (r,g,b), scale (x,y,z), size ('param' default | 'fixed'
| 'width'), mult (sizeMultiplier, default 1), emission 0..1, euler (x,y,z),
offset (x,y,z), align (1 default; 0 = world-aligned, for hanging strands).

A part's local frame is the turtle's: +Z heading, +Y up. Primitives are built
along +Y, so ALONG lays a capsule/cone/cylinder along the stem and AGAINST
points it back down the stem (a funnel with its apex on the stalk).
"""
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..',
                    'Assets', 'TerrainGen', 'Config', 'Flora')
ROOT = os.path.normpath(ROOT)
GRAMMAR_SCRIPT = '2e27993a11194c29b3db0e6c5a2c76a0'   # LSystemGrammarAsset.cs
PROFILE_SCRIPT = '01db12252b7120b4281a3eaa4b96f2d2'   # PlantProfile.cs

SHAPE = dict(none=0, capsule=1, sphere=2, cube=3, cylinder=4, quad=5, prefab=6, cone=7, funnel=8, dome=9)
SIZE = dict(fixed=0, param=1, width=2)
ALONG = (90, 0, 0)
AGAINST = (-90, 0, 0)


def yaml_source(text):
    # single-quoted YAML scalar: '' escapes a quote, a blank line + indent is a newline
    return "'" + text.strip('\n').replace("'", "''").replace('\n', '\n\n    ') + "'"


def meta(guid):
    return f"fileFormatVersion: 2\nguid: {guid}\nNativeFormatImporter:\n  externalObjects: {{}}\n  mainObjectFileID: 11400000\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"


def header(script, name, ident):
    return f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!114 &11400000
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 0}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {script}, type: 3}}
  m_Name: {name}
  m_EditorClassIdentifier: {ident}
"""


def col(c):
    return "{r: %g, g: %g, b: %g, a: 1}" % tuple(c)


def vec(v):
    return "{x: %g, y: %g, z: %g}" % tuple(v)


def write_grammar(name, guid, text, iterations):
    body = header(GRAMMAR_SCRIPT, name, 'TerrainGen.LSystem::LSystems.LSystemGrammarAsset')
    body += f"  source: {yaml_source(text)}\n  iterations: {iterations}\n"
    os.makedirs(ROOT, exist_ok=True)
    open(os.path.join(ROOT, name + '.asset'), 'w', encoding='utf-8', newline='\n').write(body)
    open(os.path.join(ROOT, name + '.asset.meta'), 'w', encoding='utf-8', newline='\n').write(meta(guid))


def write_profile(name, guid, grammar_guid, seed, stem, parts, initial_width=0.1, stem_shape='cylinder',
                  stem_radius_scale=1.0, min_stem_radius=0.006, max_modules=250000):
    body = header(PROFILE_SCRIPT, name, 'Assembly-CSharp::PlantProfile')
    body += f"""  grammar: {{fileID: 11400000, guid: {grammar_guid}, type: 2}}
  iterations: -1
  seed: {seed}
  maxModules: {max_modules}
  turtle:
    stepLength: 1
    angleDegrees: 25
    initialWidth: {initial_width}
    widthFactor: 0.7
    lengthFactor: 0.9
    origin: {{x: 0, y: 0, z: 0}}
    heading: {{x: 0, y: 1, z: 0}}
    up: {{x: 0, y: 0, z: -1}}
  stemShape: {SHAPE[stem_shape]}
  stemColor: {col(stem)}
  stemRadiusScale: {stem_radius_scale}
  minStemRadius: {min_stem_radius}
  taperStems: 1
  hideStemsBelowRadius: 0
  parts:
"""
    for p in parts:
        body += f"""  - symbol: {p['symbol']}
    shape: {SHAPE[p['shape']]}
    prefab: {{fileID: 0}}
    color: {col(p['color'])}
    scale: {vec(p['scale'])}
    sizeFrom: {SIZE[p.get('size', 'param')]}
    paramIndex: 0
    sizeMultiplier: {p.get('mult', 1)}
    emission: {p.get('emission', 0)}
    alignToHeading: {p.get('align', 1)}
    eulerOffset: {vec(p.get('euler', (0, 0, 0)))}
    localOffset: {vec(p.get('offset', (0, 0, 0)))}
    enabled: 1
"""
    os.makedirs(ROOT, exist_ok=True)
    open(os.path.join(ROOT, name + '.asset'), 'w', encoding='utf-8', newline='\n').write(body)
    open(os.path.join(ROOT, name + '.asset.meta'), 'w', encoding='utf-8', newline='\n').write(meta(guid))

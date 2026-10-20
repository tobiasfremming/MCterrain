#!/usr/bin/env python3
"""kityaml - the one YAML library for creature species assets (Unity's text format; kit assets: kitVersion 1, parts and
modules as [SerializeReference] RefIds). It replaces the per-agent copies (scratch kityaml.py x5, kitgen.py, the dragon
generators' emit/f/v3, legpatch.py).

Two layers:

  1. The document model (exact): load an asset, read or change it, dump it. Every shipped asset round-trips byte for
     byte (creature_kit.py yaml-selftest), so a generator or a patch only changes what it touches.

        import kityaml as K
        sp = K.load('<TG>/Config/Creatures/RockCrab.asset')
        sp.part('plan')['legLength'] = 0.8             # floats are written as Unity writes a float32
        sp.part('plan')['at']['offset'] = K.V(0, 0, 0.01)
        sp.add_part('SpineField', {'id': 'teeth', ...}, after='plan')
        sp.module('Walk')['speedFroude'] = 0.3          # a module by its class name
        sp.rename('StoneCrab'); sp.save('<TG>/Config/Creatures/StoneCrab.asset')   # + .meta with a fresh guid

     Values: str (raw YAML scalar), int / float / bool (formatted), V / C / Ref / Flow (inline maps), dict (a block map),
     list (a block sequence), None (an empty value). Raw scalars that look like numbers read back as str: num(x) / f32(x)
     turn them into numbers.

  2. Writers (compatible): the functions the scratch generators used, with their exact output, so an old generator
     switches by importing this module instead of its copy:
        kit5 / crabs kityaml.py:  num, V, C, Ref, emit, at, asset, meta
        biglegs / heads kitgen.py: f, v3, col, sock, key, write, profile_joints, and its emit as emit_lines

  python generators: `creature_kit.py new <Species> --from <Species|archetype>` writes one that rebuilds the asset from
  this model (K.Species + parts/modules as Python data) - edit its numbers, run it, check.
"""
import os
import re
import struct
import uuid

# ---------------------------------------------------------------- numbers as Unity writes them


def f32(x):
    """x rounded to a float32 (what Unity stores)."""
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


def unity_float(x):
    """The text Unity writes for a float field: the shortest decimal that reads back as the same float32, '1' for 1.0,
    '-0' kept, exponents as 1e-7."""
    x = float(x)
    if x != x:
        return 'NaN'
    if x in (float('inf'), float('-inf')):
        return 'Infinity' if x > 0 else '-Infinity'
    v = f32(x)
    if v == 0:
        return '-0' if str(v).startswith('-') else '0'
    for p in range(1, 10):
        s = '%.*g' % (p, v)
        if f32(float(s)) == v:
            break
    if 'e' in s:
        m, e = s.split('e')
        s = m + 'e' + str(int(e))
    elif '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s


def fmt(v):
    """A Python value as a YAML scalar (str is raw)."""
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return unity_float(v)
    if isinstance(v, Flow):
        return v.yaml()
    if isinstance(v, str):
        return v
    raise TypeError(f'not a scalar: {v!r}')


_NUM = re.compile(r'^-?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$')


def num(v):
    """kit5 compat: its number writer (round to 6 decimals). For a raw scalar from the model: num(s) parses it."""
    if isinstance(v, str):
        return int(v) if re.match(r'^-?\d+$', v) else float(v)
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, int):
        return str(v)
    r = round(float(v), 6)
    if r == int(r):
        return str(int(r))
    return ('%.6f' % r).rstrip('0').rstrip('.')


# ---------------------------------------------------------------- inline maps


class Flow:
    """An inline map {a: 1, b: 2}: keys in order, values scalars (or nested Flow)."""

    def __init__(self, items):
        self.items = list(items.items()) if isinstance(items, dict) else list(items)

    def __getitem__(self, k):
        for a, b in self.items:
            if a == k:
                return b
        raise KeyError(k)

    def __setitem__(self, k, v):
        for i, (a, _) in enumerate(self.items):
            if a == k:
                self.items[i] = (k, v)
                return
        self.items.append((k, v))

    def yaml(self):
        return '{' + ', '.join(f'{k}: {fmt(v)}' for k, v in self.items) + '}'

    def __eq__(self, o):
        return isinstance(o, Flow) and self.yaml() == o.yaml()

    def __repr__(self):
        return f'Flow({dict(self.items)!r})'


class V(Flow):
    """A Vector3 {x, y, z}. (kit5 compat: V(x, y, z).yaml() formats with num.)"""

    def __init__(self, x=0, y=0, z=0):
        super().__init__([('x', x), ('y', y), ('z', z)])
        self.v = (x, y, z)

    def __repr__(self):
        return 'K.V(%s)' % ', '.join(_py(b) for _, b in self.items)


class C(Flow):
    """A Color {r, g, b, a}."""

    def __init__(self, r=0, g=0, b=0, a=1):
        super().__init__([('r', r), ('g', g), ('b', b), ('a', a)])
        self.v = (r, g, b, a)

    def __repr__(self):
        return 'K.C(%s)' % ', '.join(_py(b) for _, b in self.items)


class Ref(Flow):
    """A [SerializeReference] pointer {rid: N}."""

    def __init__(self, rid):
        super().__init__([('rid', rid)])
        self.rid = rid

    def __repr__(self):
        return f'K.Ref({self.rid})'


def parse_flow(s):
    """'{x: 0, y: 1}' -> Flow (V / C / Ref when the keys say so); values stay raw strings."""
    body = s.strip()[1:-1]
    items, depth, cur = [], 0, ''
    for ch in body:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        if ch == ',' and depth == 0:
            items.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        items.append(cur)
    pairs = []
    for it in items:
        k, _, v = it.strip().partition(':')
        v = v.strip()
        pairs.append((k.strip(), parse_flow(v) if v.startswith('{') else v))
    keys = [k for k, _ in pairs]
    if keys == ['x', 'y', 'z']:
        return V(*[b for _, b in pairs])
    if keys == ['r', 'g', 'b', 'a']:
        return C(*[b for _, b in pairs])
    if keys == ['rid']:
        return Ref(pairs[0][1])
    return Flow(pairs)


# ---------------------------------------------------------------- the block model (parse / emit)


def _indent(l):
    return len(l) - len(l.lstrip(' '))


def _parse_value(lines, i, indent):
    """The block at lines[i] (a map at `indent`, or a sequence whose '- ' sits at `indent`). Returns (value, next)."""
    if i < len(lines) and _indent(lines[i]) == indent and lines[i].lstrip(' ').startswith('- '):
        return _parse_seq(lines, i, indent)
    return _parse_map(lines, i, indent)


def _scalar(rest, lines, j, indent):
    """A scalar after 'key: ', with Unity's wrapped continuation lines (deeper indent, no key). Returns (value, next)."""
    v = rest
    while j < len(lines) and lines[j].strip() and _indent(lines[j]) > indent and not _is_key(lines[j]):
        v += '\n' + lines[j]
        j += 1
    if v.startswith('{') and v.endswith('}') and '\n' not in v:
        return parse_flow(v), j
    return v, j


_KEY = re.compile(r'^\s*(- )?[A-Za-z_][A-Za-z0-9_]*:( |$)')


def _is_key(l):
    return bool(_KEY.match(l))


def _parse_map(lines, i, indent, first=None):
    m = {}
    while i < len(lines):
        l = lines[i]
        if first is not None:
            text, first = first, None
        else:
            if not l.strip() or _indent(l) != indent or l.lstrip(' ').startswith('- '):
                break
            text = l[indent:]
        k, _, rest = text.partition(':')
        spaced = rest.startswith(' ')
        rest = rest[1:] if spaced else rest
        j = i + 1
        if rest or spaced:   # 'key: ' (an empty string) is not 'key:' (no value)
            m[k], i = _scalar(rest, lines, j, indent)
            continue
        if j < len(lines) and lines[j].strip() and _indent(lines[j]) > indent:
            m[k], i = _parse_map(lines, j, _indent(lines[j]))
        elif j < len(lines) and _indent(lines[j]) == indent and lines[j].lstrip(' ').startswith('- '):
            m[k], i = _parse_seq(lines, j, indent)
        else:
            m[k], i = None, j
    return m, i


def _parse_seq(lines, i, indent):
    s = []
    while i < len(lines) and lines[i].strip() and _indent(lines[i]) == indent and lines[i].lstrip(' ').startswith('- '):
        item = lines[i][indent + 2:]
        if _is_key(item):
            v, i = _parse_map(lines, i, indent + 2, first=item)
            s.append(v)
        else:
            v, i = _scalar(item, lines, i + 1, indent)
            s.append(v)
    return s, i


def _emit(m, indent, out):
    pad = ' ' * indent
    for k, v in m.items():
        if isinstance(v, dict):
            if not v:
                out.append(f'{pad}{k}: {{}}')
            else:
                out.append(f'{pad}{k}:')
                _emit(v, indent + 2, out)
        elif isinstance(v, list):
            if not v:
                out.append(f'{pad}{k}: []')
            else:
                out.append(f'{pad}{k}:')
                _emit_seq(v, indent, out)
        elif v is None:
            out.append(f'{pad}{k}:')
        else:
            out.append(f'{pad}{k}: {fmt(v)}')


def _emit_seq(s, indent, out):
    pad = ' ' * indent
    for item in s:
        if isinstance(item, dict) and item:
            sub = []
            _emit(item, indent + 2, sub)
            sub[0] = pad + '- ' + sub[0][indent + 2:]
            out.extend(sub)
        else:
            out.append(f'{pad}- {fmt(item)}')


# ---------------------------------------------------------------- species assets


SPECIES_SCRIPT_GUID = '39d3296fcbe55a0429fe582610f52ec3'   # Scripts/Creatures/CreatureSpecies.cs.meta
HEADER = ['%YAML 1.1', '%TAG !u! tag:unity3d.com,2011:', '--- !u!114 &11400000']


class Item:
    """One part or module: its class, rid and data (a dict). item['field'] reads / writes its data."""

    def __init__(self, ref):
        self.ref = ref

    @property
    def cls(self):
        return self.ref['type']['class']

    @property
    def rid(self):
        return int(self.ref['rid'])

    @property
    def data(self):
        if self.ref.get('data') is None:
            self.ref['data'] = {}
        return self.ref['data']

    @property
    def id(self):
        return self.data.get('id')

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    def get(self, k, d=None):
        return self.data.get(k, d)

    def __repr__(self):
        return f'<{self.cls} {self.id or ""} rid {self.rid}>'


class Species:
    """A species asset. Species(name, scale) starts a kit asset; load(path) reads any (kit or legacy)."""

    def __init__(self, name=None, scale=1, _root=None, _header=None):
        self.header = _header or list(HEADER)
        if _root is None:
            _root = {
                'm_ObjectHideFlags': '0', 'm_CorrespondingSourceObject': Flow([('fileID', '0')]),
                'm_PrefabInstance': Flow([('fileID', '0')]), 'm_PrefabAsset': Flow([('fileID', '0')]),
                'm_GameObject': Flow([('fileID', '0')]), 'm_Enabled': '1', 'm_EditorHideFlags': '0',
                'm_Script': Flow([('fileID', '11500000'), ('guid', SPECIES_SCRIPT_GUID), ('type', '3')]),
                'm_Name': name, 'm_EditorClassIdentifier': 'TerrainGen.Runtime::CreatureSpecies',
                'scale': scale, 'kitVersion': 1, 'parts': [], 'modules': [],
                'references': {'version': '2', 'RefIds': []},
            }
        self.root = _root

    # -- identity
    @property
    def name(self):
        return self.root.get('m_Name')

    def rename(self, name):
        self.root['m_Name'] = name
        return self

    @property
    def kit(self):
        return str(self.root.get('kitVersion', '0')) not in ('0', '')

    # -- parts and modules
    def _refs(self):
        refs = self.root.setdefault('references', {'version': '2', 'RefIds': []})
        if refs.get('RefIds') is None:
            refs['RefIds'] = []
        return refs['RefIds']

    def _by_rid(self):
        return {int(r['rid']): r for r in self._refs()}

    def _list(self, key):
        lst = self.root.get(key) or []
        by = self._by_rid()
        out = []
        for e in lst:
            rid = int(e['rid'] if isinstance(e, dict) else e['rid'])
            if rid in by:
                out.append(Item(by[rid]))
        return out

    @property
    def parts(self):
        return self._list('parts')

    @property
    def modules(self):
        return self._list('modules')

    def part(self, pid):
        """The part with this id (or, failing that, the first of this class)."""
        for p in self.parts:
            if p.id == pid:
                return p
        for p in self.parts:
            if p.cls == pid:
                return p
        raise KeyError(f'{self.name}: no part {pid!r} (ids: {[p.id for p in self.parts]})')

    def module(self, cls):
        for m in self.modules:
            if m.cls == cls:
                return m
        raise KeyError(f'{self.name}: no module {cls!r} (modules: {[m.cls for m in self.modules]})')

    def _new_rid(self):
        rids = [int(r['rid']) for r in self._refs()]
        return max(rids + [999]) + 1

    def _add(self, key, cls, data, after, rid, ns, asm):
        rid = rid if rid is not None else self._new_rid()
        ref = {'rid': str(rid), 'type': Flow([('class', cls), ('ns', ns), ('asm', asm)]), 'data': data if data else None}
        self._refs().append(ref)
        lst = self.root.get(key)
        if not isinstance(lst, list):
            lst = self.root[key] = []
        entry = {'rid': str(rid)}
        if after is None:
            lst.append(entry)
        else:
            ids = [i.id for i in self._list(key)] if key == 'parts' else [i.cls for i in self._list(key)]
            lst.insert(ids.index(after) + 1, entry)
        return Item(ref)

    def add_part(self, cls, data, after=None, rid=None, ns='CreatureKit', asm='TerrainGen.Runtime'):
        return self._add('parts', cls, data, after, rid, ns, asm)

    def add_module(self, cls, data=None, after=None, rid=None, ns='CreatureKit', asm='TerrainGen.Runtime'):
        return self._add('modules', cls, data, after, rid, ns, asm)

    def remove(self, item):
        rid = item.rid
        for key in ('parts', 'modules'):
            lst = self.root.get(key)
            if isinstance(lst, list):
                self.root[key] = [e for e in lst if int(e['rid']) != rid]
        self.root['references']['RefIds'] = [r for r in self._refs() if int(r['rid']) != rid]

    # -- text
    def dump(self):
        out = list(self.header) + ['MonoBehaviour:']
        _emit(self.root, 2, out)
        return '\n'.join(out) + '\n'

    def save(self, path, meta=True):
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(self.dump())
        if meta and not os.path.exists(path + '.meta'):
            write_asset_meta(path)
        return path


def loads(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    k = next(i for i, l in enumerate(lines) if l.startswith('MonoBehaviour:'))
    root, end = _parse_map(lines, k + 1, 2)
    if end != len(lines):
        raise ValueError(f'unparsed from line {end + 1}: {lines[end]!r}')
    return Species(_root=root, _header=lines[:k])


def load(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return loads(fh.read().replace('\r\n', '\n'))


# ---------------------------------------------------------------- .meta files


def new_guid():
    return uuid.uuid4().hex


def asset_meta_text(guid=None):
    guid = guid or new_guid()
    return ('fileFormatVersion: 2\nguid: %s\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 11400000\n'
            '  userData: \n  assetBundleName: \n  assetBundleVariant: \n' % guid)


def write_asset_meta(asset_path, guid=None):
    """<asset>.meta for a ScriptableObject asset (NativeFormatImporter) with a fresh guid; returns the guid."""
    guid = guid or new_guid()
    with open(asset_path + '.meta', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(asset_meta_text(guid))
    return guid


def write_script_meta(cs_path, guid=None):
    """<file>.cs.meta (MonoImporter defaults are Unity's; the two lines are what the repo checks in)."""
    guid = guid or new_guid()
    with open(cs_path + '.meta', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('fileFormatVersion: 2\nguid: %s\n' % guid)
    return guid


# ---------------------------------------------------------------- Python source of a species (the `new` generator)


def _py(v, ind=0):
    pad = '    ' * ind
    if isinstance(v, (V, C, Ref)):
        return repr(v)
    if isinstance(v, Flow):
        return 'K.Flow([%s])' % ', '.join(f'({k!r}, {_py(b)})' for k, b in v.items)
    if isinstance(v, dict):
        if not v:
            return '{}'
        inner = ',\n'.join(f'{pad}    {k!r}: {_py(b, ind + 1)}' for k, b in v.items())
        return '{\n' + inner + ',\n' + pad + '}'
    if isinstance(v, list):
        if not v:
            return '[]'
        if all(not isinstance(b, (dict, list)) for b in v) and len(v) <= 12:
            return '[' + ', '.join(_py(b) for b in v) + ']'
        inner = ',\n'.join(f'{pad}    {_py(b, ind + 1)}' for b in v)
        return '[\n' + inner + ',\n' + pad + ']'
    if v is None:
        return 'None'
    if v in ('[]', '{}'):
        return v   # an empty list / map: written back the same
    if isinstance(v, str):
        # a number Unity wrote stays exact as a number: unity_float(float(s)) == s
        if _NUM.match(v):
            if re.match(r'^-?\d+$', v) and v != '-0':
                return v
            if unity_float(float(v)) == v:
                return repr(float(v))
        return repr(v)
    return repr(v)


def to_python(sp, out_name=None, note=''):
    """A generator script that rebuilds `sp` exactly with this module (renamed to out_name): parts and modules as
    add_part / add_module calls when that rebuilds it, else the whole document as data (a legacy asset)."""
    want = loads(sp.dump())
    if out_name:
        want.rename(out_name)
    want = want.dump()
    src = _to_python(sp, out_name, note, False)
    try:
        if species_from_python(src).dump() == want:
            return src
    except Exception:  # noqa: BLE001
        pass
    return _to_python(sp, out_name, note, True)


_TEMPLATE_KEYS = ('m_ObjectHideFlags', 'm_CorrespondingSourceObject', 'm_PrefabInstance', 'm_PrefabAsset', 'm_GameObject',
                  'm_Enabled', 'm_EditorHideFlags', 'm_Script', 'm_Name', 'm_EditorClassIdentifier', 'scale', 'kitVersion',
                  'parts', 'modules', 'references')


def _to_python(sp, out_name, note, whole):
    name = out_name or sp.name
    L = ['#!/usr/bin/env python3',
         f'"""{name}: species generator (creature-kit). {note}'.rstrip(),
         '',
         f'Edit the numbers, run it (python {name}.py <Assets/TerrainGen>: writes Config/Creatures/{name}.asset), then',
         f'creature_kit.py check {name}',
         '"""',
         'import os',
         'import sys',
         '',
         "sys.path.insert(0, os.environ.get('CREATURE_KIT_SCRIPTS') or %r)" % os.path.dirname(os.path.abspath(__file__)),
         'import kityaml as K  # noqa: E402',
         '']
    if whole or not sp.kit:
        root = dict(sp.root)
        root['m_Name'] = name
        L.append(f'sp = K.Species(_root={_py(root)}, _header={sp.header!r})')
        return '\n'.join(L + _main())
    L.append(f'sp = K.Species({name!r}, scale={_py(sp.root.get("scale", "1"))})')
    for k in sp.root:
        if k not in _TEMPLATE_KEYS:
            L.append(f'sp.root[{k!r}] = {_py(sp.root[k])}')
    refs = sp.root['references']
    if str(refs.get('version')) != '2':
        L.append(f"sp.root['references']['version'] = {refs.get('version')!r}")
    listed = set()
    for key, add in (('parts', 'add_part'), ('modules', 'add_module')):
        for it in sp._list(key):
            listed.add(it.rid)
            t = it.ref['type']
            ns, asm = t['ns'], t['asm']
            tail = '' if (ns, asm) == ('CreatureKit', 'TerrainGen.Runtime') else f', ns={ns!r}, asm={asm!r}'
            data = it.ref.get('data')
            L.append('')
            L.append(f'sp.{add}({it.cls!r}, {_py(data) if data else "None"}, rid={it.rid}{tail})')
    # references no list names (nested [SerializeReference] objects): kept as they are
    for r in sp._refs():
        if int(r['rid']) not in listed:
            L.append('')
            L.append(f"sp._refs().append({_py(r)})")
    order = [int(r['rid']) for r in sp._refs()]
    added = [it.rid for it in sp._list('parts')] + [it.rid for it in sp._list('modules')] + [r for r in order if r not in listed]
    if added != order:
        L.append('')
        L.append("# RefIds in the asset's order")
        L.append(f"sp.root['references']['RefIds'].sort(key=lambda r, o={order!r}: o.index(int(r['rid'])))")
    return '\n'.join(L + _main())


def _main():
    return ['',
            '',
            "if __name__ == '__main__':",
            "    tg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('CREATURE_TG')",
            "    if not tg:",
            "        sys.exit('usage: %s <Assets/TerrainGen> (or set CREATURE_TG)' % sys.argv[0])",
            "    print('wrote', sp.save(os.path.join(tg, 'Config', 'Creatures', sp.name + '.asset')))",
            '']


def species_from_python(src):
    """Run a generator's source and return its `sp` (tests: the round trip)."""
    g = {'__name__': 'kityaml_generator'}
    exec(compile(src, '<generator>', 'exec'), g)
    return g['sp']


# ---------------------------------------------------------------- compat: kit5 / crabs kityaml.py


_KIT5_HEADER = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!114 &11400000
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_GameObject: {fileID: 0}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: 39d3296fcbe55a0429fe582610f52ec3, type: 3}
  m_Name: NAME
  m_EditorClassIdentifier: TerrainGen.Runtime::CreatureSpecies
"""


def _kit5_yaml(v):
    if isinstance(v, (V, C)):
        return '{%s}' % ', '.join(f'{k}: {num(b)}' for k, b in v.items)
    if isinstance(v, Ref):
        return '{rid: %d}' % int(v.rid)
    return v.yaml()


def emit(key, val, ind, out, inlist=False):
    """kit5 compat: emit(key, val, indent, out_lines)."""
    pad = ' ' * ind
    if isinstance(val, Flow):
        out.append(f'{pad}{key}: {_kit5_yaml(val)}')
    elif isinstance(val, dict):
        if not val:
            out.append(f'{pad}{key}: {{}}')
            return
        out.append(f'{pad}{key}:')
        for k, v in val.items():
            emit(k, v, ind + 2, out)
    elif isinstance(val, list):
        if not val:
            out.append(f'{pad}{key}: []')
            return
        out.append(f'{pad}{key}:')
        for item in val:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    sub = []
                    emit(k, v, ind + 2, sub)
                    if first:
                        sub[0] = pad + '- ' + sub[0][ind + 2:]
                        first = False
                    out.extend(sub)
            else:
                out.append(f'{pad}- {_kit5_yaml(item) if isinstance(item, Flow) else num(item)}')
    elif isinstance(val, str):
        out.append(f'{pad}{key}: {val}')
    elif val is None:
        out.append(f'{pad}{key}:')
    else:
        out.append(f'{pad}{key}: {num(val)}')


def at(joint=0, side=0, offset=(0, 0, 0)):
    return {'joint': joint, 'side': side, 'offset': V(*offset), 'slot': 0}


def asset(name, scale, parts, modules, extra_refs=()):
    """kit5 compat: parts / modules lists of (class, data dict); extra_refs (rid, class, data) nested references."""
    out = [_KIT5_HEADER.replace('NAME', name).rstrip('\n')]
    out.append(f'  scale: {num(scale)}')
    out.append('  kitVersion: 1')
    rid = 1000
    entries = []
    out.append('  parts:')
    for cls, data in parts:
        out.append(f'  - rid: {rid}')
        entries.append((rid, cls, data))
        rid += 1
    out.append('  modules:')
    for cls, data in modules:
        out.append(f'  - rid: {rid}')
        entries.append((rid, cls, data))
        rid += 1
    entries.extend(extra_refs)
    out.append('  references:')
    out.append('    version: 2')
    out.append('    RefIds:')
    for r, cls, data in entries:
        out.append(f'    - rid: {r}')
        out.append(f'      type: {{class: {cls}, ns: CreatureKit, asm: TerrainGen.Runtime}}')
        if not data:
            out.append('      data:')
        else:
            emit('data', data, 6, out)
    return '\n'.join(out) + '\n'


def meta(guid=None):
    """kit5 compat: (guid, .meta text)."""
    guid = guid or new_guid()
    return guid, f"""fileFormatVersion: 2
guid: {guid}
NativeFormatImporter:
  externalObjects: {{}}
  mainObjectFileID: 11400000
  userData:
  assetBundleName:
  assetBundleVariant:
"""


# ---------------------------------------------------------------- compat: biglegs / heads kitgen.py


def f(x):
    if isinstance(x, bool):
        return '1' if x else '0'
    if isinstance(x, int):
        return str(x)
    s = ('%.6f' % x).rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


def v3(x, y, z):
    return '{x: %s, y: %s, z: %s}' % (f(x), f(y), f(z))


def col(r, g, b, a=1):
    return '{r: %s, g: %s, b: %s, a: %s}' % (f(r), f(g), f(b), f(a))


def emit_lines(lines, key, val, ind):
    """kitgen compat (its `emit`): two-space levels, values already strings or numbers."""
    pad = '  ' * ind
    if isinstance(val, dict):
        lines.append(f'{pad}{key}:')
        for k, w in val.items():
            emit_lines(lines, k, w, ind + 1)
    elif isinstance(val, list):
        if not val:
            lines.append(f'{pad}{key}: []')
            return
        lines.append(f'{pad}{key}:')
        for item in val:
            if isinstance(item, dict):
                first = True
                for k, w in item.items():
                    sub = []
                    emit_lines(sub, k, w, 0)
                    for i, l in enumerate(sub):
                        prefix = (pad + '- ') if first and i == 0 else (pad + '  ')
                        lines.append(prefix + l)
                    first = False
            else:
                lines.append(f'{pad}- {item if isinstance(item, str) else f(item)}')
    elif isinstance(val, str):
        lines.append(f'{pad}{key}: {val}')
    else:
        lines.append(f'{pad}{key}: {f(val)}')


def sock(joint, side=0, off=(0, 0, 0)):
    return {'joint': joint, 'side': side, 'offset': v3(*off), 'slot': 0}


def key(t, hw, hh, rise=0.0, top=2.0, bot=2.0):
    return {'t': t, 'halfWidth': hw, 'halfHeight': hh, 'rise': rise, 'squareTop': top, 'squareBottom': bot}


def write(out, name, scale, parts, modules):
    """kitgen compat: write(path, name, scale, [(class, data)], [(class, data)])."""
    L = ['%YAML 1.1', '%TAG !u! tag:unity3d.com,2011:', '--- !u!114 &11400000', 'MonoBehaviour:',
         '  m_ObjectHideFlags: 0', '  m_CorrespondingSourceObject: {fileID: 0}', '  m_PrefabInstance: {fileID: 0}',
         '  m_PrefabAsset: {fileID: 0}', '  m_GameObject: {fileID: 0}', '  m_Enabled: 1', '  m_EditorHideFlags: 0',
         '  m_Script: {fileID: 11500000, guid: 39d3296fcbe55a0429fe582610f52ec3, type: 3}', f'  m_Name: {name}',
         '  m_EditorClassIdentifier: TerrainGen.Runtime::CreatureSpecies', f'  scale: {f(scale)}', '  kitVersion: 1', '  parts:']
    rid = 1000
    for _ in parts:
        L.append(f'  - rid: {rid}')
        rid += 1
    L.append('  modules:')
    for _ in modules:
        L.append(f'  - rid: {rid}')
        rid += 1
    L += ['  references:', '    version: 2', '    RefIds:']
    rid = 1000
    for cls, data in parts + modules:
        L.append(f'    - rid: {rid}')
        L.append(f'      type: {{class: {cls}, ns: CreatureKit, asm: TerrainGen.Runtime}}')
        L.append('      data:')
        if data is not None:
            for k, w in data.items():
                emit_lines(L, k, w, 4)
        rid += 1
    open(out, 'w', newline='\n').write('\n'.join(L) + '\n')
    print('wrote', out, len(parts), 'parts', len(modules), 'modules')


def profile_joints(keys, n):
    """kitgen compat: keys (joint, hw, hh, clearance, bend) linear between keys -> explicit joints list."""
    out = []
    for j in range(n):
        for a, b in zip(keys, keys[1:]):
            if a[0] <= j <= b[0]:
                u = (j - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
                v = [a[i] + (b[i] - a[i]) * u for i in range(1, 5)]
                out.append({'halfWidth': round(v[0], 5), 'halfHeight': round(v[1], 5), 'clearance': round(v[2], 5), 'bendLimitDeg': round(v[3], 2), 'rigid': False})
                break
    assert len(out) == n, (len(out), n)
    return out


# ---------------------------------------------------------------- self-test


def selftest(folder):
    """Every asset under `folder` round-trips: load -> dump == the file; kit assets also through to_python. Returns
    a list of problems (empty = fine)."""
    problems = []
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.asset'):
            continue
        p = os.path.join(folder, fn)
        text = open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')
        try:
            sp = loads(text)
        except Exception as e:  # noqa: BLE001
            problems.append(f'{fn}: does not parse: {e}')
            continue
        if sp.dump() != text:
            problems.append(f'{fn}: dump differs from the file ({_first_diff(sp.dump(), text)})')
            continue
        if 'm_EditorClassIdentifier: TerrainGen.Runtime::CreatureSpecies' not in text:
            continue
        try:
            sp2 = species_from_python(to_python(sp))
            if sp2.dump() != text:
                problems.append(f'{fn}: the generator does not rebuild it ({_first_diff(sp2.dump(), text)})')
        except Exception as e:  # noqa: BLE001
            problems.append(f'{fn}: generator: {type(e).__name__}: {e}')
    return problems


def _first_diff(a, b):
    la, lb = a.split('\n'), b.split('\n')
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            return f'line {i + 1}: {x!r} vs {y!r}'
    return f'{len(la)} vs {len(lb)} lines'


if __name__ == '__main__':
    import sys
    probs = selftest(sys.argv[1])
    for p in probs:
        print(p)
    print('OK' if not probs else f'{len(probs)} problem(s)')
    sys.exit(1 if probs else 0)

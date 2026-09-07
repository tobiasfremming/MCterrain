"""Writers for colony placement assets.

    from colony_assets import write_colony_grammar, write_biome_flora, species

    write_colony_grammar("DolomiteColonyGrammar", guid, GRAMMAR_TEXT, iterations=22)
    write_biome_flora("DolomiteBiome",
        [species("TreePlant", "T", spacing=4, rarity="uncommon"),
         species("MossCarpetPlant", "m", spacing=0.8, rarity="common", height=1.0)],
        colony_guid=guid, colony_chance=0.45, cover_scale=140, cover_threshold=0.05, cover_softness=0.25)

species() looks up the baked prototype set by name under Config/Flora/Prototypes
and picks draw distances from the plant's height (pass height=..., else it
reads the set's maxHeight). Rarity only matters for the uniform fallback; the
grammar decides counts where a colony is set. Re-runnable: replaces the flora
and colony blocks at the end of the asset. Biome fields are appended to the
YAML after the existing ones, which Unity accepts (order is by name).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONFIG = os.path.join(ROOT, "Assets", "TerrainGen", "Config")
PROTO = os.path.join(CONFIG, "Flora", "Prototypes")
sys.path.insert(0, os.path.join(ROOT, ".claude", "skills", "crooked-branches", "scripts"))
from plant_assets import write_grammar  # noqa: E402

RARITY = dict(custom=0, common=1, uncommon=2, rare=3, landmark=4)
PRESET = dict(custom=(6, 0.7), common=(8, 0.85), uncommon=(3, 0.5), rare=(1, 0.25), landmark=(1, 0.04))


def write_colony_grammar(name, guid, text, iterations):
    """A grammar asset in Config/Flora (the same writer the plant grammars use)."""
    write_grammar(name, guid, text, iterations)


def _proto(name):
    meta = os.path.join(PROTO, name + "_Prototypes.asset.meta")
    if not os.path.exists(meta):
        sys.exit(name + " has no baked prototype set; bake it first (PlantPrototypeBaker.Bake)")
    guid = re.search(r"guid: ([0-9a-f]{32})", open(meta, encoding="utf-8").read()).group(1)
    asset = open(meta[:-5], encoding="utf-8").read()
    h = re.search(r"\n  maxHeight: ([\d.]+)", asset)
    return guid, float(h.group(1)) if h else 5.0


def species(name, symbol, spacing, rarity="uncommon", height=None, tree=None, min_upness=None, lean=None):
    """One flora entry. symbol is the colony letter (never F G f g)."""
    if symbol in ("F", "G", "f", "g") or len(symbol) != 1:
        sys.exit("bad symbol %r for %s" % (symbol, name))
    guid, h = _proto(name)
    if height is not None:
        h = height
    if tree is None:
        tree = h >= 8 or rarity == "landmark"
    per, chance = PRESET[rarity]
    if rarity == "landmark":
        lod1, lod2, imp, cull, uselod = 60, 120, 150, 900, 0
    elif h < 2.5:
        lod1, lod2, imp, cull, uselod = 25, 50, 70, 220, 1
    elif h < 8:
        lod1, lod2, imp, cull, uselod = 40, 80, 100, 400, 1
    else:
        lod1, lod2, imp, cull, uselod = 45, 90, 120, 700, 1
    if min_upness is None:
        min_upness = 0.85 if tree else (0.7 if h < 2.5 else 0.75)
    if lean is None:
        lean = 3 if tree else 6
    sink = 0.1 if h < 2.5 else (0.2 if h < 8 else 0.4)
    scale = "{x: 0.9, y: 1.1}" if rarity == "landmark" else "{x: 0.85, y: 1.2}"
    return f"""  - label: {name}
    prototypes: {{fileID: 11400000, guid: {guid}, type: 2}}
    rarity: {RARITY[rarity]}
    perPlot: {per}
    plotChance: {chance}
    symbol: {symbol}
    minSpacing: {spacing}
    minUpness: {min_upness}
    minHeight: -1000
    maxHeight: 1000
    scaleRange: {scale}
    leanDegrees: {lean}
    sink: {sink}
    useLod: {uselod}
    lod1Distance: {lod1}
    lod2Distance: {lod2}
    impostorDistance: {imp}
    cullDistance: {cull}
    enabled: 1
"""


def write_biome_flora(biome, entries, colony_guid, colony_chance=0.45, cover_scale=140.0,
                      cover_threshold=0.05, cover_softness=0.25):
    path = os.path.join(CONFIG, biome + ".asset")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"\n  flora:.*\Z", "\n", s, flags=re.S)
    s = re.sub(r"\n  colony:.*\Z", "\n", s, flags=re.S)
    if not s.endswith("\n"):
        s += "\n"
    s += "  flora:\n" + "".join(entries) if entries else "  flora: []\n"
    s += f"  colony: {{fileID: 11400000, guid: {colony_guid}, type: 2}}\n"
    s += f"  colonyChance: {colony_chance}\n  coverScale: {cover_scale}\n  coverThreshold: {cover_threshold}\n  coverSoftness: {cover_softness}\n"
    open(path, "w", encoding="utf-8", newline="\n").write(s)


def write_world_flora(entries, colony_guid=None, colony_chance=0.4, world="DefaultPlantWorld"):
    """PlantWorld.species: the everywhere list, with its own colony grammar."""
    path = os.path.join(CONFIG, "Flora", world + ".asset")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"\n  species:.*\Z", "\n", s, flags=re.S)
    s = re.sub(r"\n  colony:.*\Z", "\n", s, flags=re.S)
    if not s.endswith("\n"):
        s += "\n"
    s += "  species:\n" + "".join(entries) if entries else "  species: []\n"
    if colony_guid:
        s += f"  colony: {{fileID: 11400000, guid: {colony_guid}, type: 2}}\n  colonyChance: {colony_chance}\n"
    open(path, "w", encoding="utf-8", newline="\n").write(s)

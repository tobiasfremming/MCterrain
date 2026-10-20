// THROWAWAY Task 6 GPU spike (not committed): two monitor-ish lizards, one renderer, flat ground.
using UnityEngine;

public class CreatureSpike : MonoBehaviour
{
    public Material material;
    CreatureSpecies sp;
    CreatureRenderer rend;
    CreatureSim[] sims;
    WanderBrain[] brains;
    public string status = "";

    void Start()
    {
        Application.runInBackground = true;
        sp = ScriptableObject.CreateInstance<CreatureSpecies>();
        float[] hw = { .022f,.032f,.040f,.036f,.034f,.036f,.050f,.062f,.072f,.080f,.085f,.084f,.078f,.066f,.052f,.044f,.038f,.033f,.028f,.024f,.020f,.017f,.014f,.011f,.008f,.005f };
        float[] hh = { .018f,.026f,.032f,.030f,.030f,.032f,.040f,.046f,.052f,.056f,.058f,.057f,.054f,.050f,.044f,.038f,.033f,.029f,.025f,.021f,.018f,.015f,.012f,.010f,.007f,.005f };
        int n = hw.Length;
        sp.spacing = 0.06f;
        sp.joints = new SpineJoint[n];
        for (int i = 0; i < n; i++)
        {
            float lift = i <= 13 ? 0.06f : i < 18 ? 0.06f * (18 - i) / 5f : 0f;
            sp.joints[i] = new SpineJoint { halfWidth = hw[i], halfHeight = hh[i], clearance = hh[i] + lift, bendLimitDeg = i >= 14 ? 25f : 20f, rigid = i == 1 || i == 2 };
        }
        sp.headCapLength = 0.05f; sp.tailTipLength = 0.04f;
        sp.legs = new[]
        {
            Leg(7, -1, new Vector3(0.20f, 0f, 0.06f), new Vector3(0.3f, 0.6f, -1f), 0),
            Leg(7, +1, new Vector3(0.20f, 0f, 0.06f), new Vector3(0.3f, 0.6f, -1f), 1),
            Leg(13, -1, new Vector3(0.20f, 0f, -0.02f), new Vector3(0.3f, 0.6f, 1f), 1),
            Leg(13, +1, new Vector3(0.20f, 0f, -0.02f), new Vector3(0.3f, 0.6f, 1f), 0),
        };
        sp.speed = 0.9f; sp.turnRateDeg = 160f; sp.accel = 3f; sp.turnSlowdown = 0.5f;
        sp.undulationDeg = 6f; sp.undulationHz = 1.4f; sp.subSteps = 2;
        sp.eyeJoint = 1; sp.eyeOffset = new Vector3(0.024f, 0.014f, 0.008f); sp.eyeRadius = 0.007f;
        sp.look = new CreatureLook
        {
            dorsal = Hex("C9A46A"), flank = Hex("B9844E"), belly = Hex("E8D9B5"), pattern = Hex("4A3322"),
            patternType = CreaturePattern.BandedSpots, patternScale = 9f, patternContrast = 0.8f, patternSoftness = 0.25f, spotScale = 0.35f,
            smoothness = 0.35f, rimStrength = 0.25f, subsurface = 0.3f, sizeJitter = 0.08f, hueJitter = 0.03f, valueJitter = 0.06f,
        };
        status = "validate=" + (sp.Validate() ?? "ok");

        rend = new CreatureRenderer(sp, material);
        var ground = new FlatGroundProbe(0f);
        sims = new CreatureSim[2]; brains = new WanderBrain[2];
        for (int k = 0; k < 2; k++)
        {
            Vector3 c = new Vector3(k == 0 ? -0.6f : 0.6f, 0f, 0f);
            var area = EnclosureArea.For(c, Vector3.up, 2.5f, sp, 1f);
            sims[k] = new CreatureSim(sp, ground, _ => Vector3.up, c, Vector3.forward, 1f, k + 1);
            sims[k].Bounds = area;
            brains[k] = new WanderBrain(area, 11 + k);
            rend.Add(sims[k], new CreatureInstance { seed = k * 17.3f, hueShift = k == 0 ? 0f : 0.03f, valueShift = k == 0 ? 0f : -0.06f, sizeScale = 1f });
        }
        status += " count=" + rend.Count + " verts=" + rend.Mesh.vertexCount;
    }

    void Update()
    {
        float dt = Time.deltaTime;
        for (int k = 0; k < sims.Length; k++) sims[k].Tick(dt, brains[k].Target(sims[k], dt));
    }

    void LateUpdate() { rend.Render(); }
    void OnDestroy() { rend?.Dispose(); if (sp) Destroy(sp); }

    static Color Hex(string h) { ColorUtility.TryParseHtmlString("#" + h, out var c); return c; }

    static LegSpec Leg(int joint, int side, Vector3 rest, Vector3 pole, int group) => new LegSpec
    {
        attachJoint = joint, side = side,
        shoulderOffset = new Vector3(0.05f, -0.01f, 0f), restOffset = rest,
        upperLength = 0.11f, lowerLength = 0.10f, upperRadius = 0.022f, lowerRadius = 0.015f,
        pole = pole, stepThreshold = 0.11f, stepDuration = 0.16f, stepLift = 0.04f, overshoot = 0.06f,
        gaitGroup = group, footLength = 0.045f, toeCount = 5,
    };
}

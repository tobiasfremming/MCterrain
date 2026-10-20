// THROWAWAY Task 7 visual check (not committed): CreatureWorld with DesertMonitors on flat ground.
using UnityEngine;

public class MonitorSpike : MonoBehaviour
{
    public Material material;
    public CreatureSpecies species;
    public CreatureWorld world;

    sealed class Straight : ICreatureBrain
    {
        public Vector3 Target(CreatureSim sim, float dt) => sim.Joints[0] + (sim.Rotations[0] * Vector3.forward) * 3f;
    }

    void Start()
    {
        Application.runInBackground = true;
        world = gameObject.AddComponent<CreatureWorld>();
        world.creatureMaterial = material;
        world.SetGround(new FlatGroundProbe(0f), _ => Vector3.up);
        // one straight walker (from far back so it is at cruise when it passes the origin) and two wanderers
        world.Spawn(species, new Vector3(0f, 0f, -6f), Vector3.forward, new Straight(), null, 1);
        for (int k = 0; k < 2; k++)
        {
            Vector3 c = new Vector3(k == 0 ? -3f : 3f, 0f, 0f);
            var area = EnclosureArea.For(c, Vector3.up, 2.5f, species, 1f);
            world.Spawn(species, c, Vector3.right, new WanderBrain(area, 21 + k), area, 2 + k);
        }
    }
}

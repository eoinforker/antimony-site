"""Ten concepts for the Antimony world: one scene build, ten moods and framings. Each entry overrides the look
constants in build_world.py. Our own world throughout; the references (../refs) inform light and mood only.

camera: x, y (metres), eye (m above ground), pitch, yaw, focal (mm), fstop, focus_m
light:  pitch (negative = above the horizon), yaw (180 = toward the camera from +X), lux, colour
fog:    density, falloff, inscatter colour, volumetric extinction, start distance (m)
crystal_shift: move the crystal (metres) toward the camera / up; stars: a night sky
"""

BASE = dict(
    camera=dict(x=-2.0, y=0.0, eye=0.95, pitch=13.0, yaw=-1.0, focal=20.0, fstop=2.8, focus_m=14.0),
    light=dict(pitch=-29.0, yaw=189.0, lux=8.0, colour="#D8E2FF", scatter=7.0),
    fog=dict(density=0.022, falloff=0.018, inscatter="#B9C6F2", vol_extinction=0.7, start_m=14.0),
    exposure=-1.0, white_temp=6000.0, tint=(0.94, 0.97, 1.08), sky_light=0.55, mie=0.012,
    crystal_glow=6.5, break_glow=7.0, crystal_shift=(0.0, 0.0, 0.0), stars=False, lightbox=(15.0, -3.4, -22.0),
)

CONCEPTS = {
    1: ("field-under-the-crystal", "Low in the flowers, the crystal backlit in lavender haze, light breaking off its edge.", {}),
    2: ("night-of-the-flowers", "Bright misty night: the crystal lit from within, stars thin through the haze, a cold moon to the side.",
        dict(light=dict(pitch=-38.0, yaw=125.0, lux=0.6, colour="#AFC4FF", scatter=4.0), exposure=3.2, stars=True,
             fog=dict(density=0.03, falloff=0.03, inscatter="#5A6FB8", vol_extinction=0.8, start_m=10.0),
             sky_light=0.8, crystal_glow=12.0, break_glow=12.0, white_temp=6500.0)),
    3: ("sea-of-mist", "From the crest: the valley drowned in mist, cliffs stepping back paler, the crystal standing out of it.",
        dict(camera=dict(x=40.0, y=4.0, eye=1.7, pitch=4.0, yaw=0.0, focal=28.0, fstop=8.0, focus_m=400.0),
             fog=dict(density=0.05, falloff=0.06, inscatter="#C4CCF0", vol_extinction=0.8, start_m=30.0),
             light=dict(pitch=-18.0, yaw=200.0, lux=8.0, colour="#E0E6FF", scatter=6.0), lightbox=(46.0, 9.0, -60.0))),
    4: ("first-light", "Dawn: the one warm palette. A low gold sun beside the crystal, violet sky, the field still blue.",
        dict(light=dict(pitch=-6.0, yaw=200.0, lux=10.0, colour="#FFC890", scatter=8.0), white_temp=6500.0,
             tint=(1.0, 0.96, 1.0), fog=dict(density=0.02, falloff=0.02, inscatter="#E6B4C8", vol_extinction=0.6, start_m=14.0),
             exposure=-0.6, mie=0.02)),
    5: ("violet-storm", "Saturated violet mist, the crystal lit from above through a break in dark cloud.",
        dict(light=dict(pitch=-60.0, yaw=170.0, lux=6.0, colour="#C8B4FF", scatter=10.0), tint=(1.0, 0.9, 1.15),
             fog=dict(density=0.04, falloff=0.02, inscatter="#8A6CD8", vol_extinction=0.9, start_m=12.0),
             exposure=-0.3, crystal_glow=9.0)),
    6: ("at-the-foot", "Close under the crystal: its base rising out of the flowers, scale overhead.",
        dict(crystal_shift=(-2950.0, 0.0, -1240.0), camera=dict(x=-2.0, y=0.0, eye=0.6, pitch=26.0, yaw=0.0, focal=16.0, fstop=4.0, focus_m=20.0),
             light=dict(pitch=-35.0, yaw=200.0, lux=8.0, colour="#D8E2FF", scatter=8.0), crystal_glow=4.0, break_glow=5.0,
             lightbox=(10.0, 5.0, 25.0))),
    7: ("the-print", "The poster close in the flowers, lit from within; the crystal soft behind it.",
        dict(camera=dict(x=10.5, y=-2.2, eye=1.3, pitch=6.0, yaw=-10.0, focal=50.0, fstop=2.0, focus_m=4.6), exposure=-0.8)),
    8: ("blue-hour", "High key, almost white: firs as ink in the mist, the crystal a pale ghost, the flowers the only colour.",
        dict(fog=dict(density=0.06, falloff=0.03, inscatter="#DDE4F6", vol_extinction=0.6, start_m=6.0), exposure=-0.2,
             light=dict(pitch=-40.0, yaw=180.0, lux=6.0, colour="#EEF2FF", scatter=3.0), mie=0.03, crystal_glow=4.0)),
    9: ("across-the-valley", "Wide and high: the land falling to the valley, the crystal on the far side, light across the hills.",
        dict(camera=dict(x=30.0, y=-60.0, eye=14.0, pitch=2.0, yaw=8.0, focal=24.0, fstop=8.0, focus_m=1000.0),
             light=dict(pitch=-22.0, yaw=215.0, lux=8.0, colour="#DCE4FF", scatter=7.0))),
    10: ("star-field", "Clear night: stars dense overhead, the crystal the brightest thing, the field answering its light.",
         dict(light=dict(pitch=-30.0, yaw=150.0, lux=0.25, colour="#9FB4FF", scatter=2.0), exposure=3.6, stars=True,
              fog=dict(density=0.008, falloff=0.05, inscatter="#33407A", vol_extinction=0.5, start_m=30.0),
              camera=dict(x=-2.0, y=0.0, eye=0.95, pitch=22.0, yaw=-1.0, focal=18.0, fstop=2.8, focus_m=14.0),
              sky_light=0.6, crystal_glow=14.0, break_glow=16.0, white_temp=6500.0, mie=0.004)),
}


def look(n):
    """The full look for concept n: BASE with that concept's overrides (nested dicts merged)."""
    name, line, over = CONCEPTS[n]
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in BASE.items()}
    for k, v in over.items():
        if isinstance(v, dict):
            out[k].update(v)
        else:
            out[k] = v
    return name, line, out

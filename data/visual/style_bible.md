# Echo Visual Style Bible

> Canonical visual specification for all generated assets in the Echo cyberpunk terminal demo.
> This document governs backgrounds, objects, UI color usage, and image generation prompts.

---

## World

The setting is a **Cyber Ancient Civilization**: a post-human world where classical Greek mythology fuses with advanced technology that its inheritors no longer fully understand. Thousands of years after a civilization-ending cataclysm, marble temples still stand, but their surfaces are threaded with quantum circuitry. Statues of forgotten gods project holographic avatars. Priests died clutching corrupted data-cores. The remnants of high technology are treated as religious artifacts.

The tone is **mythic decay**. Technology persists, but its original purpose is lost. Every glowing rune could be a prayer or a firewall. Every holographic statue might be a memorial or a security drone waiting to wake. The world doesn't feel sci-fi; it feels ancient and wrong.

---

## Architecture

Buildings blend **classical Greek** and **brutalist** influences into a single visual language:

- **Marble columns** (Doric and Ionic orders) rise from darkness, their fluted surfaces cracked and weathered.
- **Broken columns** lie at angles, partially buried in rubble and mist.
- **Brutalist concrete** slabs are fused onto the marble, raw and unadorned, as if later inhabitants reinforced structures they didn't understand.
- **Holographic overlays** flicker across stone surfaces, projecting interface elements that no longer respond correctly.
- **Concrete and marble are interleaved**, not separate. A single wall might have marble at the base and poured concrete above, with neon conduit running through both.
- **Ceilings are implied, not shown.** Most spaces feel open to darkness above, with occasional hanging cables or broken holographic projectors.

The architecture should look impossible. Not futuristic, not ancient. Something that grew from both and belongs to neither.

---

## Technology

Technology in this world is old, failing, and barely understood:

- **Cyan neon circuits** trace across stone surfaces like veins. They pulse with irregular, fading energy.
- **Floating holograms** project statues, interface panels, or ghostly data streams. They flicker, glitch, and sometimes show corrupted fragments.
- **Quantum interfaces** appear as shimmering fields of light, ripples on solid surfaces, or temporal distortions in the air.
- **Quantum-lock runes** glow on sealed doors and containers. These are geometric patterns that shift slowly, binding objects across time.
- **No screens, no keyboards, no recognizable modern devices.** All technology is integrated into architecture and objects. A "console" is a column with glowing circuitry. A "data storage" is a stone altar made of light.
- **Wires and conduits** are exposed, rusted, or fused into stone. Nothing is sleek or polished.

Technology should feel biological. Circuits pulse like veins. Metal breathes. Interfaces ripple like water.

---

## Atmosphere

- **Dark.** Most of any scene is in shadow. Light sources are small, localized, and unreliable.
- **Mysterious.** The player never sees the full picture. Mist, fog, and darkness obscure the edges of every space.
- **Abandoned.** No living people are visible. Signs of past habitation (robes, tools, ritual marks) are present but deteriorated.
- **Melancholy.** The beauty is in the decay. A broken column with a single working circuit is more poignant than a pristine one.
- **Decaying grandeur.** Everything was once magnificent. Now it crumbles, flickers, and fails.

The air smells of ozone, old incense, and something metallic. Water drips from unseen sources. Echoes bounce through hollow chambers. The space feels vast and empty.

---

## Lighting

**Absolute rules:**

| Light Type | Color | Usage |
|-----------|-------|-------|
| Primary ambient | Blue-cyan | General scene illumination, fills shadowed areas with cold light |
| Secondary accent | Purple / magenta | Edge lighting on holograms, quantum effects, rare highlights |
| Danger signal | Neon red (`#ff0040`) | Locked doors, unstable objects, god intervention warnings |
| Neon primary | Neon green (`#00ff41`) | Safe pathways, functional circuits, UI overlay light sources |
| Neon secondary | Neon cyan (`#00ffff`) | Holograms, data streams, quantum interfaces |

**Forbidden light colors:**
- NO warm light. No yellow, no orange, no sunlight.
- NO incandescent glow. No fire, no torches, no warm bulbs.
- NO cheerful brightness. Light should feel cold, failing, and eerie.

Light should feel like it comes from technology, not nature. Even ambient light is artificial, as if the temple itself generates a faint electromagnetic field. Shadows dominate. Light sources are small pools in large darkness.

---

## Color Palette

Reference: `palette.yaml` for exact hex values.

| Role | Hex | Description |
|------|-----|-------------|
| Background base | `#0a0a0a` | Near-black, the void behind everything |
| Background surface | `#111111` | Dark stone, distant walls |
| Background elevated | `#1a1a1a` | Closer stone, foreground surfaces |
| Neon primary (green) | `#00ff41` | Primary UI, safe interactions, functional circuits |
| Neon secondary (cyan) | `#00ffff` | Holograms, information, quantum effects |
| Neon danger (red) | `#ff0040` | Danger, warnings, god intervention |
| Neon accent (magenta) | `#ff00ff` | Rare accents, temporal distortions |
| Stone gray | `#6b6b6b` | Weathered gray marble |
| Oxidized bronze | `#8b7355` | Dark bronze with patina |
| Brutalist concrete | `#4a4a4a` | Raw, unadorned concrete |
| Text primary | `#00ff41` | Main terminal text |
| Text muted | `#339933` | Secondary text, labels |
| Text dim | `#1a661a` | Tertiary text, metadata |

The palette is cold and dark. The only warm tone is oxidized bronze, which reads as brownish-gray rather than truly warm. Everything else trends toward blue, green, and red on a black base.

---

## Object Generation Rules

All interactive object assets must follow these rules:

1. **Isolated.** The object appears alone, with no background scene behind it.
2. **Centered.** The object sits in the center of the frame.
3. **Transparent background.** The background is solid black (`#000000`) or transparent PNG, so the object can be composited onto any scene background.
4. **Game asset.** The style is concept art for a game, not a photoreal render. Stylized, atmospheric, detailed.
5. **Front view.** The camera looks at the object from the front, slightly elevated (3/4 angle acceptable for 3D objects like columns).
6. **High detail.** Texture, weathering, circuitry, and material qualities should be visible and detailed.
7. **No people.** Objects only. If an object implies a person (e.g., a corpse), it should be the object itself, not a living character.
8. **No text or logos.** No visible text, branding, or watermarks on the asset.
9. **Studio lighting.** Even, slightly dramatic lighting that shows the object clearly while maintaining the dark, moody aesthetic.
10. **Size: 512x512.** Square format for flexible placement.

**Exception:** Holographic objects (like the Holo-Altar) use `mix-blend-mode: screen` in CSS. Their black background becomes transparent naturally when composited. These objects skip background removal.

---

## Background Generation Rules

All scene background assets must follow these rules:

1. **Wide cinematic composition.** The image fills a 16:9 widescreen frame with depth and atmosphere.
2. **Empty foreground.** The lower third of the image should be relatively clear, providing space where interactive objects can be composited later. No major objects, characters, or structures in the foreground zone.
3. **Game environment.** The style matches the object assets: concept art for a game, stylized and atmospheric.
4. **Slight overhead angle.** The camera is positioned slightly above eye level, looking down at about 15 degrees. This shows floor detail and creates depth.
5. **Atmospheric perspective.** Distant elements fade into mist or darkness. Depth haze is present.
6. **Size: 1920x1080.** Full HD widescreen.
7. **No characters or people.** The scene is empty of living beings.
8. **No text or logos.** Pure environment.
9. **Multiple light sources at varied depths.** Near circuits glow brightly, distant ones flicker dimly. This creates layers of depth.
10. **Foreground should feel like a stage.** The space where objects will be placed should look like a natural resting spot, not random floor.

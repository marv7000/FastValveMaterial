# FastValveMaterial
Convert PBR materials to VMT and VMF files that imitate PBR properties in Source engine games like Garry's Mod.
# Dependencies:
- pillow (PIL)
- numpy
# Setup:
- If you're using the release version, you don't need to do anything else
- On the other hand, when cloning the source, make sure to also pull and initialize VTFLibWrapper ("git submodules init" + "git submodules pull")

- You will need the following textures:
    - Diffuse/Color map
    - Normal map
    - Metalness map
    - Glossiness map (If you have a roughness map, set "Material Type" in config.md to "rough")
    - Optional: Ambient Occlusion map (If no image is given, the script defaults to a white image as the AO map)

1. Adjust config.md
2. Drop all texture files into your input folder
3. Run FastValveMaterial.py

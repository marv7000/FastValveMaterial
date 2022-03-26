[![Releases](https://img.shields.io/github/downloads/marv7000/FastValveMaterial/total.svg)](https://github.com/marv7000/FastValveMaterial/releases) [![License](https://img.shields.io/github/license/marv7000/FastValveMaterial.svg)](https://github.com/marv7000/Tyrant/blob/master/LICENSE)
# FastValveMaterial
Convert PBR materials to VMT and VMF files that imitate PBR properties in Source engine games like Garry's Mod.
# Dependencies:
- pillow (PIL)
- numpy
- VTFLibWrapper (https://github.com/Ganonmaster/VTFLibWrapper)
# Setup:
- If you're using the release version, you don't need to do anything else
- On the other hand, when cloning the source, make sure to also pull and initialize VTFLibWrapper ("git submodules init" + "git submodules update")

- You will need the following textures:
    - Diffuse/Color map
    - Normal map
    - Metalness map
    - Glossiness map (If you have a roughness map, set "Material Type" in config.md to "rough")
    - Optional: Ambient Occlusion map (If no image is given, the script defaults to a white image as the AO map)

1. Adjust config.md
2. Drop all texture files into your input folder
3. Run FastValveMaterial.py
# Notes and Troubleshooting:
- Make sure your images are in RGBA8888 format. While the script can understand many different color formats, if you're getting errors, check if this is the case.
- The config file needs to stay stay 34 lines long, since FVM is just parsing the parameters from every line. For example, if you want to ignore an image, simply clear the line and do not delete it!
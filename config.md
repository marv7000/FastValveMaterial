# Input format ("png", "tga")
png
# Input naming scheme (The endings of the image names in order: color map, AO map, normal map, gloss/rough map, metal map - If any map parameter is left empty, it'll be ignored and replaced with an empty image)
_rgb
_ao
_n
_r
_m
# Input path
images/
# Map used to determine material name
_n
# Output path (Can also be multiple subfolders, e.g. folder1/folder2/output/ - This path will be referenced in the VMT file!)
fastvalvematerial/
# Gamma adjustment (0-255) - Only change this from 235 if you know what you're doing, other values might break the PBR effect! Lower gamma values equal to less specular highlighting / more roughness
235
# Export converted images as tga as well (False/True)
False
# Material setup ("gloss", "rough")
rough
# Print debug messages (False/True)
True
# Print config file (False/True)
False
# Force image compression (Defaults to DXT5, otherwise RGBA8888)
True
# Force empty green channel on exponent map (For example when using mesh-stacking, False/True)
False
# Metalness factor (0-255) - Makes material less or more metallic (Useful if your material looks too shiny)
255
# Use material proxies (Only works in Garry's Mod and requires https://steamcommunity.com/sharedfiles/filedetails/?id=2459720887) (False/True)
False
# ORM texture mode (e.g. for UE4)
False
# $Color2 Value (Used to adjust parts such as: screws, metal, scratches, details, etc. Best case scenario is to start with 0.5 and work your way around it)
0.5
# $PhongBoost Value (The best range for this is usually 1-3.5, but don't be afraid to venture over/under this range for testing purposes)
2.5

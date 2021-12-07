# Input format ("png", "tga")
tga
# Input naming scheme (The endings of the image names in order: color map, ao map, normal map, gloss/rough map, metal map - If one parameter isn't set to a valid value, the corresponding method won't be called)
_rgb
_ao
_n
_g
_m
# Input path
images/
# Map used to determine material name
_n
# Output path (Can also be multiple subfolders, e.g. folder1/folder2/output/ - This path will be referenced in the VMT file!)
fastvalvematerial/
# Gamma adjustment (0-255) - Only change this from 215 if you know what you're doing, other values might break the PBR effect!
215
# Export converted images as tga as well (False/True)
False
# Material setup ("gloss", "rough")
rough
# Print debug messages (False/True)
True
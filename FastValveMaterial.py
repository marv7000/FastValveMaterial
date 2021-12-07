""" Simple Source Material "PBR" generator

Prerequisites (Python 3.x):
pillow, numpy


MIT License

Copyright (c) 2021 Marvin Friedrich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. """

from PIL import Image, ImageChops, ImageOps
import os
import sys
import math
import VTFLibWrapper.VTFLib as VTFLib
import VTFLibWrapper.VTFLibEnums as VTFLibEnums
import numpy as np
from ctypes import create_string_buffer
from pathlib import Path
import shutil

vtf_lib = VTFLib.VTFLib()

print("FastValveMaterial (v1207)\n")

f = open("config.md", 'r') # Read the config file (Actual line - 1)
config = f.read().splitlines()
config_input_format = config[1]
config_input_name_scheme = (config[3],config[4],config[5],config[6],config[7])
config_path = config[9]
config_input_mat_format = config[11]
config_output_path = config[13]
config_midtone = config[15]
config_export_images = eval(config[17])
config_material_setup = config[19]
config_debug_messages = eval(config[21])

def debug(message):
    if config_debug_messages:
        print(message)

def check_for_valid_files(path, name, ending): # Check if a file in "path" starts with the desired "name" and ends with "ending"
    for file in os.listdir(path):
        if file.endswith(ending) and file.startswith(name):
            return file

def find_material_names(): # Uses the color map to determine the current material name
    listStuff = []
    for file in os.listdir(config_path):
        if file.endswith(config_input_mat_format + "." + config_input_format): # If file ends with "scheme.format"
            listStuff.append(file.replace(config_input_mat_format + "." + config_input_format, "")) # Get rid of "scheme.format" to get the material name and append it to the list of all materials
    return listStuff

def do_diffuse(cIm, aoIm): # Generate Diffuse/Color map
    if config_input_name_scheme[1] != '':
        final_diffuse = ImageChops.multiply(cIm, aoIm) # Combine diffuse and occlusion map
    else:
        final_diffuse = cIm
    r,g,b,a = final_diffuse.split()     # Split diffuse image into channels to modify alpha
    a = a.convert('RGBA')               # Convert to RGBA so we can call Image.blend with metalImage
    a = Image.blend(a, metalImage, 1)   # Blend the alpha channel with metalImage
    a = a.convert('L')                  # Convert back to Linear
    color_spc = (r,g,b,a)
    final_diffuse = Image.merge("RGBA", color_spc)  # Merge all channels together
    export_texture(final_diffuse, (name+'_c.vtf'), 'DXT5')
    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        shutil.move(name+'_c.vtf', os.path.join(os.getcwd(), config_output_path))
        debug("[FVM] Diffuse exported")
    except:
        os.remove(name+"_c.vtf")
        debug("[FVM] Diffuse already exists!")

def do_exponent(gIm): # Generate the exponent map
    finalExponent = gIm
    r,g,b,a = finalExponent.split()
    layerImage = Image.new('RGBA', [finalExponent.size[0], finalExponent.size[1]], (0, 217, 0, 100))
    blackImage = Image.new('RGBA', [finalExponent.size[0], finalExponent.size[1]], (0, 0, 0, 100))
    finalExponent = Image.blend(finalExponent, layerImage, 0.5)

    g = g.convert('RGBA')
    b = b.convert('RGBA')
    g = Image.blend(g, layerImage, 1)
    b = Image.blend(b, blackImage, 1)
    g = g.convert('L')
    b = b.convert('L')

    colorSpc = (r,g,b,a)
    finalExponent = Image.merge('RGBA', colorSpc)
    export_texture(finalExponent, (name+'_m.vtf'), 'DXT1')
    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        shutil.move(name+'_m.vtf', config_output_path)
        debug("[FVM] Exponent exported")
    except:
        os.remove(name+"_m.vtf")
        debug("[FVM] Exponent already exists!")

def convert_roughness_to_gloss(mIm): # Inverts a roughness map "mIm" to get a glossiness map
    return ImageOps.invert(mIm)

def do_normal(config_midtone, nIm, gIm):
    finalNormal = nIm
    finalGloss = gIm
    row = finalGloss.size[0]
    col = finalGloss.size[1]
    for x in range(1 , row):
        print("(", math.ceil(x/row*100),"%)", end="\r")
        for y in range(1, col):
            value = do_gamma(x,y,finalGloss, int(config_midtone))
            finalGloss.putpixel((x,y), value)

    r,g,b,a = finalNormal.split()
    finalGloss = finalGloss.convert('L')
    a = Image.blend(a, finalGloss, 1)
    a = a.convert('L')
    colorSpc = (r,g,b,a)
    finalNormal = Image.merge('RGBA', colorSpc)

    if config_export_images:
        finalNormal.save((name+'_n.tga'), 'TGA')
    export_texture(finalNormal, (name+'_n.vtf'), 'RGBA8888') # Export normal map as *_n.vtf
    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        shutil.move(name+'_n.vtf', config_output_path)
        debug("[FVM] Normal exported")
    except:
        os.remove(name+"_n.vtf")
        debug("[FVM] Normal already exists!")

def do_gamma(x, y, im, mt): # Change the gamma of the given channels of "im" at a given xy coordinate to "config_midtone", similar to how photoshop does it
    gamma = 1
    midToneNormal = mt / 255
    if mt < 128:
        midToneNormal = midToneNormal * 2
        gamma = 1 + (9*(1-midToneNormal))
        gamma = min(gamma, 9.99)
    elif mt > 128:
        midToneNormal = (midToneNormal * 2) - 1
        gamma = 1 - midToneNormal
        gamma = max(gamma, 0.01)

    gamma_correction = 1/gamma
    (r,g,b,a) = im.getpixel((x,y))
    r = 255 *  ( (r - 0 ) / ( 255 - 0 ) )
    g = 255 *  ( (g - 0 ) / ( 255 - 0 ) )
    b = 255 *  ( (b - 0 ) / ( 255 - 0 ) )
    if mt != 128:
        r = 255 * ( pow( ( r / 255 ), gamma_correction ) )
        g = 255 * ( pow( ( g / 255 ), gamma_correction ) )
        b = 255 * ( pow( ( b / 255 ), gamma_correction ) )

    r = ( r / 255 ) *( 255 - 0 ) + 0
    g = ( g / 255 ) *( 255 - 0 ) + 0
    b = ( b / 255 ) *( 255 - 0 ) + 0
    r = math.ceil(r)
    g = math.ceil(g)
    b = math.ceil(b)
    return (r,g,b,a)

def fix_scale_mismatch(rgbIm, target): #Resize the target image to be the same as rgbIm (needed for normal maps)
    if target.height != rgbIm.height:
        factor = rgbIm.height / target.height
        fixedMap = ImageOps.scale(target, factor)
        return fixedMap
    else:
        return target

def do_material(mName): # Create a material with the given image names
    debug("[FVM] Creating material '"+ mName + "'")
    writer = ('// Generated by FastValveMaterial v1207'
    '\n"VertexLitGeneric"',
    '\n{', 
    '\n\t$basetexture ' + config_output_path + mName + "_c",
    '\n\t$bumpmap ' + config_output_path + mName + "_n",
    '\n\t$phongexponenttexture ' + config_output_path + mName + "_m",
    '\n\t$color2	"[ .3 .3 .3 ]"',
    '\n\t$blendtintbybasealpha "1"',
    '\n\t$phong "1"',
    '\n\t$phongboost "1"',
    '\n\t$phongalbedotint "1"',
    '\n\t"$PhongFresnelRanges" "[ 2 4 30 ]"',
    '\n\t$envmap	"env_cubemap"',
    '\n\t$basemapalphaenvmapmask "1"',
    '\n\t$envmapfresnel "0.3"',
    '\n\t$envmaptint "[ .035 .035 .035 ]"',
    '\n\t"Proxies"', 
    '\n\t{',
    '\n\t\t"MwEnvMapTint"',
    '\n\t\t{',
    '\n\t\t\t"min" "0"',
    '\n\t\t\t"max" "0.015"',
    '\n\t\t}',
    '\n\t}',
    '\n}')
    try:
        Path("materials/").mkdir(parents=True, exist_ok=True)
        f = open(mName + ".vmt", 'w')
        f.writelines(writer)
        f.close()
        shutil.move(mName+'.vmt', "materials/")
    except:
        debug("[FVM] Material already exists!")

def export_texture(texture, path, imageFormat=None): # Exports an image to VTF using VTFLib
    image_data = (np.asarray(texture)*-1) * 255
    image_data = image_data.astype(np.uint8, copy=False)
    def_options = vtf_lib.create_default_params_structure()
    if imageFormat.startswith('RGBA8888'):
        def_options.ImageFormat = VTFLibEnums.ImageFormat.ImageFormatRGBA8888
        def_options.Flags |= VTFLibEnums.ImageFlag.ImageFlagEightBitAlpha
        if imageFormat == 'RGBA8888Normal':
            def_options.Flags |= VTFLibEnums.ImageFlag.ImageFlagNormal
    elif imageFormat.startswith('DXT1'):
        def_options.ImageFormat = VTFLibEnums.ImageFormat.ImageFormatDXT1
        if imageFormat == 'DXT1Normal':
            def_options.Flags |= VTFLibEnums.ImageFlag.ImageFlagNormal
    elif imageFormat.startswith('DXT5'):
        def_options.ImageFormat = VTFLibEnums.ImageFormat.ImageFormatDXT5
        def_options.Flags |= VTFLibEnums.ImageFlag.ImageFlagEightBitAlpha
        if imageFormat == 'DXT5Normal':
            def_options.Flags |= VTFLibEnums.ImageFlag.ImageFlagNormal
    else:
        def_options.ImageFormat = VTFLibEnums.ImageFormat.ImageFormatRGBA8888
        def_options.Flags |= VTFLibEnums.ImageFlag.ImageFlagEightBitAlpha


    def_options.Resize = 1
    w, h = texture.size
    image_data = create_string_buffer(image_data.tobytes())
    vtf_lib.image_create_single(w, h, image_data, def_options)
    vtf_lib.image_save(path)
    vtf_lib.image_destroy()

# /////////////////////
# Main loop
# /////////////////////
for name in find_material_names(): # For every material in the input folder
    debug("[FVM] Loading:")
    try:
        debug("Material:\t"+ name)
        # Set the paths to the textures based on the config file
        
        colorSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[0] + "." + config_input_format)) 
        if config_input_name_scheme[1] != '': # If the occlusion map is set
            aoSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[1] + "." + config_input_format))
        normalSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[2] + "." + config_input_format))
        glossSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[3] + "." + config_input_format))
        metalSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[4] + "." + config_input_format))
    except FileNotFoundError:
        debug("[FVM] [ERROR] Program terminated with exit code -1:\nCouldn't locate files with correct naming scheme, throwing FileNotFoundError!")
        sys.exit()

    debug("Color:\t\t" +colorSt)
    if config_input_name_scheme[1] != '':
        debug("Occlusion:\t" +aoSt)
    else:
        debug("Occlusion:\t" +"None given, ignoring!")
    debug("Metalness:\t" +metalSt)
    debug("Normal:\t\t" +normalSt)
    debug("Glossiness:\t" +glossSt + "\n")
    
    colorImage = Image.open(colorSt)
    if config_input_name_scheme[1] != '':
        aoImage = Image.open(aoSt)
    metalImage = Image.open(metalSt)
    normalImage = Image.open(normalSt)
    glossImage = Image.open(glossSt)

    if config_material_setup == "rough": # I know this is simple as hell
        glossImage = convert_roughness_to_gloss(glossImage)
    if config_input_name_scheme[1] != '':
        aoImage = fix_scale_mismatch(colorImage, aoImage)
    metalImage = fix_scale_mismatch(colorImage, metalImage)
    normalImage = fix_scale_mismatch(colorImage, normalImage)
    glossImage = fix_scale_mismatch(colorImage, glossImage)

    if config_input_name_scheme[1] != '':
        do_diffuse(colorImage, aoImage)
    else:
        do_diffuse(colorImage, None)
    do_exponent(glossImage)
    do_normal(config_midtone, normalImage, glossImage)
    do_material(name)
    print("[FVM] Conversion for material '" + name + "' finished, files saved to '" + config_output_path + "'\n")

debug("[FVM] Program terminated with exit code 0")
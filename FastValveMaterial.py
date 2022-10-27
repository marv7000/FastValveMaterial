""" Simple Source Material "PBR" generator

Prerequisites (Python 3.x):
pillow, numpy


MIT License

Copyright (c) 2022 Marvin Friedrich

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
version = "221028"
print("FastValveMaterial (v"+version+")\n")

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
config_print_config = eval(config[23])
config_force_compression = eval(config[25])
config_clear_exponent = eval(config[27])
config_metallic_factor = eval(config[29])/255*0.83 # ? Weird ass conversion to account for the lambert factor
config_material_proxies = eval(config[31])
config_orm = eval(config[33])
config_phongwarps = eval(config[35])

def debug(message):
    if config_debug_messages:
        print("[FVM]", message)

def check_for_valid_files(path, name, ending): # Check if a file in "path" starts with the desired "name" and ends with "ending"
    for file in os.listdir(path):
        # ? Works in theory, but is busted if materials start with the same prefix
        if file.endswith(ending) and file.startswith(name + ending):
            return file

def find_material_names(): # Uses the color map to determine the current material name
    listStuff = []
    for file in os.listdir(config_path):
        if file.endswith(config_input_mat_format + "." + config_input_format): # If file ends with "scheme.format
            listStuff.append(file.replace(config_input_mat_format + "." + config_input_format, "")) # Get rid of "scheme.format" to get the material name and append it to the list of all materials

    return listStuff

def do_diffuse(cIm, aoIm, mIm, gIm): # Generate Diffuse/Color map
    final_diffuse = cIm.convert("RGBA")
    if aoIm != None:
        final_diffuse = ImageChops.multiply(final_diffuse.convert("RGB"), aoIm.convert("RGB")).convert("RGBA") # Combine diffuse and occlusion map
    else:
        final_diffuse = ImageChops.blend(final_diffuse.convert("RGB"), ImageChops.multiply(final_diffuse.convert("RGB"), gIm.convert("RGB")), 0.3).convert("RGBA") # Combine diffuse and glossiness map
    r,g,b,a = final_diffuse.split() # Split diffuse image into channels to modify alpha
    # * I think i forgot to remove some excess conversion but i literally cannot be asked to do so
    a = Image.blend(cIm.convert("L"), mIm.convert("L"), config_metallic_factor) # Blend the alpha channel with metalImage
    a = a.convert("L") # Convert back to Linear
    color_spc = (r,g,b,a)
    final_diffuse = Image.merge("RGBA", color_spc)  # Merge all channels together
    export_texture(final_diffuse, (name+'_c.vtf'), 'DXT5')
    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        shutil.move(name+'_c.vtf', os.path.join(os.getcwd(), config_output_path))
        debug("Diffuse exported")
    except Exception as e:
        debug("Diffuse already exists, replacing!")
        shutil.copyfile(os.path.join(os.getcwd(), name+"_c.vtf"), os.path.join(os.getcwd(), config_output_path+name+"_c.vtf"), follow_symlinks=True)
        os.remove(os.path.join(os.getcwd(), name+"_c.vtf"))

def do_exponent(gIm): # Generate the exponent map
    finalExponent = gIm.convert("RGBA")
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
    if config_clear_exponent:
        g = Image.new('L', [finalExponent.size[0], finalExponent.size[1]], 255)
    colorSpc = (r,g,b,a)
    finalExponent = Image.merge('RGBA', colorSpc)
    export_texture(finalExponent, (name+'_m.vtf'), 'DXT5' if config_force_compression else 'DXT1')
    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        shutil.move(name+'_m.vtf', config_output_path)
        debug("Exponent exported")
    except Exception as e:
        debug("Exponent already exists, replacing!")
        shutil.copyfile(os.path.join(os.getcwd(), name+"_m.vtf"), os.path.join(os.getcwd(), config_output_path+name+"_m.vtf"), follow_symlinks=True)
        os.remove(os.path.join(os.getcwd(), name+"_m.vtf"))

def do_normal(config_midtone, nIm, gIm):
    finalNormal = nIm.convert('RGBA')
    finalGloss = gIm.convert('RGBA')
    row = finalGloss.size[0]
    col = finalGloss.size[1]
    for x in range(1 , row):
        print("[FVM] Normal conversion: (" + str(math.ceil(x/row*100)) + "%)", end="\r")
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
    export_texture(finalNormal, (name+'_n.vtf'), 'DXT5' if config_force_compression else 'RGBA8888') # Export normal map as *_n.vtf
    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        shutil.move(name+'_n.vtf', config_output_path)
        debug("Normal exported                  ") # Spaces are needed in order to overwrite the progress count, otherwise about 4 chars will stay on screen
    except Exception as e:
        debug("Normal already exists, replacing!")
        shutil.copyfile(os.path.join(os.getcwd(), name+"_n.vtf"), os.path.join(os.getcwd(), config_output_path+name+"_n.vtf"), follow_symlinks=True)
        os.remove(os.path.join(os.getcwd(), name+"_n.vtf"))

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
    if mt != 128:
        r = 255 * ( pow( ( r / 255 ), gamma_correction ) ) # ! no clue what this does i copied it from stack overflow
        g = 255 * ( pow( ( g / 255 ), gamma_correction ) )
        b = 255 * ( pow( ( b / 255 ), gamma_correction ) )
    r = math.ceil(r)
    g = math.ceil(g)
    b = math.ceil(b)
    return (r,g,b,a)

def fix_scale_mismatch(rgbIm, target): # Resize the target image to be the same as rgbIm (needed for normal maps)
    factor = rgbIm.height / target.height
    fixedMap = ImageOps.scale(target, factor)
    return fixedMap

def do_material(mName): # Create a material with the given image names
    debug("Creating material '"+ mName + "'")
    proxies = ""
    phong = ""
    if config_material_proxies:
        proxies = ['\n\t"Proxies"', '\n\t{', '\n\t\t"MwEnvMapTint"', '\n\t\t{', '\n\t\t\t"min" "0"', '\n\t\t\t"max" "0.015"', '\n\t\t}', '\n\t}']
    if config_phongwarps:
        phong = '\n\t"$phongwarptexture" "' + config_output_path + 'phongwarp_steel"'
    else:
        '\n\t"$PhongFresnelRanges" "[ 4 3 10 ]"'
    writer = ['// Generated by FastValveMaterial v' + version,
    '\n// METALNESS: ' + str(int(config_metallic_factor*255)) + ' GAMMA: ' + str(config_midtone),
    '\n"VertexLitGeneric"',
    '\n{', 
    '\n\t"$basetexture" "' + config_output_path + mName + '_c"',
    '\n\t"$bumpmap" "' + config_output_path + mName + '_n"',
    '\n\t"$phongexponenttexture" "' + config_output_path + mName + '_m"',
    '\n\t"$color2" "[ .1 .1 .1 ]"',
    '\n\t"$blendtintbybasealpha" "1"',
    '\n\t"$phong" "1"',
    '\n\t"$phongboost" "10"',
    '\n\t"$phongalbedotint" "1"',
    phong,
    '\n\t"$envmap" "env_cubemap"',
    '\n\t"$basemapalphaenvmapmask" "1"',
    '\n\t"$envmapfresnel" "0.4"',
    '\n\t"$envmaptint" "[ .1 .1 .1 ]"']
    proxies += '\n}'
    writer += proxies

    try:
        Path(config_output_path).mkdir(parents=True, exist_ok=True)
        f = open(mName + ".vmt", 'w')
        f.writelines(writer)
        f.close()
        shutil.move(mName+'.vmt', config_output_path)
        shutil.copy("phongwarp_steel.vtf", config_output_path)
        debug("Material exported                  ") # ? Spaces are needed in order to overwrite the progress count, otherwise about 4 chars will stay on screen (?????)
    except Exception as e:
        debug("Material already exists, replacing!")
        shutil.copy("phongwarp_steel.vtf", config_output_path)
        shutil.copyfile(os.path.join(os.getcwd(), mName+".vmt"), os.path.join(os.getcwd(), config_output_path+mName+".vmt"), follow_symlinks=True)
        os.remove(os.path.join(os.getcwd(), mName+".vmt"))

def do_nrm_material(mName):
    debug("Creating material '"+ mName + "'")
    proxies = ""
    if config_material_proxies:
        proxies = ['\n\t"Proxies"', '\n\t{', '\n\t\t"MwEnvMapTint"', '\n\t\t{', '\n\t\t\t"min" "0"', '\n\t\t\t"max" "0.015"', '\n\t\t}', '\n\t}']
    writer = ['// Generated by FastValveMaterial v'+ version,
    '\n// NORMALIZED MATERIAL!'
    '\n"VertexLitGeneric"',
    '\n{', 
    '\n\t"$basetexture" "' + config_output_path + mName + '_c"',
    '\n\t"$bumpmap" "' + config_output_path + mName + '_n"',
    '\n\t"$phongexponenttexture" "' + config_output_path + mName + '_m"',
    '\n\t"$phong" "1"',
    '\n\t"$phongboost" "1"',
    '\n\t"$color2" "[ 0 0 0 ]"',
    '\n\t"$phongexponent"    "24"',
    '\n\t"$phongalbedotint" "1"',
    '\n\t"$additive"    "1"',
    '\n\t"$PhongFresnelRanges" "[ 2 4 6 ]"']
    proxies += '\n}'
    writer += proxies

    try:
        Path("materials/").mkdir(parents=True, exist_ok=True)
        f = open(mName + "_s.vmt", 'w')
        f.writelines(writer)
        f.close()
        shutil.move(mName+'_s.vmt', "materials/")
    except Exception as e:
        debug("Normalized material already exists, replacing!")
        shutil.copyfile(os.path.join(os.getcwd(), mName+"_s.vmt"), os.path.join(os.getcwd(), config_output_path+mName+"_s.vmt"), follow_symlinks=True)
        os.remove(os.path.join(os.getcwd(), mName+"_s.vmt"))

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
# * Main loop
# /////////////////////
for name in find_material_names(): # For every material in the input folder
    debug("Loading:")
    try:
        debug("Material:\t"+ name)
        # Set the paths to the textures based on the config file
        if(config_orm):
            colorSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[0] + "." + config_input_format))
            aoSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[3] + "." + config_input_format))
            normalSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[2] + "." + config_input_format))
            metalSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[3] + "." + config_input_format))
            glossSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[3] + "." + config_input_format))
        else:
            colorSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[0] + "." + config_input_format))
            if config_input_name_scheme[1] != '': # If a map is set
                aoSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[1] + "." + config_input_format))
            if config_input_name_scheme[2] != '':
                normalSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[2] + "." + config_input_format))
            if config_input_name_scheme[3] != '':
                glossSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[3] + "." + config_input_format))
            if config_input_name_scheme[4] != '':
                metalSt = config_path + "/" + str(check_for_valid_files(config_path, name, config_input_name_scheme[4] + "." + config_input_format))

    except FileNotFoundError:
        debug("[ERROR] v"+version+" terminated with exit code -1:\nCouldn't locate files with correct naming scheme, throwing FileNotFoundError!")
        sys.exit()

    if(config_orm == False):
        print("Color:\t\t" +colorSt)

        if config_input_name_scheme[1] != '':
            print("Occlusion:\t" +aoSt)
        else:
            print("Occlusion:\t" +"None given, ignoring!")
            
        if config_input_name_scheme[2] != '':
            print("Normal:\t\t" +normalSt)
        else:
            print("Normal:\t\t" +"None given, ignoring!")

        if config_input_name_scheme[3] != '':
            print("Metalness:\t" +metalSt)
        else:
            print("Metalness:\t" +"None given, ignoring!")
            
        if config_input_name_scheme[4] != '':
            print("Glossiness:\t" +glossSt + "\n")
        else:
            print("Glossiness:\t" +"None given, ignoring!\n")

        colorImage = Image.open(colorSt)

        if config_input_name_scheme[1] != '':
            aoImage = Image.open(aoSt)
        else:
            aoImage = Image.new('RGB', (colorImage.width, colorImage.height), (255,255,255)) # If no AO image is given, use a white image

        if config_input_name_scheme[2] != '':
            normalImage = Image.open(normalSt)
        else:
            raise FileNotFoundError() # Couldn't find a normal map

        if config_input_name_scheme[3] != '':
            metalImage = Image.open(metalSt)
        else:
            metalImage = Image.new('RGB', (colorImage.width, colorImage.height), (0,0,0)) # If no Metalness image is given, use a black image

        if config_input_name_scheme[4] != '':
            glossImage = Image.open(glossSt)
        else:
            glossImage = Image.new('RGB', (colorImage.width, colorImage.height), (255,255,255)) # If no Gloss image is given, use a white image

        if config_material_setup == "rough":
            glossImage = ImageOps.invert(glossImage.convert('RGB'))
        aoImage = fix_scale_mismatch(normalImage, aoImage)
        metalImage = fix_scale_mismatch(normalImage, metalImage)
        colorImage = fix_scale_mismatch(normalImage, colorImage)
        glossImage = fix_scale_mismatch(normalImage, glossImage)

        if config_input_name_scheme[1] != '':
            do_diffuse(colorImage, aoImage, metalImage, glossImage)
        else:
            do_diffuse(colorImage, None, metalImage, glossImage)

        do_exponent(glossImage)
        do_normal(config_midtone, normalImage, glossImage)

        if(config_clear_exponent):
            do_nrm_material(name)
        else:
            do_material(name)
    else:
        print("Color:\t\t" +colorSt)
        print("ORM:\t\t" +metalSt)
        print("Normal:\t\t" +normalSt + "\n")

        colorImage = Image.open(colorSt)
        ormImage = Image.open(metalSt)
        try:    
            (r,g,b) = ormImage.split()
        except:
            print("ERROR: Could not convert color bands on ORM! (Do you have empty image channels?)")
        aoImage = r
        glossImage = ImageOps.invert(g.convert('RGB'))
        metalImage = b
        normalImage = Image.open(normalSt)
        do_diffuse(colorImage, aoImage, metalImage, glossImage)
        do_exponent(glossImage)
        do_normal(config_midtone, normalImage, glossImage)

        if(config_clear_exponent):
            do_nrm_material(name)
        else:
            do_material(name)

    print("[FVM] Conversion for material '" + name + "' finished, files saved to '" + config_output_path + "'\n")

debug("v"+version+" finished with exit code 0: All conversions finished.")
if(config_print_config):
    debug("Config file dump:")
    debug(config)

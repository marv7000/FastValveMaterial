from PIL import Image, ImageChops, ImageOps
import time
import os
import sys
import math
from VTFLibWrapper.VTFLibEnums import ImageFlag
import VTFLibWrapper.VTFLib as VTFLib
import VTFLibWrapper.VTFLibEnums as VTFLibEnums
import numpy as np
from ctypes import create_string_buffer
from pathlib import Path
import shutil
from pathlib import Path

vtf_lib = VTFLib.VTFLib()

print("FastValveMaterial (v1129)\n")
print("Usage: Add textures to a subfolder and group textures together for every material you want to create.")

def get_file(path, name, ending):
    for file in os.listdir(path):
        if file.endswith(ending) and file.startswith(name):
            return file

def find_unique_names():
    listStuff = []
    for file in os.listdir(path):
        if file.endswith("g.tga"):
            listStuff.append(file.replace("_g.tga", ""))

    return listStuff


def do_diffuse(cIm, aoIm):
    final_diffuse = ImageChops.multiply(cIm, aoIm)
    r,g,b,a = final_diffuse.split()
    a = a.convert('RGBA')
    a = Image.blend(a, metalImage, 1)
    a = a.convert('L')
    color_spc = (r,g,b,a)
    final_diffuse = Image.merge("RGBA", color_spc)
    export_texture(final_diffuse, (gunName+'_c.vtf'), 'DXT5')
    Path(outPath).mkdir(parents=True, exist_ok=True)
    shutil.move(gunName+'_c.vtf', os.path.join(os.getcwd(), outPath))
    #final_diffuse.save((material_name + '_color.tga'), 'TGA' )
    print("[FVM] Diffuse exported")

def do_exponent(gIm):
    finalExponent = gIm
    r,g,b,a = finalExponent.split()
    layerImage = Image.new('RGBA', [finalExponent.size[0], finalExponent.size[1]], (0, 217, 0, 100))
    blackImage = Image.new('RGBA', [finalExponent.size[0], finalExponent.size[1]], (0, 0, 0, 100))
    finalExponent = Image.blend(finalExponent, layerImage, 0.5)
    #colorSpc = (r,g,b,a)
    #finalExponent = Image.merge('RGBA', colorSpc)
    #r,g,b,a = finalExponent.split()
    g = g.convert('RGBA')
    b = b.convert('RGBA')
    g = Image.blend(g, layerImage, 1)
    b = Image.blend(b, blackImage, 1)
    
    g = g.convert('L')
    b = b.convert('L')
    colorSpc = (r,g,b,a)
    finalExponent = Image.merge('RGBA', colorSpc)
    export_texture(finalExponent, (gunName+'_m.vtf'), 'DXT1')
    Path(outPath).mkdir(parents=True, exist_ok=True)
    shutil.move(gunName+'_m.vtf', outPath)
    #finalExponent.save( (gunName + '_m.tga'), 'TGA' )
    print("[FVM] Exponent exported")

def do_normal(mt, nIm, gIm):
    finalNormal = nIm
    finalGloss = gIm
    row = finalGloss.size[0]
    col = finalGloss.size[1]
    gamma = 1
    for x in range(1 , row):
        print("(", math.ceil(x/row*100),"%)", end="\r")
        for y in range(1, col):
            value = do_gamma(x,y,finalGloss, mt)
            finalGloss.putpixel((x,y), value)

    r,g,b,a = finalNormal.split()
    finalGloss = finalGloss.convert('L')
    a = Image.blend(a, finalGloss, 1)
    a = a.convert('L')
    colorSpc = (r,g,b,a)
    finalNormal = Image.merge('RGBA', colorSpc)
    #finalNormal.save((gunName+'_n.tga'), 'TGA')
    export_texture(finalNormal, (gunName+'_n.vtf'), 'RGBA8888')
    Path(outPath).mkdir(parents=True, exist_ok=True)
    shutil.move(gunName+'_n.vtf', outPath)
    print("[FVM] Normal exported")

def do_gamma(x, y, im, mt):
    gamma = 1
    midTones = mt
    midToneNormal = midTones / 255
    if midTones < 128:
        midToneNormal = midToneNormal * 2
        gamma = 1 + (9*(1-midToneNormal))
        gamma = min(gamma, 9.99)
    elif midTones > 128:
        midToneNormal = (midToneNormal * 2) - 1
        gamma = 1 - midToneNormal
        gamma = max(gamma, 0.01)

    gamma_correction = 1/gamma
    (r,g,b,a) = im.getpixel((x,y))
    r = 255 *  ( (r - 0 ) / ( 255 - 0 ) )
    g = 255 *  ( (g - 0 ) / ( 255 - 0 ) )
    b = 255 *  ( (b - 0 ) / ( 255 - 0 ) )
    if midTones != 128:
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

def do_material(mName):
    print("[FVM] Creating material '"+ mName + "'")
    f = open(mName + ".vmt", 'w')
    writer = ('"VertexLitGeneric"',
    '\n{', 
    '\n\t$basetexture ' + outPath + mName + "_c",
    '\n\t$bumpmap ' + outPath + mName + "_n",
    '\n\t$phongexponenttexture ' + outPath + mName + "_m",
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
    f.writelines(writer)

def export_texture(texture, path, imageFormat=None):
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

path = input("[FVM] Enter local search path (e.g. images): ")
outPath = input("[FVM] Enter subfolder path (e.g. export/materials/): ")
mt = int(input("[FVM] Enter midtone value (e.g. 215): "))
for name in find_unique_names():
    material_name = "export"
    print("[FVM] Loading:")
    try:
        gunName = name
        print(gunName)
        colorSt = path + "/" + str(get_file(path, name, "rgb.tga"))
        if colorSt == path + "/None":
            colorSt = path + "/" + str(get_file(path, name, "c.tga"))
        aoSt = path + "/" + str(get_file(path, name, "o.tga"))
        metalSt = path + "/" + str(get_file(path, name, "alpha.tga"))
        if metalSt == path + "/None":
            metalSt = path + "/" + str(get_file(path, name, "s.tga"))
        normalSt = path + "/" + str(get_file(path, name, "n.tga"))
        glossSt = path + "/" + str(get_file(path, name, "g.tga"))
    except FileNotFoundError:
        input("[FVM] [ERROR] Couldn't locate files with correct naming scheme (23)")
        sys.exit()

    print(colorSt)
    print(aoSt)
    print(metalSt)
    print(normalSt)
    print(glossSt)
    print("-----------\n")
    colorImage = Image.open(colorSt)
    aoImage = Image.open(aoSt)
    metalImage = Image.open(metalSt)
    normalImage = Image.open(normalSt)
    glossImage = Image.open(glossSt)

    aoImage = fix_scale_mismatch(colorImage, aoImage)
    metalImage = fix_scale_mismatch(colorImage, metalImage)
    normalImage = fix_scale_mismatch(colorImage, normalImage)
    glossImage = fix_scale_mismatch(colorImage, glossImage)

    do_diffuse(colorImage, aoImage)
    do_exponent(glossImage)
    do_normal(mt, normalImage, glossImage)
    do_material(gunName)
    print("[FVM] Conversion finished")
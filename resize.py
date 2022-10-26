import VTFLibWrapper.VTFLib as VTFLib
import VTFLibWrapper.VTFLibEnums as VTFLibEnums
import os

vtf_lib = VTFLib.VTFLib()

for file in os.listdir():
    if vtf_lib.image_load(file): # if is vtf
        print(file)
import sys
import os

# Get the parent directory and add it to the sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Standard packages
import numpy as np
import matplotlib.pyplot as plt
import spekpy
import astra
from src.specimen import create_obj
from src.scanning import create_projector, polychromatic_sinogram
from src.image_analysis import error_map

## X-ray source definitions yielding a polychromatic beam and a beam hardened sinogram
material = 'C'
target_material = 'W'
filter_material = 'Al'
beam = 'parallel'


# Change filter thickness to 0 no matter which filter and you cancel it
filter_thickness = 4E-3 #m
anode_angle = 12 #deg
acceleration_voltage = 80E3 #eV

# Other settings used in the lab
current = 667E-6 #A
exposure_time = 500E-3 #s
voxel_size = 132E-6 #m
n_angles_exp = 1570 #or 360


## SpekPy to generate the X-ray source Spectrum
spek_spectrum = spekpy.Spek(kvp = acceleration_voltage/1000, th  = anode_angle) # Create a spectrum, energy in keV
spek_spectrum.filter(filter_material, filter_thickness*1000) # Filter the spectrum, thickness in mm?
energy_spectrum, intensity_spectrum = spek_spectrum.get_spectrum(edges=True) # Get the spectrum



plt.plot(energy_spectrum, intensity_spectrum) # Plot the spectrum
plt.xlabel('Energy [keV]')
plt.ylabel('Fluence per mAs per unit energy [photons/cm2/mAs/keV]')
plt.title('X-ray source spectrum')
plt.show()



## Lab setup including detection volume, detector dimensions, sample dimensions
# Square detector
n_pixels = 200
dim = 2

n_pixels_x = n_pixels
n_pixels_y = n_pixels
if (dim == 2):
    n_pixels = n_pixels_x
    max_n_pixels = n_pixels_x
else:
    n_pixels = [n_pixels_x, n_pixels_y]
    max_n_pixels = max(n_pixels)

n_angles = round(max_n_pixels*np.pi/2)                    # Theoretical value for needed angles to create good reconstruction
proj_angles = np.linspace(-np.pi, np.pi, 2*n_angles)        # Angles of projection



## FROM
#
# d_source_obj + d_obj_det = n_pixels
# magnification = (d_source_obj + d_obj_det) / d_source_obj
#
# =>

magnification = 2
d_source_obj = max_n_pixels/magnification
d_obj_detector = max_n_pixels - d_source_obj



# Getting a circular object to test on
obj_dim = [n_pixels_x, n_pixels_y]
centers = [[120*n_pixels_x/200,145*n_pixels_y/200]]
shapes = ['circle']
radii = [40*n_pixels_x/200]

#obj = create_obj(obj_dim, centers, shapes, radii)

obj_dim_array = [obj_dim]
centers_array = [centers]
shapes_array = [shapes]
radii_array = [radii]
material_array = [material]


obj_dim = [n_pixels_x, n_pixels_y]
centers = [[120*n_pixels_x/200, 55*n_pixels_y/200]]
shapes = ['circle']
radii = [40*n_pixels_x/200]
material = 'Cu'

obj_dim_array.append(obj_dim)
centers_array.append(centers)
shapes_array.append(shapes)
radii_array.append(radii)
material_array.append(material)


obj_dim = [n_pixels_x, n_pixels_y]
centers = [[50,100]]
shapes = ['circle']
radii = [40]
material = 'Pb'

obj_dim_array.append(obj_dim)
centers_array.append(centers)
shapes_array.append(shapes)
radii_array.append(radii)
material_array.append(material)



obj_array = []
for i in range(len(obj_dim_array)):
    obj = create_obj(obj_dim_array[i], centers_array[i], shapes_array[i], radii_array[i])
    obj_array.append(obj)

# Removing overlap from the objects
obj_total = np.sum(obj_array, axis=0)
#obj_total[obj_total > 1] = 1
#for i in range(len(obj_dim_array) - 1):
#    obj_array[i + 1] = obj_total - obj_array[i]
#    plt.figure()
#    plt.imshow(obj_array[i+1])
#    plt.show()



proj_id_array = []
sinogram_id_array = []
sinogram_array = []
poly_sinogram_array = []

rec_id_array = []
rec_array = []
rec_harden_id_array = []
rec_harden_array = []


# create multiple objs with different attenuation
for i in range(len(obj_dim_array)):
    
    # Projection and sinogram
    proj_id = create_projector(obj_array[i], d_source_obj, d_obj_detector, n_pixels, proj_angles, beam)
    sinogram_id, sinogram = astra.create_sino(obj_array[i], proj_id)
    sinogram = np.transpose(sinogram)
    poly_sinogram = polychromatic_sinogram(sinogram, material_array[i], energy_spectrum, intensity_spectrum)
    print("converted sino to poly")
    
    proj_id_array.append(proj_id)
    sinogram_id_array.append(sinogram_id)
    sinogram_array.append(sinogram)
    poly_sinogram_array.append(poly_sinogram)
    
    ## 2D Reconstruction
    [rec_id, rec] = astra.creators.create_reconstruction("FBP", proj_id_array[i], np.transpose(sinogram_array[i]))
    rec_id_array.append(rec_id)
    rec_array.append(rec)

    ## 2D Reconstruction of Beam Hardened
    [rec_harden_id, rec_harden] = astra.creators.create_reconstruction("FBP", proj_id_array[i], np.transpose(poly_sinogram_array[i]) )
    rec_harden_id_array.append(rec_harden_id)
    rec_harden_array.append(rec_harden)



# Projection and sinogram FOR JUST A SINGLE OBJ MASKING
#proj_id = create_projector(obj, d_source_obj, d_obj_det, n_pixels_x, n_pixels_y, dim, proj_angles, beam)
#sinogram_id, sinogram = astra.create_sino(obj, proj_id)
#sinogram = np.transpose(sinogram)
#poly_sinogram = polychromatic_sinogram(sinogram, material, energy_spectrum, intensity_spectrum)
#print("converted sino to poly")


## Now to add them all together
obj_combined = np.sum(obj_array, axis=0)
#sinogram_combined = np.sum(sinogram_array, axis=0)
#poly_sinogram_combined = np.sum(poly_sinogram_array, axis=0)
poly_sinogram_combined = polychromatic_sinogram(sinogram_array, material_array, energy_spectrum, intensity_spectrum)
#rec_combined = np.sum(rec_array, axis=0)
rec_harden_combined = np.sum(rec_harden_array, axis=0)


plt.figure()
plt.imshow(poly_sinogram_combined)
plt.title("Polychromatic Beam Sinogram")
plt.colorbar()
plt.show()


## 2D Reconstruction of Beam Hardened
# Transposing the sinogram back to astras form
[rec_harden_id_final, rec_harden_final] = astra.creators.create_reconstruction("FBP", proj_id, np.transpose(poly_sinogram_combined) )

plt.figure()
plt.imshow(rec_harden_final)
plt.colorbar()
plt.title("BH Specimen Reconstruction")
plt.show()

plt.figure() 
plt.plot( rec_harden_final[ round( np.size( rec_harden_final,0 )/2 ),: ])
plt.title("BH Specimen Reconstruction: profile")
plt.show()

plt.figure()
plt.imshow(rec_harden_combined)
plt.colorbar()
plt.title("Combining BH Specimen after Reconstruction")
plt.show()

plt.figure() 
plt.plot( rec_harden_combined[ round( np.size( rec_harden_combined,0 )/2 ),: ])
plt.title("Combining BH Specimen after Reconstruction: profile")
plt.show()

rec_combined_error_map, rec_error_combined_euclidean_norm = error_map(rec_harden_combined, rec_harden_final)

plt.figure()
plt.imshow(rec_combined_error_map)
plt.title("Beam Hardening Artifacts")
plt.xlabel("Euclidean Norm (l2): " + str(rec_error_combined_euclidean_norm))
plt.colorbar()
plt.show()


rec_error_map, rec_error_euclidean_norm = error_map(rec_harden_combined, obj_combined)

plt.figure()
plt.imshow(rec_error_map)
plt.title("BH Specimen Reconstruction vs True Specimen")
plt.xlabel("Euclidean Norm (l2): " + str(rec_error_euclidean_norm))
plt.colorbar()
plt.show()
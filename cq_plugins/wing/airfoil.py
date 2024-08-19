from io import StringIO

import numpy as np
import matplotlib.pyplot as plt
import requests
from cadquery import cq
from scipy.interpolate import CubicSpline
import unittest
import urllib3
import shapely.geometry as shp

def read_airfoil_file(file_path):
    if urllib3.util.parse_url(file_path).scheme is not None:
        afpts = np.loadtxt(StringIO(str(requests.get(file_path).content, encoding='utf-8')), skiprows=1)
    else:
        afpts = np.loadtxt(file_path, skiprows=1)
    return [(p[0], p[1]) for p in afpts]

def scale_points(points, scale):
    return [(p[0] * scale, p[1] * scale) for p in points]

def reparameterize_airfoil(airfoil_data, M):
    amin = np.argmin([p[0] for p in airfoil_data])
    afpoly_upper = shp.LineString(airfoil_data[:amin+1])
    afpoly_lower = shp.LineString(airfoil_data[amin:])

    upper = [ afpoly_upper.interpolate(t, True) for t in np.linspace(1., 0., int(np.ceil(M/2)), True)]
    _upper = sorted(upper, key=lambda p: p.x)
    lower = [ afpoly_lower.interpolate(t, True) for t in np.linspace(0., 1., int(np.floor(M/2 + 1)), False)]
    _lower = sorted(lower, key=lambda p: p.x)
    complete = list(reversed(_upper)) + _lower[1:]
    return [ (p.x, p.y) for p in complete]

def plot_airfoil(original_points, scaled_points, offset_points, normals, scaled_normals):
    original_points = np.array(original_points)
    scaled_points = np.array(scaled_points)
    offset_points = np.array(offset_points)
    normals = np.array(normals)
    scaled_normals = np.array(scaled_normals) if scaled_normals is not None else None

    fig, axs = plt.subplots(2, 1, figsize=(40, 10))

    axs[0].plot(original_points[:, 0], original_points[:, 1], 'bo-', label="Original Airfoil", markersize=5)
    #axs[0].plot(offset_points[:, 0], offset_points[:, 1], 'r*-', label="Offset Airfoil", markersize=4)
    #axs[0].quiver(original_points[:, 0], original_points[:, 1],
    #              -normals[:, 0]*0.1, -normals[:, 1]*0.1,
    #              angles='xy', scale_units='xy', scale=1, color='g', label="Normals")
    axs[0].set_aspect('equal', adjustable='box')
    axs[0].legend(loc='center left', bbox_to_anchor=(1, 0.5))
    axs[0].set_xlabel("x")
    axs[0].set_ylabel("y")
    axs[0].set_title("Airfoil Comparison with Normals")
    axs[0].grid(True)

    axs[1].plot(scaled_points[:, 0], scaled_points[:, 1], 'bo-', label="Scaled Original Airfoil", markersize=5)
    axs[1].plot(offset_points[:, 0], offset_points[:, 1], 'r*-', label="Scaled Offset Airfoil", markersize=5)
    if scaled_normals is not None:
        axs[1].quiver(scaled_points[:, 0], scaled_points[:, 1],
                      -scaled_normals[:, 0]*10, -scaled_normals[:, 1]*10,
                      angles='xy', scale_units='xy', scale=1, color='g', label="Normals")
    axs[1].set_aspect('equal', adjustable='box')
    axs[1].legend(loc='center left', bbox_to_anchor=(1, 0.5))
    axs[1].set_xlabel("x (scaled)")
    axs[1].set_ylabel("y (scaled)")
    axs[1].set_title("Scaled Airfoil Comparison with Normals")
    axs[1].grid(True)

    plt.tight_layout()
    plt.show()

def airfoil(self: cq.Workplane, selig_file: str, chord: float, offset: float = 0, number_interpolation_points: int = None,
            forConstruction: bool = False):

    af_point_list = read_airfoil_file(selig_file)
    point_list = af_point_list
    scaled_points = scale_points(point_list, chord)

    if offset != 0:
        scaled_points = offset_airfoil(chord, offset, point_list)

    if number_interpolation_points is not None:
        scaled_points = reparameterize_airfoil(scaled_points, number_interpolation_points)

    #plot_airfoil(af_point_list, scale_points(point_list, chord), scaled_points, None, None)

    plane = self.plane
    new_plane = cq.Plane(xDir=plane.xDir, origin=(0, 0, 0), normal=plane.zDir)
    shape = (cq.Workplane(inPlane=new_plane)
             .splineApprox(points=scaled_points,
                           forConstruction=forConstruction,
                           tol=1e-4).close()
             .val())
    trans_shape = shape.translate(plane.origin)

    return self.newObject([trans_shape])


def offset_airfoil(chord, offset, point_list):
    afpoly = shp.Polygon(point_list)
    noffafpoly = afpoly.buffer(distance=-offset / chord)
    offset_points = (list(noffafpoly.exterior.coords))
    scaled_points = scale_points(offset_points, chord)
    amax = np.argmax([p[0] for p in scaled_points])
    if amax != 0:
        scaled_points = scaled_points[amax:] + scaled_points[:amax]
    return scaled_points


class TestAirfoilFunctions(unittest.TestCase):
    def setUp(self):
        self.chord = 185.0
        self.offset = 0.5  # Increase offset to 0.5
        self.number_interpolation_points = 200

    def test_chord_length(self):
        rg15_data = read_airfoil_file("../../components/airfoils/rg15.dat")
        naca2415_data = read_airfoil_file("../../components/airfoils/naca2415.dat")
        n63215_data = read_airfoil_file("../../components/airfoils/n63215.dat")
        for airfoil_data in [rg15_data, naca2415_data, n63215_data]:
            scaled_points = scale_points(airfoil_data, self.chord)
            max_x = max(point[0] for point in scaled_points)
            self.assertAlmostEqual(max_x, self.chord, places=6, msg=f"Expected chord length: {self.chord}, but got: {max_x}")

    def test_offset(self):
        rg15_data = read_airfoil_file("../../components/airfoils/rg15.dat")
        naca2415_data = read_airfoil_file("../../components/airfoils/naca2415.dat")
        n63215_data = read_airfoil_file("../../components/airfoils/n63215.dat")
        for airfoil_data in [rg15_data, naca2415_data, n63215_data]:
            scaled_points = scale_points(airfoil_data, self.chord)
            offset_points = offset_airfoil(self.chord, self.offset, airfoil_data)

            for orig, offset in zip(scaled_points, offset_points):
                dist = np.sqrt((orig[0] - offset[0]) ** 2 + (orig[1] - offset[1]) ** 2)
                self.assertAlmostEqual(dist, self.offset, delta=self.offset * 1e-3, msg=f"Expected offset: {self.offset}, but got: {dist}")


if __name__ == "__main__":
    # Load the data from the provided files
    rg15_data = read_airfoil_file("../../components/airfoils/rg15.dat")
    naca2415_data = read_airfoil_file("../../components/airfoils/naca2415.dat")
    n63215_data = read_airfoil_file("../../components/airfoils/n63215.dat")

    wp = cq.Workplane()
    airf = airfoil(wp,
                   selig_file="../../components/airfoils/rg15.dat",
                         chord=185,
                         offset=0.42,
                         number_interpolation_points = 201,
                         forConstruction= True)
    # Run the tests
    #unittest.main(argv=['first-arg-is-ignored'], exit=False)

    chord = 185
    # Visualize the airfoil with the increased offset using rg15 data
    original_points = rg15_data
    reparameterized_points = reparameterize_airfoil(original_points, M=201)

    # Create a Polygon from the nx2 array in `afpts`
    afpoly = shp.Polygon(reparameterized_points)
    noffafpoly = afpoly.buffer(-3.42/chord)  # Inward offset
    offset_points = list(noffafpoly.exterior.coords)

    normals = calculate_normals(reparameterized_points)

    scaled_points = scale_points(reparameterized_points, chord)
    scaled_normals = calculate_normals(scaled_points)

    #offset_points = apply_offset(reparameterized_points, normals, 0.42/chord)
    #offset_points = repair_offset_profile(offset_points, reparameterized_points)
    scaled_offset_points = scale_points(offset_points, chord)


    plot_airfoil(original_points, scaled_points, scaled_offset_points, normals, scaled_normals)

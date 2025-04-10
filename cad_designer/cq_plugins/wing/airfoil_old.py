import cadquery as cq
import numpy as np
from matplotlib import pyplot as plt

from scipy.interpolate import CubicSpline

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

def _reparameterize_airfoil(airfoil_data, M):
    airfoil_array = np.array(airfoil_data)

    # Calculate normals
    dx = np.gradient(airfoil_array[:, 0])
    dy = np.gradient(airfoil_array[:, 1])
    normals_x = -dy
    normals_y = dx
    magnitudes = np.sqrt(normals_x ** 2 + normals_y ** 2)
    normals_x /= magnitudes
    normals_y /= magnitudes

    # Calculate curvature by measuring the angle between adjacent normals
    angles = np.arccos(normals_x[:-1] * normals_x[1:] + normals_y[:-1] * normals_y[1:])
    curvatures = np.abs(angles)

    # Threshold for high curvature
    threshold = np.percentile(curvatures, 90)  # Top 10% curvatures

    new_points = []
    for i in range(len(airfoil_data) - 1):
        new_points.append(airfoil_data[i])
        if curvatures[i] > threshold:
            # Interpolate additional points in high curvature regions
            mid_point = (
            (airfoil_data[i][0] + airfoil_data[i + 1][0]) / 2, (airfoil_data[i][1] + airfoil_data[i + 1][1]) / 2)
            new_points.append(mid_point)

    new_points.append(airfoil_data[-1])

    return new_points

def reparameterize_airfoil(airfoil_data, M):
    """
    Reparameterize the airfoil data to generate M points.

    Args:
    - airfoil_data (list of tuples): List of (x, y) coordinates representing the airfoil profile.
    - M (int): Number of points to generate.

    Returns:
    - reparameterized_airfoil_data (list of tuples): List of (x, y) coordinates representing the reparameterized airfoil profile.
    """

    # Convert airfoil data to numpy array for easier manipulation
    airfoil_array = np.array(airfoil_data)

    # Separate x and y coordinates
    x = airfoil_array[:, 0]
    y = airfoil_array[:, 1]

    # Compute the cumulative chord length along the airfoil
    chord_lengths = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
    cumulative_lengths = np.concatenate(([0], np.cumsum(chord_lengths)))

    # Create a cubic spline interpolator for the cumulative lengths
    spline_interpolator = CubicSpline(cumulative_lengths, airfoil_array, axis=0)

    # Generate M equidistant points along the cumulative chord length
    new_cumulative_lengths = np.linspace(0, cumulative_lengths[-1], M)

    # Interpolate the airfoil coordinates at these new cumulative lengths
    reparameterized_airfoil_data = spline_interpolator(new_cumulative_lengths)

    return reparameterized_airfoil_data

def airfoil(self: cq.Workplane, selig_file: str, chord: float, offset: float = 0, number_interpolation_points: int = None,
            forConstruction: bool = False):
    file = open(selig_file, "r")
    point_list = []
    for line_num, line in enumerate(file):
        line: str = line
        if line_num < 1:
            pass
        else:
            tokens = [n for n in line.strip().split(" ") if n != ""]
            tok_y = float(tokens[1])
            tok_x = float(tokens[0])
            point_list.append((tok_x, tok_y))

    af_point_list = point_list

    if number_interpolation_points is not None:
        point_list = reparameterize_airfoil(point_list, number_interpolation_points)

    scaled_point_list = [(p[0] * chord, p[1] * chord) for p in point_list]

    if offset != 0:
        # Convert airfoil data to numpy array for easier manipulation
        airfoil_array = np.array(point_list)

        # Calculate the normals at each point using central differences
        dx = np.gradient(airfoil_array[:, 0])
        dy = np.gradient(airfoil_array[:, 1])
        normals_x = -dy
        normals_y = dx

        # Normalize normals
        magnitudes = np.sqrt(normals_x ** 2 + normals_y ** 2)
        normals_x /= magnitudes
        normals_y /= magnitudes

        # Offset points along the normals
        offset_x = (airfoil_array[:, 0] + offset / chord * normals_x) * chord
        offset_y = (airfoil_array[:, 1] + offset / chord * normals_y) * chord

        offset_point_list = list(zip(offset_x, offset_y))

        ## remove the crossing at the wings tail edge
        # 1. simple solution
        offset_point_list_copy = offset_point_list.copy()
        for i in range(len(offset_point_list)):
            if offset_point_list[i][1] <= offset_point_list[-i - 1][1]:
                del offset_point_list_copy[0]
                del offset_point_list_copy[-1]
            else:
                break

        plot_airfoil(af_point_list, scaled_point_list, offset_point_list_copy, None, None)

    file.close()
    plane = self.plane
    new_plane = cq.Plane(xDir=plane.xDir, origin=(0, 0, 0), normal=plane.zDir)
    shape = (cq.Workplane(inPlane=new_plane)
             .splineApprox(points=scaled_point_list if offset == 0 else offset_point_list_copy,
                           forConstruction=forConstruction,
                           tol=1e-4).close()
             .val())
    trans_shape = shape.translate(plane.origin)

    return self.newObject([trans_shape])


import cadquery as cq
import numpy as np

from scipy.interpolate import CubicSpline


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

    if number_interpolation_points is not None:
        point_list = reparameterize_airfoil(point_list, number_interpolation_points)

    if offset == 0:
        scaled_point_list = [(p[0] * chord, p[1] * chord) for p in point_list]
    else:
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


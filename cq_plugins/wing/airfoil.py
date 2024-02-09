import cadquery as cq
import numpy as np
from numpy.linalg import norm

def airfoil(self: cq.Workplane, selig_file: str, chord: float, offset: float = 0, forConstruction: bool = False):
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

    if offset == 0:
        scaled_point_list = [(p[0] * chord, p[1] * chord) for p in point_list]
    else:

        points = [(point_list[i - 1], point_list[i], point_list[(i + 1) % len(point_list)]) for i in range(len(point_list))]

        # (norm((np.array(p[0]) - np.array(p[1]))) * (np.array(p[2]) - np.array(p[1])) + norm((np.array(p[2]) - np.array(p[1]))) * (np.array(p[0]) - np.array(p[1]))) / (norm((np.array(p[2]) - np.array(p[1]))) + norm((np.array(p[0]) - np.array(p[1]))))
        # a = (np.array(p[2]) - np.array(p[1]))
        # b = (np.array(p[0]) - np.array(p[1]))
        correction_vecs = [  (norm((np.array(p[0]) - np.array(p[1]))) * (np.array(p[2]) - np.array(p[1])) + norm((np.array(p[2]) - np.array(p[1]))) * (np.array(p[0]) - np.array(p[1]))) / (norm((np.array(p[2]) - np.array(p[1]))) + norm((np.array(p[0]) - np.array(p[1])))) for p in points]
        correction_vecs_norm = [cv / norm(cv) for cv in correction_vecs]
        correction_vecs_norm_tup = [ (cv[0], cv[1]) for cv in correction_vecs_norm]

        offset_point_list = [(point_list[i][0] * chord + offset * correction_vecs_norm_tup[i][0],
          point_list[i][1] * chord + offset * correction_vecs_norm_tup[i][1]) for i in range(len(point_list))]

        ## remove the crossing at the wings tail edge
        # 1. simple solution
        offset_point_list_copy = offset_point_list.copy()
        for i in range(len(offset_point_list)):
            if offset_point_list[i][1] <= offset_point_list[-i-1][1]:
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
                           tol=1e-3).close()
             .val())
    trans_shape = shape.translate(plane.origin)

    return self.newObject([trans_shape]).toPending()


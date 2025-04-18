import logging
from typing import Any, Tuple

import numpy as np
from aerosandbox.geometry.wing import Wing, WingXSec
from aerosandbox.geometry.airplane import Airplane

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from pathlib import Path

def asb_mesh_to_stl(
    data: Tuple[np.ndarray, np.ndarray],
    output_path: str,
    scale: float = 1.0,
    correct_normals: bool = True
) -> str:
    vertices, triangles = data
    vertices = vertices * scale
    center = vertices.mean(axis=0)

    def compute_normal(v1: np.ndarray, v2: np.ndarray, v3: np.ndarray) -> np.ndarray:
        normal = np.cross(v2 - v1, v3 - v1)
        norm = np.linalg.norm(normal)
        return normal / norm if norm != 0 else np.array([0.0, 0.0, 0.0])

    stl_lines = ["solid triangle_mesh"]

    for tri in triangles:
        v1, v2, v3 = (vertices[i] for i in tri)
        normal = compute_normal(v1, v2, v3)
        centroid = (v1 + v2 + v3) / 3
        direction = centroid - center

        # Flip normal if it's pointing inward
        if correct_normals and np.dot(normal, direction) < 0:
            v2, v3 = v3, v2  # flip winding
            normal = compute_normal(v1, v2, v3)

        stl_lines.append(f"  facet normal {normal[0]} {normal[1]} {normal[2]}")
        stl_lines.append("    outer loop")
        stl_lines.append(f"      vertex {v1[0]} {v1[1]} {v1[2]}")
        stl_lines.append(f"      vertex {v2[0]} {v2[1]} {v2[2]}")
        stl_lines.append(f"      vertex {v3[0]} {v3[1]} {v3[2]}")
        stl_lines.append("    endloop")
        stl_lines.append("  endfacet")

    stl_lines.append("endsolid triangle_mesh")

    stl_str = "\n".join(stl_lines)
    Path(output_path).write_text(stl_str)
    logging.info(f"STL written to {output_path} with scale {scale}, normals corrected: {correct_normals}")
    return stl_str

def export_wing_to_stl(wing: Wing, filepath: str | Path = "wing_model.step") -> None:
    airplane = Airplane(
        name="ConvertedWing",
        wings=[wing]
    )

    stl = asb_mesh_to_stl(
        wing.mesh_body(method='tri'),
        output_path=filepath,
        scale=0.1)

    # Generate the CAD model
    #cad = airplane.draw(backend="plotly", show=False)

    # Export to STEP file
    #cad.write_fig(filepath)
    #cad.show()
    print(f"✅ STEP export complete: {filepath}")
#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

import logging

import OCP.Geom as OGeom
import OCP.TopoDS as OTopo
from OCP.BRep import BRep_Tool_Surface
from OCP.BRepOffsetAPI import (BRepOffsetAPI_MakeThickSolid)
from OCP.Geom import Geom_Plane
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopTools import TopTools_ListOfShape
from OCP.TopoDS import (topods)
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
import tigl3.geometry as TGeo


class ShellCreator:
    def __init__(self, named_shape):
        self.m = ConstructionStepsViewer.instance()
        self.named_shape = named_shape

    def face_is_plane(self, face):

        # Returns True if the TopoDS_Shape is a plane, False otherwise
        hs: OGeom.Geom_Surface = BRep_Tool_Surface(face)
        downcast_result = OGeom.Geom_Plane.DownCast(hs)
        print(type(downcast_result))

        if downcast_result is None:
            return False
        else:
            return True

    def geom_plane_from_face(self, aFace):

        # Returns the geometric plane entity from a planar surface
        return Geom_Plane.DownCast(BRep_Tool_Surface(aFace))

    def create_shell(self, thickness, achs="Y", end="min"):
        # Our goal is to find the highest Z face and remove it
        logging.debug(f"Creating Shell with {thickness} and removing Face on the {end=} of {achs=}")
        faceToRemove = None
        if end == "min":
            var_min = 10
        else:
            var_max = -10

        # We have to work our way through all the faces to find the highest Z face so we can remove it for the shell
        a_face_explorer = TopExp_Explorer(self.named_shape.shape(), TopAbs_FACE)
        while a_face_explorer.More():
            a_face: OTopo.TopoDS_Face = topods.Face(a_face_explorer.Current())

            if self.face_is_plane(a_face):
                aPlane = self.geom_plane_from_face(a_face)

                # We want the highest Z face, so compare this to the previous faces
                aPnt = aPlane.Location()
                if achs == "X":
                    a_coordinate = aPnt.X()
                elif achs == "Z":
                    a_coordinate = aPnt.Z()
                else:
                    a_coordinate = aPnt.Y()

                logging.debug(f"{a_coordinate=}")
                if end == "min":
                    if a_coordinate < var_min:
                        var_min = a_coordinate
                        faceToRemove = a_face
                else:
                    var_max = -10
                    if a_coordinate > var_max:
                        var_max = a_coordinate
                        faceToRemove = a_face

            a_face_explorer.Next()

        faces_to_remove: TopTools_ListOfShape = TopTools_ListOfShape()
        faces_to_remove.Append(faceToRemove)
        logging.debug(f"Removing  {str(faces_to_remove.Size())} faces")
        make_thick_solid = BRepOffsetAPI_MakeThickSolid(self.named_shape.shape(), faces_to_remove, thickness, 0.0001)

        if not make_thick_solid.IsDone():
            logging.error(f"Shelling did not work")

        new_shell: TGeo.CNamedShape = TGeo.CNamedShape(make_thick_solid.Shape(), f"{self.named_shape.name} Shell")
        self.m.display_this_shape(new_shell, severity=logging.NOTSET)

        return new_shell

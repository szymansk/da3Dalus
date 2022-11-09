#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

import logging

import OCC.Core.Geom as OGeom
import OCC.Core.TopoDS as OTopo
from OCC.Core.BRep import BRep_Tool_Surface
from OCC.Core.BRepOffsetAPI import (BRepOffsetAPI_MakeThickSolid)
from OCC.Core.Geom import Geom_Plane
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.TopoDS import (topods)
from Extra.mydisplay import myDisplay


class ShellCreator:
    def __init__(self, shape):
        self.m = myDisplay.instance()
        self.shape = shape

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
        logging.info(f"Creating Shell with {thickness} and removing Face on the {end=} of {achs=}")
        faceToRemove = None
        if end == "min":
            var_min = 10
        else:
            var_max = -10

        # We have to work our way through all the faces to find the highest Z face so we can remove it for the shell
        a_face_explorer = TopExp_Explorer(self.shape, TopAbs_FACE)
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

                logging.info(f"{a_coordinate=}")
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
        logging.info(f"Removing  {str(faces_to_remove.Size())} faces")
        make_thick_solid = BRepOffsetAPI_MakeThickSolid(self.shape, faces_to_remove, thickness, 0.0001)

        if not make_thick_solid.IsDone():
            logging.error(f"Shelling did not work")

        new_shell = make_thick_solid.Shape()
        self.m.display_this_shape(new_shell)

        return new_shell

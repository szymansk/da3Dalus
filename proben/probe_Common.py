import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo

from Extra.ConstructionStepsViewer import ConstructionStepsViewer

if __name__ == "__main__":
    m = ConstructionStepsViewer.instance(True, 12)

    point = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeSphere(2).Shape(), "point")
    point2 = point
    point2 = TGeo.CNamedShape(OExs.translate_shp(point2.shape(), Ogp.gp_Vec(0, 2, 1.5)), "point2")
    box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(10, 10, 10).Shape(), "box")
    common_sphere = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Common(point.shape(), point2.shape()).Shape(), "Commn_spehe")

    # list_tu_cut = [point, point2]
    m.display_in_origin(point, "", True)
    m.display_in_origin(point2, "", True)
    m.display_in_origin(common_sphere, "")
    # m.display_in_origin(box, True)

    m.start()

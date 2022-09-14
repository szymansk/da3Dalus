from re import M
from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories

import OCC.Core.BRep as OBrep
import OCC.Core.Bnd as OBnd
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Extend.ShapeFactory as OExs
from Ausgabeservice import *
from Wand_erstellen import *
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape

from abmasse import get_dimensions, get_koordinates
from mydisplay import myDisplay
from shape_verschieben import rotate_shape
from shapeslicer.ShapeSlicer import ShapeSlicer

class aircombat_test:
    def __init__(self):
        self.m=myDisplay.instance()
        i_cpacs=5
        self.tixi_h = tixi3wrapper.Tixi3()

        self.tigl_handle = tigl3wrapper.Tigl3()
        if i_cpacs==1:
            self.tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
        if i_cpacs==2:
            self.tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
        if i_cpacs==3:
            self.tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml")
        if i_cpacs==5:
            self.tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
        if i_cpacs==4:
            self.tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinywing_skaliert.xml") 
        
        self.tigl_handle.open(self.tixi_h, "")
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(self.tigl_handle._handle.value)

    def rotate_shape(self,shape, axis, angle):
        """Rotate a shape around an axis, with a given angle.
        @param shape : the shape to rotate
        @point : the origin of the axis
        @vector : the axis direction
        @angle : the value of the rotation
        @return: the rotated shape.
        """
        #assert_shape_not_null(shape)
        #if unite == "deg":  # convert angle to radians
        angle = radians(angle)
        trns = Ogp.gp_Trsf()
        trns.SetRotation(axis, angle)
        brep_trns = OBui.BRepBuilderAPI_Transform(shape, trns, False)
        brep_trns.Build()
        shp = brep_trns.Shape()
        return shp

    def create_mainwing(self):
        self.wing: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(1)   
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.m.display_this_shape(self.wing_shape, "Right wing Shape")
        # Set up the mirror
        aTrsf= Ogp.gp_Trsf()
        aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
        transformed_wing = OBuilder.BRepBuilderAPI_Transform(self.wing_shape, aTrsf)
        mirrored_wing= transformed_wing.Shape()
        complete_wing= OAlgo.BRepAlgoAPI_Fuse(self.wing_shape,mirrored_wing).Shape()
        self.complete_wing=OExs.translate_shp(complete_wing,Ogp.gp_Vec(0,0, 2))
        self.m.display_this_shape(complete_wing,msg="Fused completewing")


    def create_fuselage(self):
        self.fuselage: TConfig.CCPACSFuselage= self.cpacs_configuration.get_fuselage(1)
        self.fuselage_loft: TGeo.CNamedShape= self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape=self.fuselage_loft.shape()
        #self.fuselage_shape=OExs.translate_shp(self.fuselage_shape,Ogp.gp_Vec(0,0,0.003))
        xmin, ymin, zmin, xmax,ymax,zmax= get_koordinates(self.fuselage_shape)
        self.fuselage_lenght, self.fuselage_widht, self.fuselage_height= get_dimensions(xmin, ymin, zmin, xmax,ymax,zmax)
        print("Fuselage Dimensions", self.fuselage_lenght, self.fuselage_height, self.fuselage_widht)
        self.m.display_this_shape(self.fuselage_shape, "Fuselage Shape")
        self.m.display_in_origin(self.fuselage_shape, True)
        
    def cut_fuselage_with_wing(self):
        self.cutted_fuselage_shape= OAlgo.BRepAlgoAPI_Cut(self.fuselage_shape,self.complete_wing).Shape()
        print(type(self.cutted_fuselage_shape), self.cutted_fuselage_shape.ShapeType())
        self.m.display_this_shape(self.cutted_fuselage_shape, "Cutted Fuselage")
        
    def hollow_fuselage(self):
        #facesToRemove = TopTools_ListOfShape()
        # Fuselage Hollow, walls for wings #0.01
        #self.fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(self.cutted_fuselage_shape, facesToRemove, 0.04, 0.01).Shape()
        self.fuselage_hollow= create_hollowedsolid(self.fuselage_shape,0.0004)
        self.m.display_this_shape(self.fuselage_hollow, "Hollow Fuselage- Thickness 0.4mm",True)
        

    def create_cross_rib(self):
        rib_width= 0.0004
        self.mybox = OPrim.BRepPrimAPI_MakeBox(1, 1, 1).Shape()
        box = OPrim.BRepPrimAPI_MakeBox(self.fuselage_lenght*2, rib_width*2, self.fuselage_height*2).Shape()
        self.moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-rib_width,-self.fuselage_height))
        #Cut Out for Hardware
        hardware_box_height=self.fuselage_height*0.4+(rib_width/2)
        hardware_box_lenght= self.fuselage_lenght*0.4
        hardware_box_widht= self.fuselage_widht*0.8
        hardware_box= OPrim.BRepPrimAPI_MakeBox(hardware_box_lenght, hardware_box_widht, hardware_box_height).Shape()
        self.moved_hardware_box= OExs.translate_shp(hardware_box,Ogp.gp_Vec(0,-hardware_box_widht/2, -hardware_box_height+ (rib_width/2)))
        self.m.display_this_shape(self.moved_hardware_box, "Hardware Box")
        rib_quantity=2
        d_angle= 180/rib_quantity
        for i in range(rib_quantity):     
            angle=i*d_angle
            print(i, angle) 
            sbox= self.rotate_shape(self.moved_box, Ogp.gp_OX(), angle)
            if i==0:
                self.rippen=sbox
            else:
                self.rippen=OAlgo.BRepAlgoAPI_Fuse(self.rippen,sbox).Shape()
        self.m.display_this_shape(self.rippen, "Cross Ribs")
        
    def create_quadrat_rib(self, rib_width=0.0004, factor=0.3):
        box = OPrim.BRepPrimAPI_MakeBox(self.fuselage_lenght*2, rib_width*2, self.fuselage_height*2).Shape()
        moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-rib_width,-self.fuselage_height))
        self.m.display_this_shape(moved_box, "MOved Box")
        #self.m.display_in_origin(self.moved_box)
        ver_rib=moved_box
        ver_rib_1=OExs.translate_shp(ver_rib,Ogp.gp_Vec(0.0,self.fuselage_widht*factor,0.0))
        ver_rib_2=OExs.translate_shp(ver_rib,Ogp.gp_Vec(0.0,-self.fuselage_widht*factor,0.0))
        self.m.display_in_origin(ver_rib_1)
        self.m.display_in_origin(ver_rib_2)
        hor_rib= rotate_shape(moved_box, Ogp.gp_OX(), 90)
        hor_rib_1=OExs.translate_shp(hor_rib,Ogp.gp_Vec(0.0,0.0,self.fuselage_height*factor))
        self.m.display_in_origin(hor_rib_1)
        hor_rib_2=OExs.translate_shp(hor_rib,Ogp.gp_Vec(0.0,0.0,-self.fuselage_height*factor))
        self.m.display_in_origin(hor_rib_2)
        rippen=ver_rib_1
        rippen=OAlgo.BRepAlgoAPI_Fuse(rippen,ver_rib_2).Shape()
        rippen=OAlgo.BRepAlgoAPI_Fuse(rippen,hor_rib_1).Shape()
        rippen=OAlgo.BRepAlgoAPI_Fuse(rippen,hor_rib_2).Shape()
        self.m.display_this_shape(rippen, "Corrs Ribs")
        return rippen
    
    def create_cylinder_reinforcemnt(self, factor=0.3,radius=0.004 ):
        cylinder= OPrim.BRepPrimAPI_MakeCylinder(radius,self.fuselage_lenght).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        cylinder_1= OExs.translate_shp(cylinder,Ogp.gp_Vec(0.0,self.fuselage_widht*factor,self.fuselage_height*factor))
        cylinder_2= OExs.translate_shp(cylinder,Ogp.gp_Vec(0.0,self.fuselage_widht*factor,-self.fuselage_height*factor))
        cylinder_3= OExs.translate_shp(cylinder,Ogp.gp_Vec(0.0,-self.fuselage_widht*factor,-self.fuselage_height*factor))
        cylinder_4= OExs.translate_shp(cylinder,Ogp.gp_Vec(0.0,-self.fuselage_widht*factor,self.fuselage_height*factor))
        cylinders=cylinder_1
        cylinders=OAlgo.BRepAlgoAPI_Fuse(cylinders,cylinder_2).Shape()
        cylinders=OAlgo.BRepAlgoAPI_Fuse(cylinders,cylinder_3).Shape()
        cylinders=OAlgo.BRepAlgoAPI_Fuse(cylinders,cylinder_4).Shape()
        self.m.display_this_shape(cylinders, "Reinforcement 4")
        self.m.display_in_origin(cylinders)
        return cylinders
        
    def create_sharp_ribs(self,rib_width=0.0004, factor=0.3, radius=0.004):
        quadrat= self.create_quadrat_rib(rib_width, factor)
        cylinders= self.create_cylinder_reinforcemnt(factor, radius)
        self.rippen_cuted= OAlgo.BRepAlgoAPI_Fuse(quadrat,cylinders).Shape()
        self.m.display_this_shape(self.rippen_cuted, "Sharp Rippen")
    
    def create_thin_star_ribs(self):
        #Cutout for Extra Ribs
        #cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*0.8)/2,40).Shape()
        cylinder= OPrim.BRepPrimAPI_MakeCylinder(1.5,40).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.m.display_this_shape(cylinder, "Cylinder Cutout")
        rib_quantity=2
        # Extraribs
        d_angle=180/(rib_quantity*2)
        for i in range(rib_quantity*2):
            angle=i*d_angle
            print(i, angle) 
            sbox= self.rotate_shape(self.moved_box, Ogp.gp_OX(), angle)
            if i==0:
                self.rippen_ver=sbox
            else:
                self.rippen_ver=OAlgo.BRepAlgoAPI_Fuse(self.rippen_ver,sbox).Shape()
        self.m.display_this_shape(self.rippen_ver, "Star ribs")
        self.rippen_ver= OAlgo.BRepAlgoAPI_Cut(self.rippen_ver, cylinder).Shape()
        self.m.display_this_shape(self.rippen_ver,"Starribs with cylinder cutout")

    def reinforcement_tunel_in(self):
        self.reinforcement_tunnel_in= OPrim.BRepPrimAPI_MakeCylinder(0.002,self.fuselage_lenght).Shape()
        self.reinforcement_tunnel_in= self.rotate_shape(self.reinforcement_tunnel_in, Ogp.gp_OY(), 90)
    
    def reinforcement_tunel_out(self):
        self.reinforcement_tunnel_out= OPrim.BRepPrimAPI_MakeCylinder(0.004,self.fuselage_lenght).Shape()
        self.reinforcement_tunnel_out= self.rotate_shape(self.reinforcement_tunnel_out, Ogp.gp_OY(), 90)
        self.m.display_this_shape(self.reinforcement_tunnel_out, "Reinforcement Tunel")

    def common_fuselage_ribs_ver(self):     
        self.rippen_ver= OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, self.rippen_ver).Shape()
        self.m.display_this_shape(self.rippen_ver, "Ribs cut to fuselage shape")
       
    def cut_ribs_harwarebox(self):
        self.rippen_cuted=  OAlgo.BRepAlgoAPI_Cut(self.rippen, self.moved_hardware_box).Shape()
        self.m.display_this_shape(self.rippen_cuted, "Cross Ribs with hardware Box Cutout")

    def fuse_reinforcemt_ribs(self):
        self.rippen_cuted= OAlgo.BRepAlgoAPI_Fuse(self.rippen_cuted,self.reinforcement_tunnel_out).Shape()
        self.m.display_this_shape(self.rippen_cuted, "Ribs with reinforcement tunel")

    def common_fuselage_ribs_cuted(self):
        #self.rippen_cuted=OAlgo.BRepAlgoAPI_Common(self.cutted_fuselage_shape, self.rippen_cuted).Shape()
        #self.m.display_in_origin(self.fuselage_shape, True)
        #self.m.display_in_origin(self.rippen_cuted, True)
        #fuselage_offset= OOff.BRepOffsetAPI_MakeOffsetShape(self.fuselage_shape, 0.0004,0.0001).Shape()
        self.rippen_cuted=OAlgo.BRepAlgoAPI_Common(self.fuselage_shape,self.rippen_cuted).Shape()
        self.m.display_this_shape(self.rippen_cuted,"Cut ribs to fuselage shape")
        #self.m.display_in_origin(self.rippen_cuted)

    def fuse_ribs(self):
        self.rippen_gesamt=OAlgo.BRepAlgoAPI_Fuse(self.rippen_cuted, self.rippen_ver).Shape()
        self.m.display_this_shape(self.rippen_gesamt, " Fused Ribs")
        
    def center_mass(self):
        point:Ogp.gp_Pnt =TGeo.get_center_of_mass(self.rippen_cuted)
        print(point.X(), point.Y(), point.Z())
        center_of_mass = OPrim.BRepPrimAPI_MakeSphere(point, 1).Shape()
        
    def fuse_fuselagehollow_ribs(self):             
        print("---------Starting last Fuse: Wait...")
        self.m.display_in_origin(self.fuselage_hollow, True)
        self.m.display_in_origin(self.rippen_cuted)
        self.fuselage_done=OAlgo.BRepAlgoAPI_Fuse(self.fuselage_hollow,self.rippen_cuted).Shape()
        self.m.display_this_shape(self.fuselage_done, "Done")
        
    def test_fuse(self):
        print("---------Starting Test Fuse: Wait...")
        #self.m.display_in_origin(self.fuselage_hollow, True)        
        mybox = OPrim.BRepPrimAPI_MakeBox(self.fuselage_lenght/10, self.fuselage_widht/10, self.fuselage_height/10).Shape()
        mybox=translate_shp(mybox,gp_Vec(0,self.fuselage_widht/2,self.fuselage_height/2))
        self.m.display_in_origin(mybox)
        self.fuselage_done=OAlgo.BRepAlgoAPI_Fuse(self.fuselage_hollow,self.rippen_cuted).Shape()
        self.m.display_this_shape(self.fuselage_done, "Test Fuse")
    
    def cut_fuselage_ribs(self):             
        print("Cutting: fuselage and ribs...")
        self.m.display_in_origin(self.fuselage_offset, True)
        self.m.display_in_origin(self.rippen_cuted)
        self.fuselage_done= OAlgo.BRepAlgoAPI_Cut(self.fuselage_offset,self.rippen_cuted).Shape()
        self.m.display_this_shape(self.fuselage_done, "Done")
        
    def create_hollow(self, offset=0.001):
        fuselage_offset= OOff.BRepOffsetAPI_MakeOffsetShape(self.fuselage_shape, -offset,0.0001).Shape()
        self.m.display_this_shape(fuselage_offset)
        self.fuselage_hollow= OAlgo.BRepAlgoAPI_Cut(self.fuselage_shape,fuselage_offset).Shape()
        self.m.display_this_shape(self.fuselage_hollow, "")
        
    def offset_fuselage(self):
        self.fuselage_offset= OOff.BRepOffsetAPI_MakeOffsetShape(self.fuselage_shape, 0.0008,0.00001).Shape()


if __name__ == "__main__":
    a=aircombat_test()
    a.create_fuselage()
    a.create_sharp_ribs()
    
    a.offset_fuselage() 
    #a.create_cross_rib()
    #a.reinforcement_tunel_out()
    #a.cut_ribs_harwarebox()
    #a.fuse_reinforcemt_ribs()
    a.common_fuselage_ribs_cuted()
    a.cut_fuselage_ribs()

    slicer=ShapeSlicer(a.fuselage_done,4)
    slicer.slice2()
    write_stls_srom_list(slicer.parts_list)
    
    a.m.start()
    
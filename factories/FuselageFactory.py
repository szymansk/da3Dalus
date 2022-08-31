from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored

import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories
import tigl3.boolean_ops as TBoo

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import time
from OCC.Display.SimpleGui import init_display

from factories.RibFactory import *
from parts.Wing import *
from parts.Fuselage import *

from abmasse import *
from Ausgabeservice import *
from Aussparungen import *
from Innenstruktur import *
from shape_verschieben import *
from Wand_erstellen import *
import logging

class FuselageFactory:
    def __init__(self, tigl_handle) -> None:
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.fuselage:Fuselage= Fuselage()
    
    def create_fuselage_shape(self, fuse_nr):
        fuselage: TConfig.CCPACSFuselage= self.cpacs_configuration.get_fuselage(fuse_nr)
        self.fuselage.loft: TGeo.CNamedShape= fuselage.get_loft()
        self.fuselage.shape: OTopo.TopoDS_Shape=self.fuselage.loft.shape()
        self.fuselage.calculate_koordinates()
        self.fuselage.calculate_outter_dimensions()
        print(self.fuselage.__str__())
        
    def create_holow_fuselage(self, thickness:float):
        self.fuselage.hollow= create_hollowedsolid(self.fuselage.shape ,thickness)
        #facesToRemove = TopTools_ListOfShape()
        #self.fuselage.hollow= OOff.BRepOffsetAPI_MakeThickSolid(self.fuselage.cutted.shape(), facesToRemove, thickness, 0.001)
    
    def fuse_ribs(self, ribs):
        logging.info("Start Fuselage Fuse ---- Wait")
        start= time.time()
        #cuts the ribs to the shape of the wing
        #CommonSurface = OAlgo.BRepAlgoAPI_Common(self.wing.rib.ribs,self.wing.shape).Shape()
        CommonSurface = OAlgo.BRepAlgoAPI_Common(ribs,self.fuselage.shape).Shape()
        #fuses Wing and Ribs to 1 shape
        self.fuselage.with_ribs= OAlgo.BRepAlgoAPI_Fuse(self.fuselage.hollow,CommonSurface).Shape()
        end= time.time()
        dif= end-start
        logging.info("Fuselage Fuse took " + str(dif) + "seconds")
     
    def cut_out_wing(self):
        display, start_display, add_menu, add_function_to_menu = init_display()
        wing: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(1) 
        wing_loft: TGeo.CNamedShape = wing.get_loft()
        wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
        aTrsf= Ogp.gp_Trsf()
        aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
        transformed_wing = OBuilder.BRepBuilderAPI_Transform(wing_shape, aTrsf)
        mirrored_wing= transformed_wing.Shape()
        complete_wing2= BRepAlgoAPI_Fuse(wing_shape,mirrored_wing).Shape()
        print("complete:" ,type(complete_wing2))
        #display.DisplayShape(complete_wing)
        #display.FitAll()
        #start_display()
        named_wings_shape= TGeo.CNamedShape(complete_wing2, "cutout")
        cutter= TBoo.CCutShape(self.fuselage.loft, named_wings_shape)
        self.fuselage.cutted:TGeo.CNamedShape= cutter.named_shape().shape()

            
    def export_stl(self, name):
        write_stl_file2(self.fuselage.with_ribs, name)
        
    def make_profil(self,tigl_h):
        self.tigl_h=tigl_h
        # display, start_display, add_menu, add_function_to_menu = init_display()
        #servo,b1,b2,fertig = a1.make_Servo(0.15,0.2,0.2)
        #display.DisplayShape(servo.Shape(),color="blue")
        #display.DisplayShape(b1)
        #display.DisplayShape(b2)

        #FIXME unpack config outsource
        # get the configuration manager
        mgr = tigl3.configuration.CCPACSConfigurationManager_get_instance()
        # get the CPACS configuration, defined by the tigl handle
        # we need to access the underlying tigl handle (that is used in the C/C++ API)
        config = mgr.get_configuration(tigl_h._handle.value)
        
        CommonSurface=[]
        for ifuse in range(1, config.get_fuselage_count() + 1):
            fuselage = config.get_fuselage(ifuse)
            fuselage_shape = fuselage.get_loft().shape()

            #display.DisplayShape(fuselage_shape)

            xmin,ymin,zmin,xmax,ymax,zmax = get_koordinates(fuselage_shape)
            xdiff,zdiff,ydiff = get_dimensions(xmin,ymin,zmin,xmax,ymax,zmax)
            #print(xdiff,zdiff,ydiff,xmax)
            #print(xmax,ymax,zmax)

            #S=make_ribs(ydiff,xdiff,0.1,xmax)
            # hoehe,breite,dicke,extrude
            S=make_ribs(zdiff,ydiff,0.1,xmax*2)
            #rotate ribs so it can be printed
            Srotate=rotate_shape(S.Shape(),gp_OY(),90)
            anzahl = 3
            #Sneu = make_translation(Srotate,-0.1,anzahl)
            Sskdl= self.make_translation_fuse(Srotate,-0.9,anzahl)
            #display.DisplayShape(Sskdl)
            
            m_rippen = move_rippen_neu(Sskdl,0,0,zdiff*0.5)
          
            #m_rippen = move_rippen_neu(Sskdl,0,0,0)
            #display.DisplayShape(m_rippen)
            #CommonSurface2=BRepAlgoAPI_Common(m_rippen,fuselage_shape).Shape()
            #display.DisplayShape(CommonSurface2)
            #verbunden=BRepAlgoAPI_Fuse(neu)

            #neu=[]
            #verbunden=[]
            profile=[]
            #CommonSurface3=[]
            #CS=[]

            for isegment in range(1, fuselage.get_segment_count() + 1):
            #for isegment in range(1, 16):
                segment = fuselage.get_segment(isegment)
                profile.append(segment.get_loft().shape())
                #CommonSurface3.append(BRepAlgoAPI_Common(m_rippen,profile[isegment-1]).Shape())
                #neu.append(w1.create_hollowedsolid(segment.get_loft().shape()))
                #verbunden.append(BRepAlgoAPI_Fuse(neu[isegment-1],CommonSurface3[isegment-1]).Shape())
                #verbunden.append(BRepAlgoAPI_Fuse(neu[isegment-1],CommonSurface3).Shape())
                #display.DisplayShape(verbunden)
                #display.DisplayShape(CommonSurface3)
            #display.DisplayShape(verbunden)

            cs=fuse_shapes_common(profile)
            ausgehoelt=create_hollowedsolid(cs,0.04)

            #display.DisplayShape(cs,transparency=0.8)
            #display.DisplayShape(neu,transparency=0.8)
            CommonSurface3=BRepAlgoAPI_Common(m_rippen,cs).Shape()

            #display.DisplayShape(CommonSurface3)
            fertig=BRepAlgoAPI_Fuse(ausgehoelt,CommonSurface3).Shape()
            
            # display.DisplayShape(fertig,transparency=0.8)
            write_stl_file2(fertig,"rumpf.stl")
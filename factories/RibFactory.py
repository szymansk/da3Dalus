import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo
from math import *
from parts.Rib import *



class RibFactory:
    
    def __init__(self) -> None:
        self.rib:Rib= Rib()
              
    #TODO where does height, thikness, extrude come frome?
    def create_rib_grid(self, spacing, thikness,xdiff, ydiff, zdiff,type:str="x"):
       #self.rib.height=self.wing.xdiff
       self.rib.height=xdiff
       self.rib.thikness=thikness
       self.rib.set_profile(type)
       self.rib.extrude_lenght=zdiff
       self.rib.ydiff=ydiff
       self.rib.spacing=spacing
       self.extrude_profile(self.rib.extrude_lenght)
       self.make_pattern()
    
    #def create_rib(self,profile_height, profile_thikness, extrude_lenght):
     #   self.single = Ribs(profile_height, profile_thikness, extrude_lenght)

    def extrude_profile(self, extrude_lenght):
        self.rib.extrude_length=extrude_lenght
        self.rib.rib= OPrim.BRepPrimAPI_MakePrism(
            self.rib.profile,
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, self.rib.extrude_lenght)),
        )
        
    def make_pattern(self):
        trans_rib=None
        ribs=self.rib.rib.Shape()
        spacing=self.rib.spacing       
        q=self.calculate_ribs_quantity()
        position=-(spacing*q/4)
        print("position:",position)
        for i in range(q):
            trans_rib=OExs.translate_shp(self.rib.rib.Shape(),gp_Vec(0.0,position,0.0))
            #ribs=OAlgo.BRepAlgoAPI_Fuse(self.rib.single,trans_rib).Shape()
            ribs=OAlgo.BRepAlgoAPI_Fuse(ribs,trans_rib).Shape()
            position=position + spacing
        #ribs=move_rippen_neu(ribs,self.wing.xmin,self.wing.ymax,self.wing.zmin)
        self.rib.ribs= ribs
    
    def calculate_ribs_quantity(self) ->int:
        x= int(2*(self.rib.ydiff/self.rib.spacing))
        print("Rib_quantity:" , x)
        x=6
        return (x)

    #def move_rippen(self,rippen_gesamt,xmin,ymin,zmin):
    def move_rippen(self, x, y,z ):
        trafo = TGeo.CTiglTransformation()
        #trafo.add_translation(self.wing.xmin,self.wing.ymin,self.wing.zmin)
        trafo.add_translation(x,y,z)
        self.rib.ribs=trafo.transform(self.rib.ribs)
        
    def rotate(self, axis, angle):
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
        trns = gp_Trsf()
        trns.SetRotation(axis, angle)
        brep_trns = OBuilder.BRepBuilderAPI_Transform(self.rib.ribs, trns, False)
        brep_trns.Build()
        self.rib.ribs = brep_trns.Shape()
    
    '''    
    def extrude_profile(self):
        return OPrim.BRepPrimAPI_MakePrism(
            self.rib.profile,
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, self.rib.extrude_lenght)),
        )
      
    def make_pattern(self,anz, wingspan,spacing):
        trans_rib=None
        ribs=self.rib.single
        for i in range(anz):
            trans_rib=OExs.translate_shp(self.rib.single,gp_Vec(0.0,wingspan,0.0))
            #ribs=OAlgo.BRepAlgoAPI_Fuse(self.rib.single,trans_rib).Shape()
            ribs=OAlgo.BRepAlgoAPI_Fuse(ribs,trans_rib).Shape()
            wingspan=wingspan-spacing
        self.ribs.shape= ribs
    
    def rotate(shape, axis, angle):
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
    trns = gp_Trsf()
    trns.SetRotation(axis, angle)
    brep_trns = OBuilder.BRepBuilderAPI_Transform(shape, trns, False)
    brep_trns.Build()
    shp = brep_trns.Shape()
    return shp
    '''
    

    
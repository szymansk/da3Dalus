from __future__ import print_function

import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
from _alt.abmasse import get_dimensions_from_Shape
from stl_exporter.Exporter import write_stl_file2


def get_tigl_handler(i_cpacs):
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    
    if i_cpacs==0:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
    if i_cpacs==1:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
    if i_cpacs==2:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinybit_new.xml")
    if i_cpacs==3:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
    if i_cpacs==4:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\test_fuselage_v2.xml")
    if i_cpacs==5:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\d150_rumpf_skaliert_v2.xml")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle
    

m= myDisplay.instance(True)

for i in range(4,6):
    print(i)
    tigl_handle= get_tigl_handler(i)
    config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
   
    cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)
    fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
    name2= fuselage.get_name()
    fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
    x,y,z=get_dimensions_from_Shape(fuselage_shape)
    msg= f"stest {name2}  {x:.3f} {y:.3f} {z:.3f} "
    m.display_this_shape(fuselage_shape, msg)
    name2= name2 + str(i) + ".stl"
    write_stl_file2(fuselage_shape,name2)
    print("Done")
    
m.start()

    #wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
    #wing_loft: TGeo.CNamedShape = wing.get_loft()
    #wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    #Set up the mirror
    #wing1: TConfig.CCPACSWing= cpacs_configuration.get_wing(3)   
    #wing_loft1: TGeo.CNamedShape = wing1.get_loft()
    #wing_shape1: OTopo.TopoDS_Shape = wing_loft1.shape()
    

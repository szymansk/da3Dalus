from __future__ import print_function

import tigl3.configuration as TConfig

from _alt.Wand_erstellen import *

i_cpacs=2
	
tixi_h = tixi3wrapper.Tixi3()
tigl_handle = tigl3wrapper.Tigl3()
if i_cpacs==1:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
if i_cpacs==2:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
if i_cpacs==3:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat.xml")
if i_cpacs==4:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinybit_rumpf.xml") 
tigl_handle.open(tixi_h, "")




config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)
wing: TConfig.CCPACSWing==None
for iwing in range(1,cpacs_configuration.get_wing_count()+1):  
    wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(iwing)
    print(iwing, ":", wing.get_name())
    for isection in range(1, wing.get_section_count()+1):
        section1: TConfig.CCPACSWingSection= wing.get_section(1)
        print("\t", isection, ":", section1.get_name())
        for ielement in range (1, section1.get_section_element_count()+1):
            element: TConfig.CCPACSWingSectionElement= section1.get_section_element(ielement)
            print("\t\t", ielement, ":", element.get_name(),"-", element.get_airfoil_uid(), "-", element.get_scaling())
            
profile: TConfig.CCPACSWingProfile= cpacs_configuration.get_wing_profile("D150_VAMP_W_SupCritProf1")
l_wire:OTopo.TopoDS_Wire= profile.get_lower_wire()
shape:OTopo.TopoDS_Shape=l_wire.Complemented()

mywire:OTopo.TopoDS_Wire = profile.get_wire()
c_wire:OTopo.TopoDS_Wire= profile.get_chord_line_wire()
c_Shape=c_wire.Complemented()


display, start_display, add_menu, add_function_to_menu = init_display()
display.DisplayShape(mywire)
display.DisplayShape(c_Shape)
display.FitAll()
start_display()


      
            
    
    #element1: TConfig.CCPACSWingSectionElement= section1.get_section_element(1)
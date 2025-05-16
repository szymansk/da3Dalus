import os
import sys
import json
import zipfile
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.fuselage.FuselageConfiguration import FuselageConfiguration

def test_airplane_configuration_serialization():
    """Test serialization and deserialization of AirplaneConfiguration."""
    print("Testing AirplaneConfiguration serialization and deserialization...")
    
    # Create a simple wing configuration
    root_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=100, incidence=0)
    tip_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=50, incidence=0)
    
    wing = WingConfiguration(nose_pnt=(0, 0, 0), root_airfoil=root_airfoil, length=1000, sweep=100,
                             tip_airfoil=tip_airfoil, symmetric=True)
    
    # Create a simple fuselage configuration
    fuselage = FuselageConfiguration(name="test_fuselage")
    
    # Create an airplane configuration
    airplane = AirplaneConfiguration(
        name="test_airplane",
        total_mass_kg=100,
        wings=[wing],
        fuselages=[fuselage]
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test saving to JSON
    json_path = output_dir / "airplane.json"
    airplane.save_to_json(str(json_path))
    print(f"Saved airplane configuration to {json_path}")
    
    # Test loading from JSON
    loaded_airplane = AirplaneConfiguration.from_json(str(json_path))
    print(f"Loaded airplane configuration from {json_path}")
    print(f"Original name: {airplane.name}, Loaded name: {loaded_airplane.name}")
    print(f"Original mass: {airplane.total_mass}, Loaded mass: {loaded_airplane.total_mass}")
    print(f"Original wings count: {len(airplane.wings)}, Loaded wings count: {len(loaded_airplane.wings)}")
    print(f"Original fuselages count: {len(airplane.fuselages)}, Loaded fuselages count: {len(loaded_airplane.fuselages)}")
    
    # Test saving to ZIP
    zip_path = output_dir / "airplane.zip"
    airplane.save_to_zip(str(zip_path))
    print(f"Saved airplane configuration to {zip_path}")
    
    # Test loading from ZIP
    loaded_airplane_from_zip = AirplaneConfiguration.from_zip(str(zip_path))
    print(f"Loaded airplane configuration from {zip_path}")
    print(f"Original name: {airplane.name}, Loaded name: {loaded_airplane_from_zip.name}")
    print(f"Original mass: {airplane.total_mass}, Loaded mass: {loaded_airplane_from_zip.total_mass}")
    print(f"Original wings count: {len(airplane.wings)}, Loaded wings count: {len(loaded_airplane_from_zip.wings)}")
    print(f"Original fuselages count: {len(airplane.fuselages)}, Loaded fuselages count: {len(loaded_airplane_from_zip.fuselages)}")
    
    # Test loading individual components
    with zipfile.ZipFile(str(zip_path), 'r') as zipf:
        # Extract the wing file
        wing_file = "wings/wing_0.json"
        zipf.extract(wing_file, str(output_dir))
        
        # Load the wing
        wing_path = output_dir / wing_file
        loaded_wing = WingConfiguration.from_json(str(wing_path))
        print(f"Loaded wing from {wing_path}")
        #print(f"Original wing length: {wing.}, Loaded wing length: {loaded_wing.length}")
        
        # Extract the fuselage file
        fuselage_file = "fuselages/fuselage_0.json"
        zipf.extract(fuselage_file, str(output_dir))
        
        # Load the fuselage
        fuselage_path = output_dir / fuselage_file
        loaded_fuselage = FuselageConfiguration.from_json(str(fuselage_path))
        print(f"Loaded fuselage from {fuselage_path}")
        print(f"Original fuselage name: {fuselage.name}, Loaded fuselage name: {loaded_fuselage.name}")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_airplane_configuration_serialization()
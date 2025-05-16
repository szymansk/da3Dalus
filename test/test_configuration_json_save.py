import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.fuselage.FuselageConfiguration import FuselageConfiguration

def test_wing_configuration_save_load():
    """Test saving and loading a WingConfiguration to/from a JSON file."""
    print("Testing WingConfiguration save_to_json and from_json...")
    
    # Create a simple wing configuration
    root_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=100, incidence=0)
    tip_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=50, incidence=0)
    
    wing = WingConfiguration(nose_pnt=(0, 0, 0), root_airfoil=root_airfoil, length=1000, sweep=100,
                             tip_airfoil=tip_airfoil, symmetric=True)
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_json_save")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON
    json_path = output_dir / "wing.json"
    wing.save_to_json(str(json_path))
    print(f"Saved wing configuration to {json_path}")
    
    # Load from JSON
    loaded_wing = WingConfiguration.from_json(str(json_path))
    print(f"Loaded wing configuration from {json_path}")
    
    # Verify some properties
    print(f"Original wing length: {wing.length}, Loaded wing length: {loaded_wing.length}")
    print(f"Original wing sweep: {wing.sweep}, Loaded wing sweep: {loaded_wing.sweep}")
    print(f"Original wing symmetric: {wing.symmetric}, Loaded wing symmetric: {loaded_wing.symmetric}")
    
    print("WingConfiguration test completed successfully!")

def test_fuselage_configuration_save_load():
    """Test saving and loading a FuselageConfiguration to/from a JSON file."""
    print("\nTesting FuselageConfiguration save_to_json and from_json...")
    
    # Create a simple fuselage configuration
    fuselage = FuselageConfiguration(name="test_fuselage")
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_json_save")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON
    json_path = output_dir / "fuselage.json"
    fuselage.save_to_json(str(json_path))
    print(f"Saved fuselage configuration to {json_path}")
    
    # Load from JSON
    loaded_fuselage = FuselageConfiguration.from_json(str(json_path))
    print(f"Loaded fuselage configuration from {json_path}")
    
    # Verify some properties
    print(f"Original fuselage name: {fuselage.name}, Loaded fuselage name: {loaded_fuselage.name}")
    
    print("FuselageConfiguration test completed successfully!")

if __name__ == "__main__":
    test_wing_configuration_save_load()
    test_fuselage_configuration_save_load()
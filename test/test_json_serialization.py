import os
import sys
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.components.Servo import Servo

def test_trailing_edge_device_serialization():
    """Test serialization and deserialization of TrailingEdgeDevice."""
    print("Testing TrailingEdgeDevice serialization and deserialization...")
    
    # Create a simple TrailingEdgeDevice
    device = TrailingEdgeDevice(
        name="flap",
        rel_chord_root=0.7,
        rel_chord_tip=0.7,
        symmetric=True
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_json_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to JSON
    json_path = output_dir / "trailing_edge_device.json"
    with open(json_path, 'w') as f:
        json.dump(device.__getstate__(), f, indent=4)
    print(f"Saved trailing edge device to {json_path}")
    
    # Deserialize from JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    deserialized_device = TrailingEdgeDevice.from_json_dict(data)
    print(f"Loaded trailing edge device from {json_path}")
    
    # Verify properties
    print(f"Original name: {device.name}, Deserialized name: {deserialized_device.name}")
    print(f"Original rel_chord_root: {device.rel_chord_root}, Deserialized rel_chord_root: {deserialized_device.rel_chord_root}")
    print(f"Original symmetric: {device.symmetric}, Deserialized symmetric: {deserialized_device.symmetric}")
    
    print("TrailingEdgeDevice test completed successfully!")

def test_spare_serialization():
    """Test serialization and deserialization of Spare."""
    print("\nTesting Spare serialization and deserialization...")
    
    # Create a simple Spare
    spare = Spare(
        spare_support_dimension_width=10,
        spare_support_dimension_height=5,
        spare_position_factor=0.25,
        spare_length=100,
        spare_mode="standard"
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_json_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to JSON
    json_path = output_dir / "spare.json"
    with open(json_path, 'w') as f:
        json.dump(spare.__getstate__(), f, indent=4)
    print(f"Saved spare to {json_path}")
    
    # Deserialize from JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    deserialized_spare = Spare.from_json_dict(data)
    print(f"Loaded spare from {json_path}")
    
    # Verify properties
    print(f"Original spare_position_factor: {spare.spare_position_factor}, Deserialized spare_position_factor: {deserialized_spare.spare_position_factor}")
    print(f"Original spare_length: {spare.spare_length}, Deserialized spare_length: {deserialized_spare.spare_length}")
    print(f"Original spare_mode: {spare.spare_mode}, Deserialized spare_mode: {deserialized_spare.spare_mode}")
    
    print("Spare test completed successfully!")

def test_servo_serialization():
    """Test serialization and deserialization of Servo."""
    print("\nTesting Servo serialization and deserialization...")
    
    # Create a simple Servo
    servo = Servo(
        length=30,
        width=12,
        height=30,
        leading_length=15,
        latch_z=5,
        latch_x=2,
        latch_thickness=1,
        latch_length=3,
        cable_z=10,
        screw_hole_lx=5,
        screw_hole_d=2
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_json_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to JSON
    json_path = output_dir / "servo.json"
    with open(json_path, 'w') as f:
        json.dump(servo.__getstate__(), f, indent=4)
    print(f"Saved servo to {json_path}")
    
    # Deserialize from JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    deserialized_servo = Servo.from_json_dict(data)
    print(f"Loaded servo from {json_path}")
    
    # Verify properties
    print(f"Original length: {servo.length}, Deserialized length: {deserialized_servo.length}")
    print(f"Original width: {servo.width}, Deserialized width: {deserialized_servo.width}")
    print(f"Original height: {servo.height}, Deserialized height: {deserialized_servo.height}")
    print(f"Original trailing_length: {servo.trailing_length}, Deserialized trailing_length: {deserialized_servo.trailing_length}")
    
    print("Servo test completed successfully!")

def test_complex_object_serialization():
    """Test serialization and deserialization of complex objects."""
    print("\nTesting complex object serialization and deserialization...")
    
    # Create a Servo
    servo = Servo(
        length=30,
        width=12,
        height=30,
        leading_length=15,
        latch_z=5,
        latch_x=2,
        latch_thickness=1,
        latch_length=3,
        cable_z=10,
        screw_hole_lx=5,
        screw_hole_d=2
    )
    
    # Create a TrailingEdgeDevice with a Servo
    device = TrailingEdgeDevice(
        name="flap",
        rel_chord_root=0.7,
        rel_chord_tip=0.7,
        servo=servo,
        symmetric=True
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_json_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to JSON
    json_path = output_dir / "complex_object.json"
    with open(json_path, 'w') as f:
        json.dump(device.__getstate__(), f, indent=4)
    print(f"Saved complex object to {json_path}")
    
    # Deserialize from JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    deserialized_device = TrailingEdgeDevice.from_json_dict(data)
    print(f"Loaded complex object from {json_path}")
    
    # Verify properties
    print(f"Original name: {device.name}, Deserialized name: {deserialized_device.name}")
    print(f"Original has servo: {device._servo is not None}, Deserialized has servo: {deserialized_device._servo is not None}")
    if device._servo is not None and deserialized_device._servo is not None:
        print(f"Original servo length: {device._servo.length}, Deserialized servo length: {deserialized_device._servo.length}")
    
    print("Complex object test completed successfully!")

if __name__ == "__main__":
    test_trailing_edge_device_serialization()
    test_spare_serialization()
    test_servo_serialization()
    test_complex_object_serialization()
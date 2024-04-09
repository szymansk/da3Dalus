from Airplane.aircraft_topology.components.ComponentInformation import ComponentInformation
from Airplane.aircraft_topology.Position import Position

class EngineInformation(ComponentInformation):

    def __init__(self, down_thrust: float, side_thrust: float, position: Position,
                 length: float, width: float, height: float, screw_hole_circle: float, mount_box_length: float,
                 screw_din_diameter: float, screw_length: float, rot_x: float=0.0):
        self.engine_screw_length = screw_length
        self.engine_screw_din_diameter = screw_din_diameter
        self.engine_mount_box_length = mount_box_length
        self.engine_screw_hole_circle = screw_hole_circle
        self.height = height
        self.width = width
        self.length = length
        self.position = position
        self.side_thrust = side_thrust
        self.down_thrust = down_thrust
        self.rot_x = rot_x

        super().__init__(trans_z=self.position.get_z(),
                         trans_y=self.position.get_y(),
                         trans_x=self.position.get_x(),
                         rot_z=self.side_thrust,
                         rot_y=self.down_thrust,
                         rot_x=self.rot_x,
                         length=self.length,
                         width=self.width,
                         height=self.height)


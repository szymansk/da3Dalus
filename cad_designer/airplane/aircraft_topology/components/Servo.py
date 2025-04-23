from typing import TypeVar, Literal

from cadquery import Workplane, Sketch, Plane
from pydantic import NonNegativeFloat
from pydantic.v1 import PositiveFloat

T = TypeVar("T", bound="Servo")


class Servo:
    """
    A servo is a device to actuate control surfaces or other things on an rc-plane.

    We define the servo in the following way.
    1. the center of construction (0-point) is where the rotation axis (z-axis) intersects the center of the
    lever axis (y-axis).
    2. The z-axis is pointing upwards and x-axis is pointing along the servo's longer side
    3. The y-axis is orthogonal to the x and y-axis.

    Based on this coordinate system we can define all needed inputs for a servo
    """

    def __init__(self: T,
                 length: PositiveFloat,
                 width: PositiveFloat,
                 height: PositiveFloat,
                 leading_length: NonNegativeFloat,
                 latch_z: NonNegativeFloat,
                 latch_x: NonNegativeFloat,
                 latch_thickness: NonNegativeFloat,
                 latch_length: NonNegativeFloat,
                 cable_z: NonNegativeFloat,
                 screw_hole_lx: NonNegativeFloat,
                 screw_hole_d: NonNegativeFloat):
        self.length: float = length  # x-dimension
        self.width: float = width  # y-dimension
        self.height: float = height  # z-dimension
        self.leading_length: float = leading_length  # x-dimension from the front edge to 0-point

        # latch definition
        self.latch_z: float = latch_z  # z-dimension lower edge of latch
        self.latch_x: float = latch_x
        self.latch_thickness: float = latch_thickness
        self.latch_length: float = latch_length

        self.cable_z: float = cable_z

        self.screw_hole_lx = screw_hole_lx
        self.screw_hole_d = screw_hole_d

        self.trailing_length: float = self.length - self.leading_length
        pass

    def create_laying_glue_in_mount(self: T,
                                    base_thickness:float = 1.0,
                                    placement: Literal['top', 'bottom'] = 'top') -> Workplane:
        servo_outlines = (Sketch()
                          .segment((0, 0), (-self.leading_length, 0))
                          .segment((-self.leading_length, 0),
                                   (-self.leading_length, -self.latch_z + self.latch_thickness))
                          .segment((-self.leading_length, -self.latch_z + self.latch_thickness),
                                   (-self.leading_length - self.latch_length, -self.latch_z + self.latch_thickness))
                          .segment((-self.leading_length - self.latch_length, -self.latch_z + self.latch_thickness),
                                   (-self.leading_length - self.latch_length, -self.latch_z))
                          .segment((-self.leading_length - self.latch_length, -self.latch_z),
                                   (-self.leading_length, -self.latch_z))

                          .segment((-self.leading_length, -self.latch_z),
                                   (-self.leading_length, -self.cable_z + self.latch_thickness / 2.))
                          .segment((-self.leading_length, -self.cable_z + self.latch_thickness / 2.), (
            -self.leading_length - self.latch_length, -self.cable_z + self.latch_thickness / 2.))
                          .segment(
            (-self.leading_length - self.latch_length, -self.cable_z + self.latch_thickness / 2.),
            (-self.leading_length - self.latch_length, -self.cable_z - self.latch_thickness / 2.))
                          .segment(
            (-self.leading_length - self.latch_length, -self.cable_z - self.latch_thickness / 2.),
            (-self.leading_length - self.latch_length + 1, -self.cable_z - self.latch_thickness / 2.))
                          .segment(
            (-self.leading_length - self.latch_length + 1, -self.cable_z - self.latch_thickness / 2.),
            (-self.leading_length - self.latch_length + 1, -self.height))

                          .segment((-self.leading_length, -self.height),
                                   (self.trailing_length + self.latch_length - 1, -self.height))

                          .segment((0, 0), (self.trailing_length, 0))
                          .segment((self.trailing_length, 0),
                                   (self.trailing_length, -self.latch_z + self.latch_thickness))
                          .segment((self.trailing_length, -self.latch_z + self.latch_thickness),
                                   (self.trailing_length + self.latch_length, -self.latch_z + self.latch_thickness))
                          .segment((self.trailing_length + self.latch_length, -self.latch_z + self.latch_thickness),
                                   (self.trailing_length + self.latch_length, -self.latch_z))
                          .segment((self.trailing_length + self.latch_length, -self.latch_z),
                                   (self.trailing_length, -self.latch_z))

                          .segment((self.trailing_length, -self.latch_z),
                                   (self.trailing_length, -self.cable_z + self.latch_thickness / 2.))
                          .segment((self.trailing_length, -self.cable_z + self.latch_thickness / 2.), (
            self.trailing_length + self.latch_length, -self.cable_z + self.latch_thickness / 2.))
                          .segment(
            (self.trailing_length + self.latch_length, -self.cable_z + self.latch_thickness / 2.),
            (self.trailing_length + self.latch_length, -self.cable_z - self.latch_thickness / 2.))
                          .segment(
            (self.trailing_length + self.latch_length, -self.cable_z - self.latch_thickness / 2.),
            (self.trailing_length + self.latch_length - 1, -self.cable_z - self.latch_thickness / 2.))
                          .segment(
            (self.trailing_length + self.latch_length - 1, -self.cable_z - self.latch_thickness / 2.),
            (self.trailing_length + self.latch_length - 1, -self.height))
                          .assemble()
                          )

        glue_in_mount_outlines = (Sketch()
                                  .segment((0.5, 0), (0.5, -5))
                                  .segment((0.5, -5), (-0.5, -5))
                                  .segment((-0.5, -5), (-0.5, 0))
                                  .segment((-0.5, 0), (-self.leading_length - self.latch_length, 0))
                                  .segment((-self.leading_length - self.latch_length, 0),
                                           (-self.leading_length - self.latch_length, -self.height))
                                  .segment((-self.leading_length - self.latch_length, -self.height),
                                           (self.trailing_length + self.latch_length, -self.height))
                                  .segment((self.trailing_length + self.latch_length, -self.height),
                                           (self.trailing_length + self.latch_length, 0))
                                  .close()
                                  .assemble()
                                  )

        glue_in_mount = (Workplane()
        .placeSketch(glue_in_mount_outlines).extrude(until=  (self.width / 2 + base_thickness))
        .faces(">Z").workplane().placeSketch(servo_outlines).extrude(
            until=  (-self.width / 2.0),
            combine='cut')
        )

        if placement == 'top':
            glue_in_mount = glue_in_mount.mirror('XY')

        return glue_in_mount

    def create_laying_mount_for_wing(self: T) -> Workplane:
        glue_in_mount_outlines = (Sketch()
                                  .segment((0, 10), (-(self.leading_length + self.latch_length), 10))
                                  .segment((-(self.leading_length + self.latch_length), 10),
                                           (-(self.leading_length + self.latch_length), -self.height))
                                  .segment((-(self.leading_length + self.latch_length), -self.height),
                                           (self.trailing_length + self.latch_length, -self.height))
                                  .segment((self.trailing_length + self.latch_length, -self.height),
                                           (self.trailing_length + self.latch_length, 10))
                                  .close()
                                  .assemble()
                                  )
        mount_outlines_bottom = (Sketch()
                                 .segment((-0, 20), (-(self.leading_length + self.latch_length), 20))
                                 .segment((-(self.leading_length + self.latch_length), 20),
                                          (-(self.leading_length + self.latch_length), -self.height - 20))
                                 .segment((-(self.leading_length + self.latch_length), -self.height - 20),
                                          (self.trailing_length + self.latch_length + 20, -self.height - 20))
                                 .segment((self.trailing_length + self.latch_length + 20, -self.height - 20),
                                          (self.trailing_length + self.latch_length + 20, 20))
                                 .close()
                                 .assemble()
                                 )
        mount_outlines = (Sketch()
                          .segment((-0, 0), (-(self.leading_length + self.latch_length), 0))
                          .segment((-(self.leading_length + self.latch_length), 0),
                                   (-(self.leading_length + self.latch_length), -self.height - 20))
                          .segment((-(self.leading_length + self.latch_length), -self.height - 20),
                                   (self.trailing_length + self.latch_length + 20, -self.height - 20))
                          .segment((self.trailing_length + self.latch_length + 20, -self.height - 20),
                                   (self.trailing_length + self.latch_length + 20, 0))
                          .close()
                          .assemble()
                          )
        mount = (Workplane().tag('first')
                 .placeSketch(mount_outlines_bottom).extrude(until=-22, combine='a')
                 .edges('>Z').edges('>Y').chamfer(20)
                 .faces(">Z").workplane(offset=-1).placeSketch(mount_outlines).extrude(until=3, combine='a')
                 .edges('>Z').edges('>Y').chamfer(1.99)
                 .faces(">Z").workplane().placeSketch(glue_in_mount_outlines).extrude(until=-2, combine='cut')
                 .edges('>Z').edges('<Y').chamfer(18)
                 .edges('>Z').edges('>X').chamfer(18)
                 .faces(">Z").edges("<<Y[3]").chamfer(1.99)
                 )
        return mount

    def create_servo_cover_for_wing(self: T, printer_wall_thickness: float, offset: float, in_plane:Plane = None) -> Workplane:
        width_left = self.leading_length + self.latch_length + offset
        width_right = self.trailing_length + self.latch_length + offset
        height_down = self.height + offset
        height_up = offset
        cover_outlines = (Sketch()
                          .segment(         (-0,  height_up),   (-width_left,  height_up))
                          .segment((-width_left,  height_up),   (-width_left, -height_down))
                          .segment((-width_left, -height_down), (width_right, -height_down))
                          .segment((width_right, -height_down), (width_right,  height_up))
                          .close()
                          .assemble()
                          )
        wp = Workplane(inPlane=in_plane, origin=(0,0,0)) if in_plane is not None else Workplane()
        cover = (wp
                 .placeSketch(cover_outlines).extrude(until=printer_wall_thickness * 10)
                 .faces("<Z").workplane(invert=True)
                 .placeSketch(cover_outlines).extrude(until=-printer_wall_thickness * 10)
                 )
        return cover

    def __getstate__(self):
        """Return a dictionary of serializable attributes for JSON serialization."""
        return {
            'model': self.__class__.__name__,
            'length': self.length,
            'width': self.width,
            'height': self.height,
            'leading_length': self.leading_length,
            'latch_z': self.latch_z,
            'latch_x': self.latch_x,
            'latch_thickness': self.latch_thickness,
            'latch_length': self.latch_length,
            'cable_z': self.cable_z,
            'screw_hole_lx': self.screw_hole_lx,
            'screw_hole_d': self.screw_hole_d,
            'trailing_length': self.trailing_length
        }

    @staticmethod
    def from_json_dict(data: dict) -> 'Servo':
        """
        Create a Servo from a JSON dictionary.

        Args:
            data: Dictionary containing the Servo data.

        Returns:
            A new Servo instance.
        """
        # Create and return the Servo
        servo = Servo(
            length=data.get('length'),
            width=data.get('width'),
            height=data.get('height'),
            leading_length=data.get('leading_length'),
            latch_z=data.get('latch_z'),
            latch_x=data.get('latch_x'),
            latch_thickness=data.get('latch_thickness'),
            latch_length=data.get('latch_length'),
            cable_z=data.get('cable_z'),
            screw_hole_lx=data.get('screw_hole_lx'),
            screw_hole_d=data.get('screw_hole_d')
        )

        # Set trailing_length if it's in the data
        if 'trailing_length' in data:
            servo.trailing_length = data.get('trailing_length')

        return servo

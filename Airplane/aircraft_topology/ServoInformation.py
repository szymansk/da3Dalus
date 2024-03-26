import logging
from OCP.gp import *
from Airplane.aircraft_topology.ComponentInformation import ComponentInformation

class ServoInformation(ComponentInformation):
    def __init__(self, height: float, width: float, length: float, lever_length: float, rot_x: float = 0.0,
                 rot_y: float = 0.0,
                 rot_z: float = 0.0, trans_x: float = 0.0, trans_y: float = 0.0, trans_z: float = 0.0):
        self.lever_length = lever_length

        self.trans_z = trans_z
        self.trans_y = trans_y
        self.trans_x = trans_x
        self.rot_z = rot_z
        self.rot_y = rot_y
        self.rot_x = rot_x
        self.length = length
        self.width = width
        self.height = height

        self._corner_vecs = [gp_Vec(0.000000000, 0.000, 0),
                             gp_Vec(self.length, 0.000, 0),
                             gp_Vec(self.length, 0.000, -self.height),
                             gp_Vec(0.000000000, 0.000, -self.height),

                             gp_Vec(0.000000000, -self.width, 0),
                             gp_Vec(self.length, -self.width, 0),
                             gp_Vec(self.length, -self.width, -self.height),
                             gp_Vec(0.000000000, -self.width, -self.height)]
        super().__init__(trans_z=self.trans_z,
                         trans_y=self.trans_y,
                         trans_x=self.trans_x,
                         rot_z=self.rot_z,
                         rot_y=self.rot_y,
                         rot_x=self.rot_x,
                         length=self.length,
                         width=self.width,
                         height=self.height)


from typing import TypeVar

from cadquery import Sketch, Workplane

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

    def __init__(self: T, length: float, width: float, height: float, leading_length: float,
                 latch_z: float, latch_x: float, latch_thickness: float, latch_length: float,
                 cable_z: float):
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

        self.trailing_length: float = self.length - self.leading_length
        pass

    def create_laying_glue_in_mount(self: T, base_thickness:float = 1.0) -> Workplane:
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
                         .placeSketch(glue_in_mount_outlines).extrude(until=self.width / 2 + base_thickness)
                         .faces(">Z").workplane().placeSketch(servo_outlines).extrude(until=-self.width / 2.0,
                                                                                      combine='cut')
                         )

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

    def create_servo_cover_for_wing(self: T, printer_wall_thickness: float, offset: float) -> Workplane:
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
        cover = (Workplane()
                 .placeSketch(cover_outlines).extrude(until=printer_wall_thickness * 15)
                 .faces("<Z").workplane(invert=True)
                 .placeSketch(cover_outlines).extrude(until=-printer_wall_thickness * 15)
                 )
        return cover

if __name__ == "__main__":
    from cadq_server import CQServerConnector
    servo = Servo(length=23, width=12.5, height=31.5, leading_length=6,
                  latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                  cable_z=26)
    glue_in_mount = servo.create_laying_glue_in_mount()
    mount = servo.create_laying_mount_for_wing()

    mount.add(glue_in_mount).display("mounts", 5000)
    pass
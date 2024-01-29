import logging
import os
from pathlib import Path

import OCP
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.IGESControl import IGESControl_Reader, IGESControl_Writer
from OCP.Interface import Interface_Static
from OCP.TopoDS import TopoDS_Shape
from cadquery import Shape

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.aircraft_topology.ComponentInformation import ComponentInformation
from Airplane.aircraft_topology.ServoInformation import ServoInformation
from Airplane.creator.ScaleRotateTranslateCreator import ScaleRotateTranslateCreator
from Airplane.creator.StepImportCreator import StepImportCreator
from Extra.BooleanOperationsForLists import BooleanCADOperation

from Extra.ConstructionStepsViewer import *
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut


# === BEGIN: Basic shape operations ===
class Fuse2ShapesCreator(AbstractShapeCreator):
    """
    Fusing shape B with shape A.
    """

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None, loglevel=logging.INFO):
        self.shape_a = shape_a
        self.shape_b = shape_b
        super().__init__(creator_id, shapes_of_interest_keys=[self.shape_a, self.shape_b], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(
            f"fusing shapes '{list(shapes_of_interest.keys())[0]}' + '{list(shapes_of_interest.keys())[1]}' --> '{self.identifier}'")
        shape_list = [sh if isinstance(sh, cq.Workplane) else cq.Workplane(obj=sh) for sh in shape_list]

        fused_shape = shape_list[0] + shape_list[1]

        fused_shape.display(name=self.identifier, severity=logging.DEBUG)
        return {self.identifier: fused_shape}


class FuseMultipleShapesCreator(AbstractShapeCreator):
    """
    Fusing shape B with shape A.
    """

    def __init__(self, creator_id: str, shapes: list[str], loglevel=logging.INFO):
        self.shapes = shapes
        super().__init__(creator_id, shapes_of_interest_keys=shapes, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"fusing shapes '{' + '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")

        fused_shape = shape_list[0]
        for shape in shape_list[1:]:
            fused_shape += shape
        fused_shape = fused_shape.combine(glue=True)

        fused_shape.display(self.identifier, logging.DEBUG)
        return {self.identifier: fused_shape}


class Cut2ShapesCreator(AbstractShapeCreator):
    """
    Cut the subtrahend from the minuend (minuend - subtrahend = new_shape).
    """

    def __init__(self, creator_id: str,
                 minuend: str = None,
                 subtrahend: str = None, loglevel=logging.INFO):
        self.minuend = minuend
        self.subtrahend = subtrahend
        super().__init__(creator_id, shapes_of_interest_keys=[self.minuend, self.subtrahend], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(
            f"cutting shapes '{list(shapes_of_interest.keys())[0]}' - '{list(shapes_of_interest.keys())[1]}' "
            f"--> '{self.identifier}'")

        shape__minuend = shape_list[0]
        shape__subtrahend = shape_list[1]
        try:
            cut_shape = shape__minuend.cut(shape__subtrahend.solids().val(), clean=True).combine(glue=True)
        except:
            logging.error(
                f"FAILED: cutting shapes '{list(shapes_of_interest.keys())[0]}' - "
                f"'{list(shapes_of_interest.keys())[1]}' --> '{self.identifier}'")
            cut_shape = shape__minuend

        cut_shape.display(name=self.identifier, severity=logging.DEBUG)
        return {self.identifier: cut_shape}


class CutMultipleShapesCreator(AbstractShapeCreator):
    """
    Fusing shape B with shape A.
    """

    def __init__(self, creator_id: str, subtrahends: list[str], minuend: str = None, loglevel=logging.INFO):
        self.subtrahends = subtrahends
        self.minuend = minuend
        soik = [self.minuend] + self.subtrahends
        super().__init__(creator_id, shapes_of_interest_keys=soik, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"cutting shapes '{' - '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")
        subtrahends_shapes = [shapes_of_interest[key] for key in self.subtrahends]

        shape = list(shapes_of_interest.values())[0]
        for subtrahend in subtrahends_shapes:
            shape = shape.cut(subtrahend, clean=True)
            shape.display(name=f"{self.identifier}", severity=logging.NOTSET)
        new_shape = shape.combine(glue=True)

        new_shape.display(name=f"{self.identifier}", severity=logging.DEBUG)
        return {self.identifier: new_shape}


class SimpleOffsetShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 offset: float,
                 shape: str = None,
                 loglevel=logging.INFO):
        self.offset = offset
        self.shape = shape

        super().__init__(creator_id, shapes_of_interest_keys=[shape], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"offset shape '{list(shapes_of_interest.keys())[0]}' by {self.offset}mm --> '{self.identifier}'")

        shape: Workplane = shape_list[0].offset3D(self.offset, perform_simple=True).display(name=self.identifier, severity=logging.DEBUG)
        return {self.identifier: shape}


class FuselageShellShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 thickness: float,
                 fuselage: str = None,
                 loglevel=logging.INFO):
        self.thickness = thickness
        self.fuselage = fuselage

        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"shell shape '{list(shapes_of_interest.keys())[0]}' by {self.thickness}mm --> '{self.identifier}'")

        fuselage = shape_list[0].findSolid()
        offset_shape = cq.Workplane("ZY").newObject([fuselage]).offset3D(self.thickness)
        shape = cq.Workplane("ZY").newObject([fuselage]).cut(toCut=offset_shape)\
            .display(name=f"{self.identifier}", severity=logging.DEBUG).findSolid()

        return {self.identifier: shape}


class RepairFacesShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 shape: str = None,
                 repair_tool: str = None,
                 loglevel=logging.INFO):
        self.repair_tool = repair_tool
        self.shape = shape

        super().__init__(creator_id, shapes_of_interest_keys=[shape, repair_tool], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"repair shape '{list(shapes_of_interest.keys())[0]}' with {list(shapes_of_interest.keys())[1]} --> '{self.identifier}'")

        faces = shape_list[1].faces()
        shape = shape_list[0].add(faces).combine(glue=True, tol=0.05).display(name=self.identifier, severity=logging.DEBUG)

        return {self.identifier: shape}


#TODO: MirrorShapeCreator
class MirrorShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 shape: str = None,
                 loglevel=logging.INFO):
        self.shape = shape
        super().__init__(creator_id, shapes_of_interest_keys=[shape], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"mirror '{list(shapes_of_interest.keys())[0]}'  --> '{self.identifier}'")
        shape = shapes_of_interest[self.shape]

        # Set up the mirror
        aTrsf = Ogp.gp_Trsf()
        aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_DY()))
        # Apply the mirror transformation
        aBRespTrsf = BRepBuilderAPI_Transform(shape.shape(), aTrsf)

        topods_shape = aBRespTrsf.Shape()
        result = TGeo.CNamedShape(topods_shape, f"mirrored_{shape.name()}")

        ConstructionStepsViewer.instance().display_offset(result, shape, result, severity=logging.DEBUG,
                                                          msg=self.identifier)

        return {self.identifier: result}

class Intersect2ShapesCreator(AbstractShapeCreator):
    """
    Intersect the shape A with shape B (minuend / subtrahend = new_shape).
    """

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None, loglevel=logging.INFO):
        self.shape_a = shape_a
        self.shape_b = shape_b
        super().__init__(creator_id, shapes_of_interest_keys=[self.shape_a, self.shape_b], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(
            f"intersecting shapes '{list(shapes_of_interest.keys())[0]}' / '{list(shapes_of_interest.keys())[1]}' --> '{self.identifier}'")

        shape__a = shape_list[0]
        shape__b = shape_list[1]
        new_shape = shape__a.intersect(shape__b).combine(glue=True).display(name=self.identifier, severity=logging.DEBUG)

        return {self.identifier: new_shape}
# === END basic shape operations ===

class IgesImportCreator(AbstractShapeCreator):
    """
    Import an iges file as a shape.
    """

    def __init__(self, creator_id: str, iges_file: str, trans_x: float = .0, trans_y: float = .0, trans_z: float = .0,
                 rot_x: float = .0, rot_y: float = .0, rot_z: float = .0, scale: float = 1.0, scale_x=1.0, scale_y=1.0,
                 scale_z=1.0, loglevel=logging.INFO):
        self.iges_file = iges_file
        self.trans_x = trans_x
        self.trans_y = trans_y
        self.trans_z = trans_z
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z
        self.scale = scale
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.scale_z = scale_z

        if self.scale != 1.0:
            self.scale_x = self.scale_y = self.scale_z = self.scale

        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"importing iges model '{self.iges_file}' --> '{self.identifier}'")

        shape = IgesImportCreator.iges_importer(self.iges_file)
        trans_shape = ScaleRotateTranslateCreator.transform_by(shape, rot_x=self.rot_x, rot_y=self.rot_y,
                                                               rot_z=self.rot_z, trans_x=self.trans_x,
                                                               trans_y=self.trans_y, trans_z=self.trans_z,
                                                               scale_x=self.scale_x, scale_y=self.scale_y,
                                                               scale_z=self.scale_z)

        return {self.identifier: trans_shape}

    @classmethod
    def iges_importer(cls, filename) -> Workplane:
        """Imports a IGES file as a new CQ Workplane object."""
        reader = IGESControl_Reader()
        # with suppress_stdout_stderr():
        read_status = reader.ReadFile(filename)
        if read_status != OCP.IFSelect.IFSelect_RetDone:
            raise ValueError("IGES file %s could not be loaded" % (filename))
        reader.TransferRoots()
        occ_shapes = []
        for i in range(reader.NbShapes()):
            occ_shapes.append(reader.Shape(i + 1))
        solids = []
        for shape in occ_shapes:
            solids.append(Shape.cast(shape))

        return cq.Workplane("XY").newObject(solids)

class ExportToIgesCreator(AbstractShapeCreator):

    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str] = None, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.shapes_to_export: list[str] = shapes_to_export
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        for key, shape in shapes_of_interest.items():
            path = os.path.join(self.file_path, f"{self.identifier}_{key}.igs")
            logging.info(f"exporting iges model '{key}' --> '{path}'")
            self.export_iges_file(shape, path)
        return shapes_of_interest

    @classmethod
    def export_iges_file(cls, shape, filename, author=None, organization=None):
        """ Exports a shape to an IGES file.  """
        # initialize iges writer in BRep mode
        writer = IGESControl_Writer("MM", 1)
        Interface_Static.SetIVal("write.iges.brep.mode", 1)
        # write surfaces with iges 5.3 entities
        Interface_Static.SetIVal("write.convertsurface.mode", 1)
        Interface_Static.SetIVal("write.precision.mode", 1)
        if author is not None:
           Interface_Static.SetCVal("write.iges.header.author", author)
        if organization is not None:
           Interface_Static.SetCVal("write.iges.header.company", organization)
        writer.AddShape(shape.val().wrapped)
        writer.ComputeModel()
        writer.Write(filename)

class ExportToStepCreator(AbstractShapeCreator):

    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str] = None, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.shapes_to_export: list[str] = shapes_to_export
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"exporting step model '{', '.join(shapes_of_interest.keys())}' --> '{self.file_path}'")

        from cadquery import exporters
        ass = cq.Assembly()
        for name, shape in shapes_of_interest.items():
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.step")
            exporters.export(shape, step_path)
            ass.add(shape)

        step_path = os.path.join(self.file_path, f"{self.identifier}.step", exporters.ExportTypes.STEP)
        exporters.assembly.exportAssembly(ass, step_path)
        logging.debug(f"writing model to '{step_path}'")

        from OCP.STEPControl import STEPControl_AsIs
        from OCP.IFSelect import IFSelect_RetDone
        step_writer = self._generateStepWriter()
        for name, shape in shapes_of_interest.items():
            # t_shape = ScaleRotateTranslateCreator.transform_by(shape=shape, scale=1000.0)
            if step_writer.Transfer(shape.findSolid().wrapped, STEPControl_AsIs) != IFSelect_RetDone:
                logging.fatal(f"error while exporting '{name}'")
                raise RuntimeError(f"error while exporting '{name}'")

        step_path = os.path.join(self.file_path, f"{self.identifier}.stp")

        aStat = step_writer.Write(step_path)
        if aStat != IFSelect_RetDone:
            logging.ERROR("Step writing error")

        return shapes_of_interest

    def _generateStepWriter(self):
        # ===============
        from OCP.STEPControl import STEPControl_Controller, STEPControl_Writer
        st = STEPControl_Controller()
        # st.Init()
        step_writer = STEPControl_Writer()
        dd = step_writer.WS().TransferWriter().FinderProcess()
        # from OCP.Interface_Static import Interface_Static_SetCVal, Interface_Static_SetIVal
        # defines the version of schema used for the output STEP file:
        # 1 or AP214CD (default): AP214, CD version (dated 26 November 1996),
        # 2 or AP214DIS: AP214, DIS version (dated 15 September 1998).
        # 3 or AP203: AP203, possibly with modular extensions (depending on data written to a file).
        # 4 or AP214IS: AP214, IS version (dated 2002)
        # 5 or AP242DIS: AP242, DIS version.
        # Interface_Static_SetCVal("write.step.schema", "AP214CD")
        # 0 (Off) : (default) writes STEP files without assemblies.
        # 1 (On) : writes all shapes in the form of STEP assemblies.
        # 2 (Auto) : writes shapes having a structure of (possibly nested) TopoDS_Compounds in the form of STEP
        #    assemblies, single shapes are written without assembly structures.
        # Interface_Static_SetIVal("write.step.assembly", 0)
        # Interface_Static_SetCVal("write.step.unit", "")
        # Interface_Static_SetIVal("write.precision.mode", 0)
        return step_writer

class ExportToStlCreator(AbstractShapeCreator):

    def __init__(self, creator_id: str, shapes_to_export: list[str], mode: str = "binary",
                 linear_deflection: float = 0.0000001, loglevel=logging.INFO):
        self.mode = mode
        self.linear_deflection = linear_deflection
        self.shapes_to_export: list[str] = shapes_to_export \
            if shapes_to_export is not None else [None]
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"converting shapes '{', '.join(shapes_of_interest.keys())}' to .STL")

        import stl_exporter.Exporter as Exporter
        stl_exporter = Exporter.Exporter()
        stl_exporter.write_stls_from_list(shapes_of_interest.values(), mode=self.mode,
                                          linear_deflection=self.linear_deflection)
        return shapes_of_interest


class ExportTo3mfCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str],
                 tolerance: float = 0.1, angular_tolerance: float = 0.1, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.tolerance = tolerance
        self.angular_tolerance = angular_tolerance
        self.shapes_to_export: list[str] = shapes_to_export \
            if shapes_to_export is not None else [None]
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"converting shapes '{', '.join(shapes_of_interest.keys())}' to .3mf")

        from cadquery import exporters
        ass = cq.Assembly()
        for name, shape in shapes_of_interest.items():
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.3mf")
            logging.debug(f"writing model to '{step_path}'")
            exporters.export(shape, step_path,
                             tolerance=self.tolerance, angularTolerance=self.angular_tolerance)
            ass.add(shape)

        #step_path = os.path.join(self.file_path, f"{self.identifier}.3mf", exporters.ExportTypes.STEP)
        #exporters.assembly.exportAssembly(ass, step_path,
        #                 tolerance=self.tolerance, angularTolerance=self.angular_tolerance)
        #logging.debug(f"writing model to '{step_path}'")

        return shapes_of_interest


# === END basic import export operations ===

class ServoImporterCreator(AbstractShapeCreator):

    def __init__(self, creator_id: str, servo_feature: str, servo_stamp: str, servo_filling: str, servo_model: str,
                 servo_idx: int, reverse_model=False, servo_information: dict[int, ServoInformation] = None,
                 mirror_model_by_plane="", loglevel=logging.INFO):
        self.mirror_model_by_plane = mirror_model_by_plane
        self.reverse_model = reverse_model
        self.servo_idx = servo_idx
        self.servo_model = servo_model
        self._servo_information = servo_information
        self.servo_filling = servo_filling
        self.servo_stamp = servo_stamp
        self.servo_feature = servo_feature
        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"importing servo model '{self.identifier}' --> '{self.identifier}.stamp, "
                     f"{self.identifier}.filling, {self.identifier}.feature, {self.identifier}.model'")
        servo = self._servo_information[self.servo_idx]
        shapes: list[Workplane] = []
        for file in [self.servo_stamp, self.servo_filling, self.servo_feature]:
            self.import_servo_shape(file, shapes, servo)
        self.import_servo_shape(self.servo_model, shapes, servo, mirroring=self.mirror_model_by_plane)
        dict = {f"{self.identifier}.stamp": shapes[0],
                f"{self.identifier}.filling": shapes[1],
                f"{self.identifier}.feature": shapes[2],
                f"{self.identifier}.model": shapes[3]}
        for k, v in dict.items():
            if v is not None:
                v.display(name=k, severity=logging.DEBUG)

        return dict

    def import_servo_shape(self, file, shapes, servo, mirroring=""):
        if file is None:
            shapes.append(None)
        else:
            if Path(file).suffix.lower() in [".iges", ".igs"]:
                shapes.append(IgesImportCreator.iges_importer(file))
            elif Path(file).suffix.lower() in [".step", ".stp"]:
                shapes.append(StepImportCreator.step_importer(file))
            else:
                logging.fatal(f"cannot load file '{file}'. suffix unknown!")

            shapes[-1] = ScaleRotateTranslateCreator.transform_by(shapes[-1], scale=1, rot_x=servo.rot_x,
                                                                  rot_y=servo.rot_y, rot_z=servo.rot_z,
                                                                  trans_x=servo.trans_x, trans_y=servo.trans_y,
                                                                  trans_z=servo.trans_z,
                                                                  mirroring=mirroring)


class ComponentImporterCreator(AbstractShapeCreator):

    def __init__(self,
                 creator_id: str,
                 component_idx: str,
                 component_file: str,
                 mirror_model_by_plane="",
                 component_information: dict[str, ComponentInformation] = None,
                 loglevel=logging.INFO):
        self.component_idx = component_idx
        self._component_information = component_information
        self.component_file = component_file
        self.mirror_model_by_plane = mirror_model_by_plane

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"importing component '{self.component_idx}' with model '{self.component_file}'"
                     f" --> '{self.identifier}'")
        from pathlib import Path

        component = self._component_information[self.component_idx]
        file = self.component_file
        if Path(file).suffix.lower() in [".iges", ".igs"]:
            shape = IgesImportCreator.iges_importer(file)
        elif Path(file).suffix.lower() in [".step", ".stp"]:
            shape = StepImportCreator.step_importer(file)
        else:
            logging.fatal(f"cannot load file '{file}'. suffix unknown!")
            raise RuntimeError(f"cannot load file '{file}'. suffix unknown!")

        shape = ScaleRotateTranslateCreator.transform_by(shape,
                                                         scale=1,
                                                         rot_x=component.rot_x,
                                                         rot_y=component.rot_y,
                                                         rot_z=component.rot_z,
                                                         trans_x=component.trans_x,
                                                         trans_y=component.trans_y,
                                                         trans_z=component.trans_z,
                                                         mirroring=self.mirror_model_by_plane) \
            .display(self.identifier, logging.DEBUG)

        return {f"{self.identifier}": shape}


class SliceShapesCreator(AbstractShapeCreator):
    """
    Slices the given shape in <number_of_parts> parts along the x-axis. And returns a dictionary with the parts.
    The naming convention for a key is <shape_identifier>[<part_number>], e.g. {"fuselage[0]": <CNamedShape>, "fuselage[1]": <CNamedShape>}
    """

    def __init__(self, creator_id: str, number_of_parts: int, shapes_to_slice: list[str] = None, loglevel=logging.INFO):
        self.shapes_to_slice = shapes_to_slice if shapes_to_slice is not None else [None]
        self.number_of_parts = number_of_parts
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_slice, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"slicing each shape of '{', '.join(shapes_of_interest.keys())}' in {self.number_of_parts} parts")

        from Extra.ShapeSlicer import ShapeSlicer
        parts: dict[str, Workplane] = {}
        for key, shape in shapes_of_interest.items():
            my_slicer = ShapeSlicer(shape, self.loglevel, self.number_of_parts)
            my_slicer.slice_by_cut(self.loglevel)
            for i, s in enumerate(my_slicer.parts_list):
                parts[f"{key}[{i}]"] = s
                ConstructionStepsViewer.instance().display_this_shape(s, logging.DEBUG, msg=f"{key}[{i}]")
        return parts


class FullWingLoftShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 right_main_wing_index: int,
                 cpacs_configuration=None,
                 loglevel=logging.INFO
                 ):
        self.right_main_wing_index = right_main_wing_index
        self._cpacs_configuration = cpacs_configuration
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating wing loft/hull with index {self.right_main_wing_index} --> '{self.identifier}'")

        right_wing = self._cpacs_configuration.get_wing(self.right_main_wing_index).get_loft()
        left_wing = self._cpacs_configuration.get_wing(self.right_main_wing_index).get_mirrored_loft()
        complete_wing = BooleanCADOperation.fuse_shapes(
            right_wing,
            left_wing,
            self.identifier)

        ConstructionStepsViewer.instance().display_fuse(complete_wing, right_wing, left_wing, logging.DEBUG)
        ConstructionStepsViewer.instance().display_this_shape(
            complete_wing, logging.DEBUG, msg=f"{self.identifier}")
        return {str(self.identifier): complete_wing,
                f"{self.identifier}.right": right_wing,
                f"{self.identifier}.left": left_wing}


class FullFuselageLoftShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 cpacs_configuration=None, loglevel=logging.INFO):
        self.fuselage_index = fuselage_index
        self._cpacs_configuration = cpacs_configuration
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating wing loft/hull with index {self.fuselage_index} --> '{self.identifier}'")
        full_fuselage_loft = self._cpacs_configuration.get_fuselage(self.fuselage_index).get_loft()

        ConstructionStepsViewer.instance().display_this_shape(full_fuselage_loft, logging.DEBUG,
                                                              msg=f"{self.identifier}")
        return {str(self.identifier): full_fuselage_loft}

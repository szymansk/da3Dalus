from typing import Optional
import logging
logger = logging.getLogger(__name__)

from cad_designer.aerosandbox.convert2aerosandbox import convert_step_to_asb_fuselage

import aerosandbox as asb

class FuselageConfiguration:
    #TODO generate fuselage from XSecs

    def __init__(self,
                 name: str):
        self.name: str = name
        self.asb_fuselage: Optional[asb.Fuselage] = None
        self._step_file: Optional[str] = None
        self._step_scale: Optional[float] = None
        self._number_of_slices: Optional[int] = None
        pass

    def __getstate__(self):
        """Return a dictionary of serializable attributes for JSON serialization."""
        data = {
            "name": self.name,
            "step_file": self._step_file,
            "step_scale": self._step_scale,
            "number_of_slices": self._number_of_slices,
        }

        # If we have an asb_fuselage, we need to serialize its properties
        if self.asb_fuselage:
            data["asb_fuselage"] = {
                "name": self.asb_fuselage.name,
                "color": self.asb_fuselage.color,
                "xsecs": [
                    {
                        "xyz_c": xsec.xyz_c.tolist() if hasattr(xsec.xyz_c, 'tolist') else xsec.xyz_c,
                        "xyz_normal": xsec.xyz_normal.tolist() if hasattr(xsec.xyz_normal, 'tolist') else xsec.xyz_normal,
                        "height": xsec.height,
                        "width": xsec.width,
                        "shape": xsec.shape,
                    }
                    for xsec in self.asb_fuselage.xsecs
                ]
            }

        return data

    @staticmethod
    def from_json_dict(data: dict) -> 'FuselageConfiguration':
        """
        Create a FuselageConfiguration from a JSON dictionary.

        Args:
            data: Dictionary containing the FuselageConfiguration data.

        Returns:
            A new FuselageConfiguration instance.
        """
        fuselage = FuselageConfiguration(name=data.get("name", ""))

        # If we have asb_fuselage data, recreate the asb.Fuselage object
        if "asb_fuselage" in data:
            import numpy as np
            asb_data = data["asb_fuselage"]

            # Create cross-sections
            xsecs = []
            for xsec_data in asb_data.get("xsecs", []):
                xsec = asb.FuselageXSec(
                    xyz_c=np.array(xsec_data.get("xyz_c", [0, 0, 0])),
                    xyz_normal=np.array(xsec_data.get("xyz_normal", [1., 0, 0])),
                    height=xsec_data.get("height", 0),
                    width=xsec_data.get("width", 0),
                )
                xsecs.append(xsec)

            # Create the fuselage
            fuselage.asb_fuselage = asb.Fuselage(
                name=asb_data.get("name", ""),
                color=asb_data.get("color", ""),
                xsecs=xsecs
            )

        return fuselage

    @staticmethod
    def from_json(file_path: str) -> 'FuselageConfiguration':
        """
        Load a FuselageConfiguration from a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            A new FuselageConfiguration instance.
        """
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return FuselageConfiguration.from_json_dict(data)

    def save_to_json(self, file_path: str) -> None:
        """
        Save the FuselageConfiguration to a JSON file.

        Args:
            file_path: Path to the JSON file.
        """
        import json
        with open(file_path, 'w') as f:
            json.dump(self.__getstate__(), f, indent=4)

    @staticmethod
    def from_step_file(step_file: str, scale: float = 1.0, number_of_slices: int=100, name: str=None) -> "FuselageConfiguration":
        """Creates a FuselageConfiguration object from a STEP file"""
        MM_TO_M = 1.0e-3
        fuselage = convert_step_to_asb_fuselage(
            step_file=step_file,
            number_of_slices=number_of_slices,
            scale=scale*MM_TO_M,
        )
        fuselage.analysis_specific_options= {
                dict(panel_resolution=24, panel_spacing="cosine")
            }

        if len(fuselage) == 0:
            logger.error(f"Failed to convert {step_file} to an Aerosandbox fuselage.")
            logger.error("Please check the file and try again.")
            raise ValueError(f"Failed to convert {step_file} to an Aerosandbox fuselage.")
        elif len(fuselage) > 1:
            logger.warning("More than one fuselage found in the STEP file. Only the first one found will be used.")

        _name = step_file.split("/")[-1].split(".")[0] if name is None else name
        obj = FuselageConfiguration(name=_name)
        obj.asb_fuselage = fuselage[0]
        obj._step_file = step_file
        obj._step_scale = scale
        obj._number_of_slices = number_of_slices
        return obj

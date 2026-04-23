from __future__ import annotations

from functools import cached_property
from typing import Any
import json
import os
import zipfile

from cad_designer.aerosandbox.aerodynamic_calculations import calculate_cl_max, calculate_stall_velocity, \
    calculate_CL_per_CD_max, best_range_speed, analyze_static_longitudinal_stability, compute_derivative
from cad_designer.aerosandbox.classification import classify_Cm_alpha, classify_Cl_beta, classify_Cn_beta
from cad_designer.airplane.aircraft_topology.fuselage.FuselageConfiguration import FuselageConfiguration
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration

import aerosandbox as asb
import numpy as np


class AirplaneConfiguration:

    def __init__(self,
                 name: str,
                 total_mass_kg: float,
                 wings: list[WingConfiguration],
                 fuselages: list[FuselageConfiguration] | None = None,
                 ):
        self.name: str = name
        self.total_mass: float = total_mass_kg
        self.wings: list[WingConfiguration] = wings
        self.fuselages: list[FuselageConfiguration] | None = fuselages

        self._main_wing_index = 0
        self._main_wing = self.wings[self._main_wing_index]

    def to_dict(self) -> dict[str, Any]:
        """Convert the AirplaneConfiguration to a dictionary for JSON serialization."""
        data = {
            "name": self.name,
            "total_mass_kg": self.total_mass,
            "wings": [wing.__getstate__() for wing in self.wings],
        }

        if self.fuselages:
            data["fuselages"] = [fuselage.__getstate__() for fuselage in self.fuselages]

        return data

    def save_to_json(self, file_path: str) -> None:
        """Save the AirplaneConfiguration to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    def save_to_zip(self, zip_path: str) -> None:
        """
        Save the AirplaneConfiguration to a zip file with directories for wings and fuselages.
        Each object is saved individually in JSON format.
        """
        # Create temporary directory structure
        temp_dir = os.path.join(os.path.dirname(zip_path), "temp_airplane_config")
        wings_dir = os.path.join(temp_dir, "wings")
        fuselages_dir = os.path.join(temp_dir, "fuselages")

        # Create directories if they don't exist
        os.makedirs(wings_dir, exist_ok=True)
        os.makedirs(fuselages_dir, exist_ok=True)

        # Save main configuration
        main_config = {
            "name": self.name,
            "total_mass_kg": self.total_mass,
            "wings": [f"wings/wing_{i}.json" for i in range(len(self.wings))],
            "fuselages": [f"fuselages/fuselage_{i}.json" for i in range(len(self.fuselages))] if self.fuselages else []
        }

        with open(os.path.join(temp_dir, "config.json"), 'w') as f:
            json.dump(main_config, f, indent=4)

        # Save wings
        for i, wing in enumerate(self.wings):
            wing_path = os.path.join(wings_dir, f"wing_{i}.json")
            with open(wing_path, 'w') as f:
                json.dump(wing.__getstate__(), f, indent=4)

        # Save fuselages if they exist
        if self.fuselages:
            for i, fuselage in enumerate(self.fuselages):
                fuselage_path = os.path.join(fuselages_dir, f"fuselage_{i}.json")
                with open(fuselage_path, 'w') as f:
                    json.dump(fuselage.__getstate__(), f, indent=4)

        # Create zip file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir)

    @staticmethod
    def from_json(file_path: str) -> 'AirplaneConfiguration':
        """Load an AirplaneConfiguration from a JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        wings = [WingConfiguration.from_json_dict(wing_data) for wing_data in data.get("wings", [])]
        fuselages = [FuselageConfiguration.from_json_dict(fuselage_data) for fuselage_data in
                     data.get("fuselages", [])] if "fuselages" in data else None

        return AirplaneConfiguration(
            name=data["name"],
            total_mass_kg=data["total_mass_kg"],
            wings=wings,
            fuselages=fuselages
        )

    @staticmethod
    def from_zip(zip_path: str) -> 'AirplaneConfiguration':
        """
        Load an AirplaneConfiguration from a zip file.
        The zip file should contain a config.json file and directories for wings and fuselages.
        """
        # Create temporary directory to extract files
        temp_dir = os.path.join(os.path.dirname(zip_path), "temp_extract")
        os.makedirs(temp_dir, exist_ok=True)

        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(temp_dir)

        # Load main configuration
        with open(os.path.join(temp_dir, "config.json"), 'r') as f:
            config = json.load(f)

        # Load wings
        wings = []
        for wing_path in config["wings"]:
            with open(os.path.join(temp_dir, wing_path), 'r') as f:
                wing_data = json.load(f)
            wings.append(WingConfiguration.from_json_dict(wing_data))

        # Load fuselages if they exist
        fuselages = None
        if "fuselages" in config and config["fuselages"]:
            fuselages = []
            for fuselage_path in config["fuselages"]:
                with open(os.path.join(temp_dir, fuselage_path), 'r') as f:
                    fuselage_data = json.load(f)
                fuselages.append(FuselageConfiguration.from_json_dict(fuselage_data))

        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir)

        return AirplaneConfiguration(
            name=config["name"],
            total_mass_kg=config["total_mass_kg"],
            wings=wings,
            fuselages=fuselages
        )

    @cached_property
    def asb_airplane(self) -> asb.Airplane:
        """Converts the AirplaneConfiguration object to an Aerosandbox airplane object"""
        mm_to_m_scale = 1.0e-3
        wings = [wing.asb_wing(scale=mm_to_m_scale) for wing in self.wings]
        fuselages = [fuselage.asb_fuselage for fuselage in self.fuselages] if self.fuselages else []

        asb_airplane = asb.Airplane(
            name=self.name,
            xyz_ref=None,
            wings=wings,
            fuselages=fuselages,
            propulsors=None,
            analysis_specific_options={
                asb.AVL: {
                    "profile_drag_coefficient": 0.,
                }
            }
        )

        self._asb_main_wing = asb_airplane.wings[self._main_wing_index]
        return asb_airplane

    def airplane_analysis(self, CG_percent_MAC_in_front_of_NP: float = 12.5, elevation_m: float = 0,
                          rho_kgm3: float = 1.225, gravity: float = 9.81):
        alpha = np.linspace(-20, 20, 300)
        beta = np.linspace(-5, 5, 100)

        aero = asb.AeroBuildup(
            airplane=self.asb_airplane,
            op_point=asb.OperatingPoint(
                velocity=10,  # m/s is not important at this point
                alpha=alpha,
                beta=0
            ),
            model_size='xsmall'
        ).run()

        # calculate stall_alpha and CL_max
        stall_alpha, CL_max = calculate_cl_max(alpha, aero["CL"])

        # best travel/glide alpha
        aoa_at_best_LD, max_LD, CL_at_max_LD = calculate_CL_per_CD_max(alpha, aero["CL"], aero["CD"])

        # stability analysis at best travel/glide alpha
        aero_beta = asb.AeroBuildup(
            airplane=self.asb_airplane,
            op_point=asb.OperatingPoint(
                velocity=10,  # m/s is not important at this point
                alpha=aoa_at_best_LD,
                beta=beta
            ),
            model_size='xsmall'
        ).run()

        # calculate travel and stall speed over a range of total masses
        stall_velocity_m_per_s = []
        travel_velocity_m_per_s = []

        masses = np.linspace(self.total_mass * 0.5, self.total_mass * 1.5, 100)
        for mass in masses:
            stall_velocity_m_per_s.append(
                calculate_stall_velocity(CL_max, mass_kg=mass, wing_area_m2=self._asb_main_wing.area()))
            travel_velocity_m_per_s.append(
                best_range_speed(CL_at_max_LD, mass_kg=mass, wing_area_m2=self._asb_main_wing.area(), rho=rho_kgm3,
                                 gravity=gravity))

        from cad_designer.airplane.aircraft_topology.models.analysis_model import (
            AircraftSummaryModel, AircraftModel, EnvironmentModel, ControlSurfacesModel,
            WingGeometryModel, AerodynamicsModel, EfficiencyModel, StabilityModel
        )
        summary_model = AircraftSummaryModel(
            aircraft=AircraftModel(
                name=self.name,
                mass_kg=self.total_mass,
                wing_area_m2=self._asb_main_wing.area(),
                wing_span_m=self._asb_main_wing.span(),
                wing_chord_m=self._asb_main_wing.mean_geometric_chord(),
                MAC_m=self._asb_main_wing.mean_aerodynamic_chord(),
                static_margin_in_percent_MAC=CG_percent_MAC_in_front_of_NP,
                NP_m=list(self.asb_airplane.aerodynamic_center()),
                airfoil_root=self._main_wing.segments[0].root_airfoil.airfoil.split("/")[-1].split(".")[0],
                airfoil_tip=self._main_wing.segments[-1].tip_airfoil.airfoil.split("/")[-1].split(".")[0],
            ),
            environment=EnvironmentModel(
                rho_kgm3=rho_kgm3,
                gravity=gravity,
                elevation_m=elevation_m,
            ),
            control_surfaces=ControlSurfacesModel(
                flaps_installed=False,
                flap_type="plain",
                flap_deflection_deg=0,
                flap_area_m2=self._asb_main_wing.control_surface_area(by_name="flaps"),
                aileron_area_m2=self._asb_main_wing.control_surface_area(by_name="aileron"),
            ),
            wing_geometry=WingGeometryModel(
                taper_ratio=self._asb_main_wing.taper_ratio(),
                sweep_deg=self._asb_main_wing.mean_sweep_angle(),
                dihedral_deg=self._asb_main_wing.mean_dihedral_angle(),
                washout_deg=sum(seg.tip_airfoil.incidence for seg in self._main_wing.segments) +
                            self._main_wing.segments[0].root_airfoil.incidence,
                incidence_deg=self._asb_main_wing.mean_twist_angle(),
            ),
            aerodynamics=AerodynamicsModel(
                alpha_range_deg=list(alpha),
                F_g_curve_alpha=list(aero["F_g"]),
                F_b_curve_alpha=list(aero["F_b"]),
                F_w_curve_alpha=list(aero["F_w"]),
                M_g_curve_alpha=list(aero["M_g"]),
                M_b_curve_alpha=list(aero["M_b"]),
                M_w_curve_alpha=list(aero["M_w"]),
                L_lift_force_N_curve_alpha=list(aero["L"]),
                Y_side_force_N_curve_alpha=list(aero["Y"]),
                D_drag_force_N_curve_alpha=list(aero["D"]),
                l_b_rolling_moment_Nm_curve_alpha=list(aero["l_b"]),
                m_b_pitching_moment_Nm_curve_alpha=list(aero["m_b"]),
                n_b_yawing_moment_Nm_curve_alpha=list(aero["n_b"]),
                CL_lift_coefficient_curve_alpha=list(aero["CL"]),
                CY_sideforce_coefficient_curve_alpha=list(aero["CY"]),
                CD_drag_coefficient_curve_alpha=list(aero["CD"]),
                Cl_rolling_moment_curve_alpha=list(aero["Cl"]),
                Cm_pitching_moment_curve_alpha=list(aero["Cm"]),
                Cn_yawing_moment_curve_alpha=list(aero["Cn"]),
            ),
            efficiency=EfficiencyModel(
                masses_kg=list(masses),
                stall_velocity_m_per_s_curve_masses_kg=list(stall_velocity_m_per_s),
                travel_velocity_m_per_s_curve_masses_kg=list(travel_velocity_m_per_s),
                stall_velocity_m_per_s=calculate_stall_velocity(
                    CL_max, mass_kg=self.total_mass, wing_area_m2=self._asb_main_wing.area()
                ),
                travel_velocity_m_per_s=best_range_speed(
                    CL_at_max_LD, mass_kg=self.total_mass, wing_area_m2=self._asb_main_wing.area(),
                    rho=rho_kgm3, gravity=gravity
                ),
                alpha_at_stall_deg=stall_alpha,
                alpha_at_best_LD_deg=aoa_at_best_LD,
                max_LD_ratio=max_LD,
                CL_at_max_LD=CL_at_max_LD,
            ),
            stability=StabilityModel(
                static_longitudinal_stability_best_alpha=classify_Cm_alpha(compute_derivative(alpha, aero["Cm"])),
                static_lateral_stability_best_alpha=classify_Cl_beta(compute_derivative(beta, aero_beta["Cl"])),
                static_directional_stability_best_alpha=classify_Cn_beta(compute_derivative(beta, aero_beta["Cn"])),
            )
        )

        return summary_model

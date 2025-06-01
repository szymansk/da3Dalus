"""
Test for AvlAnalysisModel

This test file demonstrates how to create an AvlAnalysisModel instance from a dictionary
and verify that it's correctly populated with all the data.

Note: This test is designed to be run in an environment with all the required dependencies.
Due to the current environment limitations, this is provided as a reference implementation.

To run this test, you would need:
1. Python 3.x
2. pydantic
3. All other dependencies required by the cad_designer module

Usage:
    python test_avl_analysis_model.py
"""
from cad_designer.airplane.aircraft_topology.models.analysis_model import AnalysisModel


# The following imports would be needed in a real environment
# import os
# import sys
# import json
# from pathlib import Path
# 
# # Add the project root to the Python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# 
# from cad_designer.airplane.aircraft_topology.models.analysis_model import AvlAnalysisModel

def test_avl_analysis_model_from_dict():
    """Test creating an AvlAnalysisModel from a dictionary."""
    print("Testing AvlAnalysisModel creation from dictionary...")

    # Test data from the issue description
    test_data = {'Surfaces': 5.0,
                 'Strips': 60.0,
                 'Vortices': 720.0,
                 'Sref': 0.15006,
                 'Cref': 0.183,
                 'Bref': 0.82,
                 'Xref': 0.0,
                 'Yref': 0.0,
                 'Zref': 0.0,
                 'pb/2V': -0.0,
                 "p'b/2V": -0.0,
                 'qc/2V': 0.0,
                 'rb/2V': -0.0,
                 "r'b/2V": -0.0,
                 'CDvis': 0.0,
                 'CDind': 0.0337564,
                 'CLff': 0.482,
                 'CDff': 0.0167172,
                 'CYff': -0.00074,
                 'e': 0.9872,
                 'flaps': 1.0,
                 'aileron': 0.0,
                 'elevator': 0.0,
                 'rudder': 0.0,
                 'CLa': 4.655086,
                 'CLb': -5.7e-05,
                 'CYa': -9.9e-05,
                 'CYb': -0.355659,
                 'Cla': 0.000673,
                 'Clb': -0.09859,
                 'Cma': -6.276607,
                 'Cmb': 0.000258,
                 'Cna': 9.2e-05,
                 'Cnb': 0.213175,
                 'CLp': 4.2e-05,
                 'CLq': 20.154713,
                 'CLr': 0.000111,
                 'CYp': 0.124251,
                 'CYq': -0.000957,
                 'CYr': 0.486204,
                 'Clp': -0.362175,
                 'Clq': 0.000347,
                 'Clr': 0.182851,
                 'Cmp': -0.000194,
                 'Cmq': -33.791439,
                 'Cmr': -0.000501,
                 'Cnp': -0.090168,
                 'Cnq': 0.000832,
                 'Cnr': -0.38484,
                 'CLd01': 0.014286,
                 'CLd02': -0.0,
                 'CLd03': 0.010476,
                 'CLd04': 1e-06,
                 'CYd01': -0.0,
                 'CYd02': -7e-06,
                 'CYd03': -0.0,
                 'CYd04': -0.004608,
                 'Cld01': 0.0,
                 'Cld02': -7.4e-05,
                 'Cld03': 0.0,
                 'Cld04': -0.000386,
                 'Cmd01': -0.022641,
                 'Cmd02': 0.0,
                 'Cmd03': -0.035227,
                 'Cmd04': -5e-06,
                 'Cnd01': 0.0,
                 'Cnd02': 2e-06,
                 'Cnd03': -0.0,
                 'Cnd04': 0.003829,
                 'CDffd01': 0.001033,
                 'CDffd02': 0.0,
                 'CDffd03': 0.000711,
                 'CDffd04': 9e-06,
                 'ed01': -0.002796,
                 'ed02': -0.0,
                 'ed03': 0.001981,
                 'ed04': -0.000505,
                 'Xnp': 0.246745,
                 'alpha': 5.0,
                 'beta': 0.0,
                 'mach': 0.044,
                 'CX': 0.01063,
                 'Cl': -6e-05,
                 "Cl'": -1e-05,
                 'CY': -0.00073,
                 'Cm': -0.64608,
                 'CZ': -0.50876,
                 'Cn': 0.00064,
                 "Cn'": 0.00064,
                 'CL': 0.50775,
                 'CD': 0.03376,
                 'p': -0.0,
                 'q': 0.0,
                 'r': -0.0,
                 'L': 10.500335753578634,
                 'Y': -0.015096494534933336,
                 'D': 0.6981611719169171,
                 'l_b': -0.0010174623713955072,
                 'm_b': -2.4450663063160825,
                 'n_b': 0.010852931961552077,
                 'Clb Cnr / Clr Cnb': 0.9733733715379989,
                 'F_w': [-0.6981611719169171, -0.015096494534933336, -10.500335753578634],
                 'F_b': (0.21966010382578438, -0.015096494534933336, -10.521227561394223),
                 'F_g': (-0.21966010382578438, -0.015096494534933336, 10.521227561394223),
                 'M_b': [-0.0010174623713955072, -2.4450663063160825, 0.010852931961552077],
                 'M_g': (0.0010174623713955072, -2.4450663063160825, -0.010852931961552077),
                 'M_w': (-6.769527379318896e-05, -2.4450663063160825, 0.010900310967545396)}

    # Create the model from the dictionary
    model = AnalysisModel.from_dict(test_data)
    print("Successfully created AvlAnalysisModel from dictionary")

    # Verify reference model
    print("\nVerifying reference model...")
    assert model.reference.Bref == 0.82, f"Expected Bref=0.82, got {model.reference.Bref}"
    assert model.reference.Cref == 0.183, f"Expected Cref=0.183, got {model.reference.Cref}"
    assert model.reference.Sref == 0.15006, f"Expected Sref=0.15006, got {model.reference.Sref}"
    assert model.reference.Xnp == 0.246745, f"Expected Xnp=0.246745, got {model.reference.Xnp}"
    print("Reference model verified successfully")

    # Verify forces model
    print("\nVerifying forces model...")
    assert model.forces.L == 10.500335753578634, f"Expected L=10.500335753578634, got {model.forces.L}"
    assert model.forces.D == 0.6981611719169171, f"Expected D=0.6981611719169171, got {model.forces.D}"
    assert model.forces.Y == -0.015096494534933336, f"Expected Y=-0.015096494534933336, got {model.forces.Y}"
    print("Forces model verified successfully")

    # Verify moments model
    print("\nVerifying moments model...")
    assert model.moments.l_b == -0.0010174623713955072, f"Expected l_b=-0.0010174623713955072, got {model.moments.l_b}"
    assert model.moments.m_b == -2.4450663063160825, f"Expected m_b=-2.4450663063160825, got {model.moments.m_b}"
    assert model.moments.n_b == 0.010852931961552077, f"Expected n_b=0.010852931961552077, got {model.moments.n_b}"
    print("Moments model verified successfully")

    # Verify coefficients model
    print("\nVerifying coefficients model...")
    assert model.coefficients.CL == 0.50775, f"Expected CL=0.50775, got {model.coefficients.CL}"
    assert model.coefficients.CD == 0.03376, f"Expected CD=0.03376, got {model.coefficients.CD}"
    assert model.coefficients.Cm == -0.64608, f"Expected Cm=-0.64608, got {model.coefficients.Cm}"
    print("Coefficients model verified successfully")

    # Verify derivatives model
    print("\nVerifying derivatives model...")
    assert model.derivatives.CLa == 4.655086, f"Expected CLa=4.655086, got {model.derivatives.CLa}"
    assert model.derivatives.Cmq == -33.791439, f"Expected Cmq=-33.791439, got {model.derivatives.Cmq}"
    assert model.derivatives.Cnb == 0.213175, f"Expected Cnb=0.213175, got {model.derivatives.Cnb}"
    print("Derivatives model verified successfully")

    # Verify control surfaces model
    print("\nVerifying control surfaces model...")
    assert model.control_surfaces.aileron == 0.0, f"Expected aileron=0.0, got {model.control_surfaces.aileron}"
    assert model.control_surfaces.flaps == 1.0, f"Expected flaps=1.0, got {model.control_surfaces.flaps}"

    # Verify control surface list
    assert len(
        model.control_surfaces.control_surfaces) == 4, f"Expected 4 control surfaces, got {len(model.control_surfaces.control_surfaces)}"

    # Check control surface names and values
    expected_names = ['elevator', 'rudder', 'aileron', 'flaps']
    for i, cs in enumerate(model.control_surfaces.control_surfaces):
        print(f"Control surface {i + 1}: {cs.name}")
        assert cs.name in expected_names, f"Unexpected control surface name: {cs.name}"

        # Verify specific control surface values
        if cs.name == 'flaps':
            assert cs.ed == -0.002796, f"Expected ed=-0.002796 for elevator, got {cs.ed}"
            assert cs.CLd == 0.014286, f"Expected CLd=0.014286 for elevator, got {cs.CLd}"
            assert cs.Cmd == -0.022641, f"Expected Cmd=-0.022641 for elevator, got {cs.Cmd}"
        elif cs.name == 'aileron':
            assert cs.ed == -0.0, f"Expected ed=-0.0 for rudder, got {cs.ed}"
            assert cs.CYd == -7e-06, f"Expected CYd=-7e-06 for rudder, got {cs.CYd}"
            assert cs.Cnd == 2e-06, f"Expected Cnd=2e-06 for rudder, got {cs.Cnd}"

    print("Control surfaces model verified successfully")

    # Verify flight condition model
    print("\nVerifying flight condition model...")
    assert model.flight_condition.alpha == 5.0, f"Expected alpha=5.0, got {model.flight_condition.alpha}"
    assert model.flight_condition.beta == 0.0, f"Expected beta=0.0, got {model.flight_condition.beta}"
    assert model.flight_condition.mach == 0.044, f"Expected mach=0.044, got {model.flight_condition.mach}"
    print("Flight condition model verified successfully")

    print("\nAll tests passed successfully!")


if __name__ == "__main__":
    test_avl_analysis_model_from_dict()

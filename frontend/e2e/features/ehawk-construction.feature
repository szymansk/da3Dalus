Feature: eHawk Designer Workflow
  As a drone engineer
  I want to construct an eHawk main wing step by step through the workbench UI
  So that I can export a printable CAD model

  This mirrors the backend test in test_ehawk_designer_workflow_integration.py
  using the exact same parameter values from ehawk_workflow_helpers._build_main_wing.

  Background:
    Given the backend is running on "http://localhost:8000"
    And I am on the workbench

  # ── Stage 0: Create aeroplane ──────────────────────────────────

  Scenario: Stage 0 — Create a new aeroplane
    When I create an aeroplane named "eHawk designer workflow"
    Then the API returns status 201
    And the aeroplane has a valid UUID

  # ── Stage 1: Bare aerodynamic wing via PUT /wings/{name} ───────
  #
  # Root segment: chord 162mm, airfoil mh32, dihedral 1°, length 20mm
  # Then 10 more segments added stepwise (see _build_main_wing).
  # The asb schema carries xyz_le, chord, twist, airfoil per x_sec.

  Scenario: Stage 1 — Create bare aerodynamic wing
    Given an aeroplane "eHawk designer workflow" exists
    When I create wing "main_wing" with the eHawk geometry:
      | field     | value |
      | symmetric | true  |
      | airfoil   | mh32  |
    And the wing has the following root segment:
      | field                          | value |
      | root_airfoil_chord             | 162.0 |
      | root_airfoil_dihedral_degrees  | 1     |
      | root_airfoil_incidence         | 0     |
      | tip_airfoil_chord              | 162.0 |
      | tip_airfoil_incidence          | 0     |
      | length                         | 20.0  |
      | sweep                          | 0     |
      | number_interpolation_points    | 201   |
    And I add segment 1 with:
      | field                          | value |
      | length                         | 200   |
      | sweep                          | 2.5   |
      | tip_airfoil_chord              | 157   |
      | tip_airfoil_incidence          | 0     |
    And I add segment 2 with:
      | field                          | value |
      | length                         | 250   |
      | sweep                          | 8     |
      | tip_airfoil_incidence          | 0     |
    And I add segment 3 with:
      | field                          | value |
      | length                         | 75    |
      | sweep                          | 5     |
      | tip_airfoil_incidence          | 0     |
    And I add segment 4 with:
      | field                          | value |
      | length                         | 85    |
      | sweep                          | 11    |
      | tip_airfoil_incidence          | 0     |
    And I add segment 5 with:
      | field                          | value |
      | length                         | 40    |
      | sweep                          | 12    |
      | tip_airfoil_incidence          | 0     |
    And I add segment 6 with:
      | field                          | value |
      | length                         | 20    |
      | sweep                          | 7.5   |
      | tip_airfoil_chord              | 79.5  |
      | tip_airfoil_dihedral_degrees   | 5     |
      | tip_airfoil_incidence          | 0     |
    And I add tip segment 7 with:
      | field                          | value |
      | length                         | 15    |
      | sweep                          | 7.5   |
      | tip_airfoil_chord              | 71.0  |
      | tip_airfoil_dihedral_degrees   | 5     |
      | tip_type                       | flat  |
    And I add tip segment 8 with:
      | field                          | value |
      | length                         | 15    |
      | sweep                          | 10    |
      | tip_airfoil_chord              | 55.0  |
      | tip_airfoil_dihedral_degrees   | 5     |
      | tip_type                       | flat  |
    And I add tip segment 9 with:
      | field                          | value |
      | length                         | 15    |
      | sweep                          | 12.5  |
      | tip_airfoil_chord              | 42.5  |
      | tip_airfoil_dihedral_degrees   | 10    |
      | tip_type                       | flat  |
    And I add tip segment 10 with:
      | field                          | value |
      | length                         | 10    |
      | sweep                          | 15    |
      | tip_airfoil_chord              | 30.5  |
      | tip_airfoil_dihedral_degrees   | 15    |
      | tip_type                       | flat  |
    And I add tip segment 11 with:
      | field                          | value |
      | length                         | 5     |
      | sweep                          | 17.5  |
      | tip_airfoil_chord              | 12.0  |
      | tip_type                       | flat  |
    Then the wing "main_wing" has 12 cross sections
    And all cross sections have no spars
    And all cross sections have no trailing edge devices

  # ── Stage 1 STL checkpoint ─────────────────────────────────────

  Scenario: Stage 1 STL — Export bare wing loft
    Given the "eHawk designer workflow" has wing "main_wing"
    When I export "main_wing" as "wing_loft/stl"
    And I wait for the export task to complete within 240 seconds
    Then the export zip contains at least 1 STL file
    And the STL has at least 100 triangles
    And the STL bounding box span is at least 500 mm

  # ── Stage 2: First aero check (alpha sweep) ────────────────────

  Scenario: Stage 2 — Run alpha sweep on bare wing
    Given the "eHawk designer workflow" has wing "main_wing"
    When I run an alpha sweep with:
      | field           | value        |
      | analysis_tool   | aero_buildup |
      | velocity_m_s    | 20.0         |
      | alpha_start_deg | -4.0         |
      | alpha_end_deg   | 8.0          |
      | alpha_step_deg  | 2.0          |
      | beta_deg        | 0.0          |
      | xyz_ref_m       | [0,0,0]      |
    Then the alpha sweep returns status 200 or 202

  # ── Stage 3: Add aileron TED on segments 2–5 ───────────────────
  #
  # Segment 2 is the primary aileron with full TED details:
  #   rel_chord_root=0.8, rel_chord_tip=0.8, hinge_spacing=0.5,
  #   side_spacing_root=2.0, side_spacing_tip=2.0, servo=1,
  #   servo_placement="top", rel_chord_servo_position=0.414,
  #   rel_length_servo_position=0.486, positive/negative=35°,
  #   trailing_edge_offset_factor=1.2, hinge_type="top", symmetric=false

  Scenario: Stage 3 — Add aileron control surfaces
    Given the "eHawk designer workflow" has wing "main_wing"
    When I add a control surface on cross section 2:
      | field        | value   |
      | name         | aileron |
      | hinge_point  | 0.8     |
      | symmetric    | false   |
      | deflection   | 0.0     |
    And I set TED cad details on cross section 2:
      | field                         | value |
      | rel_chord_tip                 | 0.8   |
      | hinge_spacing                 | 0.5   |
      | side_spacing_root             | 2.0   |
      | side_spacing_tip              | 2.0   |
      | servo_placement               | top   |
      | rel_chord_servo_position      | 0.414 |
      | rel_length_servo_position     | 0.486 |
      | positive_deflection_deg       | 35    |
      | negative_deflection_deg       | 35    |
      | trailing_edge_offset_factor   | 1.2   |
      | hinge_type                    | top   |
    And I add a control surface on cross section 3:
      | field        | value   |
      | name         | aileron |
      | hinge_point  | 0.8     |
      | symmetric    | false   |
      | deflection   | 0.0     |
    And I add a control surface on cross section 4:
      | field        | value   |
      | name         | aileron |
      | hinge_point  | 0.8     |
      | symmetric    | false   |
      | deflection   | 0.0     |
    And I add a control surface on cross section 5:
      | field        | value   |
      | name         | aileron |
      | hinge_point  | 0.8     |
      | symmetric    | false   |
      | deflection   | 0.0     |
    Then the wing has 4 cross sections with trailing edge devices

  # ── Stage 3 STL checkpoint ─────────────────────────────────────

  Scenario: Stage 3 STL — Export wing loft with TEDs
    Given the "eHawk designer workflow" has wing "main_wing" with TEDs
    When I export "main_wing" as "wing_loft/stl"
    And I wait for the export task to complete within 240 seconds
    Then the export zip contains at least 1 STL file
    And the STL has at least 100 triangles

  # ── Stage 4: Re-run aero with TEDs ─────────────────────────────

  Scenario: Stage 4 — Alpha sweep with TEDs present
    Given the "eHawk designer workflow" has wing "main_wing" with TEDs
    When I run an alpha sweep with:
      | field           | value        |
      | analysis_tool   | aero_buildup |
      | velocity_m_s    | 20.0         |
      | alpha_start_deg | -4.0         |
      | alpha_end_deg   | 8.0          |
      | alpha_step_deg  | 2.0          |
      | beta_deg        | 0.0          |
      | xyz_ref_m       | [0,0,0]      |
    Then the alpha sweep returns status 200 or 202

  # ── Stage 5: Add structural spars ──────────────────────────────
  #
  # Root segment (x_sec 0) has 3 spars:
  #   spar 1: dim 4.42×4.42, pos_factor 0.25
  #   spar 2: dim 6.42×6.42, pos_factor 0.55, vector (0,1,0), length 70
  #   spar 3: dim 6.42×6.42, pos_factor 0.20, vector (0,1,0), length 70
  # Segments 1–5 have follow-mode spars.
  # Segment 6 has standard_backward spar.

  Scenario: Stage 5 — Add structural spars
    Given the "eHawk designer workflow" has wing "main_wing" with TEDs
    When I add spars on cross section 0:
      | width | height | position_factor | mode     | vector    | length |
      | 4.42  | 4.42   | 0.25            | standard |           |        |
      | 6.42  | 6.42   | 0.55            | standard | [0,1,0]   | 70     |
      | 6.42  | 6.42   | 0.20            | standard | [0,1,0]   | 70     |
    And I add spars on cross section 1:
      | width | height | position_factor | mode   | length |
      | 4.42  | 4.42   | 0.25            | follow |        |
      | 6.42  | 6.42   | 0.55            | follow | 60     |
      | 6.42  | 6.42   | 0.20            | follow | 60     |
    And I add spars on cross section 2:
      | width | height | position_factor | mode   |
      | 4.42  | 4.42   | 0.25            | follow |
    And I add spars on cross section 3:
      | width | height | position_factor | mode   |
      | 4.42  | 4.42   | 0.25            | follow |
    And I add spars on cross section 4:
      | width | height | position_factor | mode   |
      | 4.42  | 4.42   | 0.25            | follow |
    And I add spars on cross section 5:
      | width | height | position_factor | mode   |
      | 4.42  | 4.42   | 0.25            | follow |
    And I add spars on cross section 6:
      | width | height | position_factor | mode              |
      | 4.42  | 4.42   | 0.25            | standard_backward |
    Then all spar-bearing cross sections have the correct spar count

  # ── Stage 5 STL checkpoint (vase_mode_wing) ────────────────────
  #
  # Now that spars exist, vase_mode_wing is valid.
  # Requires servo_information for servo 1 (aileron on segment 2).

  Scenario: Stage 5 STL — Export vase mode wing with spars
    Given the "eHawk designer workflow" has wing "main_wing" fully configured
    When I export "main_wing" as "vase_mode_wing/stl" with servo settings:
      | field              | value |
      | layer_height       | 0.24  |
      | wall_thickness     | 0.42  |
      | rel_gap_wall       | 0.075 |
      | servo_1_length     | 23    |
      | servo_1_width      | 12.5  |
      | servo_1_height     | 31.5  |
      | servo_1_leading    | 6     |
      | servo_1_latch_z    | 14.5  |
      | servo_1_latch_x    | 7.25  |
      | servo_1_latch_t    | 2.6   |
      | servo_1_latch_l    | 6     |
      | servo_1_cable_z    | 26    |
    And I wait for the export task to complete within 240 seconds
    Then the export zip contains at least 1 STL file
    And the STL has at least 100 triangles
    And the STL bounding box span is at least 500 mm

  # ── Stage 6: Final STEP export ─────────────────────────────────

  Scenario: Stage 6 — Export printable STEP file
    Given the "eHawk designer workflow" has wing "main_wing" fully configured
    When I export "main_wing" as "vase_mode_wing/step" with the same servo settings
    And I wait for the export task to complete within 240 seconds
    Then the export zip contains at least 1 STEP file

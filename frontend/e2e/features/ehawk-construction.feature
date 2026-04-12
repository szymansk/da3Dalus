Feature: eHawk Designer Workflow — Full UI Construction
  As a drone engineer using the da3Dalus workbench
  I want to construct an eHawk main wing step by step entirely through the UI
  So that the backend DB contains a correct, fully configured eHawk

  This test mirrors the backend test_ehawk_designer_workflow_integration.py.
  Every action goes through the real browser UI — no direct API calls except
  for verification (reading back DB state to confirm correctness).

  The eHawk main wing has:
  - 12 segments (13 x_secs including terminal)
  - Root: airfoil mh32, chord 162mm, dihedral 1°, length 20mm
  - Ailerons on segments 2-5
  - 3 spars on root segment, follow-mode spars on segments 1-6
  - Symmetric wing

  Background:
    Given the backend is running
    And the frontend is running

  # ── Stage 0: Create aeroplane ──────────────────────────────────

  Scenario: Stage 0 — Create eHawk aeroplane
    Given I am on the workbench
    When I click "Create New" and enter name "eHawk E2E Test"
    Then I see the construction workbench
    And the header shows project "eHawk E2E Test"

  # ── Stage 1: Build the wing segment by segment ────────────────
  #
  # The designer creates the wing via "+ Wing", then adds segments
  # one by one using the PropertyForm in WingConfig mode.
  #
  # Root segment: chord 162mm, airfoil mh32, dihedral 1°, length 20mm
  # Segment 1: length 200mm, sweep 2.5mm, tip chord 157mm
  # Segments 2-5: aileron segments (varying length/sweep)
  # Segments 6-11: tip segments with increasing dihedral

  Scenario: Stage 1a — Create wing via UI
    Given the "eHawk E2E Test" aeroplane is selected
    When I click the "Wing" button and enter name "main_wing"
    Then the tree shows "main_wing"

  Scenario: Stage 1b — Configure root segment in WingConfig mode
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 0" in the tree
    And the property form is in "WingConfig" mode
    And I set the following WingConfig fields:
      | field                      | value |
      | root_airfoil               | mh32  |
      | root_chord                 | 162.0 |
      | tip_airfoil                | mh32  |
      | tip_chord                  | 162.0 |
      | length                     | 20.0  |
      | sweep                      | 0     |
      | dihedral                   | 1.0   |
      | incidence                  | 0     |
      | rotation_point             | 0.25  |
      | interpolation_pts          | 201   |
    And I click "Save"
    Then the save completes without error

  Scenario: Stage 1c — Add segment 1
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click "+ segment" on "main_wing"
    And I set the following WingConfig fields:
      | field          | value |
      | length         | 200   |
      | sweep          | 2.5   |
      | tip_airfoil    | mh32  |
      | tip_chord      | 157   |
    And I click "Save"
    Then the tree shows "segment 1"

  Scenario: Stage 1d — Add segment 2 with aileron
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click "+ segment" on "main_wing"
    And I set the following WingConfig fields:
      | field          | value |
      | length         | 250   |
      | sweep          | 8     |
      | tip_airfoil    | mh32  |
    And I click "Save"
    Then the tree shows "segment 2"

  # ── Stage 2: First aerodynamic check ───────────────────────────

  Scenario: Stage 2 — Run alpha sweep on the wing
    Given the "eHawk E2E Test" has wing "main_wing"
    When I click the "Analysis" step pill
    And I set the analysis parameters:
      | field       | value        |
      | velocity    | 20.0         |
      | alpha_start | -4.0         |
      | alpha_end   | 8.0          |
      | alpha_step  | 2.0          |
      | tool        | aero_buildup |
    And I click "Run Analysis"
    Then the analysis completes without error
    And the polar chart shows bars
    And the chart annotation shows a CL_max value

  # ── Stage 3: Add aileron control surfaces ──────────────────────

  Scenario: Stage 3 — Add aileron TED on segment 2
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 2" in the tree
    And I open the "Trailing Edge Device" section
    And I set the following TED fields:
      | field                       | value   |
      | name                        | aileron |
      | hinge_point                 | 0.8     |
      | rel_chord_tip               | 0.8     |
      | symmetric                   | false   |
      | servo_placement             | top     |
      | positive_deflection_deg     | 35      |
      | negative_deflection_deg     | 35      |
    And I click "Save TED"
    Then segment 2 shows an "AILERON" chip in the tree

  # ── Stage 4: Aero check with TEDs ─────────────────────────────

  Scenario: Stage 4 — Re-run alpha sweep with ailerons
    Given the "eHawk E2E Test" has wing "main_wing"
    When I click the "Analysis" step pill
    And I click "Run Analysis"
    Then the analysis completes without error

  # ── Stage 5: Add structural spars ──────────────────────────────

  Scenario: Stage 5 — Add spars on root segment
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 0" in the tree
    And I open the "Spars" section
    And I add a spar with:
      | width | height | position_factor | mode     |
      | 4.42  | 4.42   | 0.25            | standard |
    And I add a spar with:
      | width | height | position_factor | mode     | vector  | length |
      | 6.42  | 6.42   | 0.55            | standard | [0,1,0] | 70     |
    And I add a spar with:
      | width | height | position_factor | mode     | vector  | length |
      | 6.42  | 6.42   | 0.20            | standard | [0,1,0] | 70     |
    Then segment 0 shows "spars (3)" in the tree

  # ── Stage 6: 3D Preview via tessellation ────────────────────────

  @slow
  Scenario: Stage 6 — Preview 3D via tessellation
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click "Preview 3D"
    Then the tessellation progress is shown
    And the 3D viewer renders within 120 seconds

  # ── Verification: Check DB state ───────────────────────────────

  Scenario: Verify eHawk in backend DB
    Given the "eHawk E2E Test" aeroplane exists
    When I query the wing "main_wing" from the API
    Then the wing has at least 3 cross sections
    And cross section 0 has airfoil containing "mh32"
    And cross section 0 has chord approximately 0.162
    And the wing is symmetric

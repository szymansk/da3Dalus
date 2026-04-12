Feature: eHawk Designer Workflow — End-to-End
  As a drone engineer using the da3Dalus workbench
  I want to construct an eHawk main wing and run aerodynamic analysis
  So that the backend DB contains a correct, fully configured eHawk

  This test uses the real UI and real backend. No mocks, no fakes.
  The eHawk wing config is submitted via the from-wingconfig API
  (since the UI does not yet have a segment-by-segment builder),
  then verified through the UI (tree, property form, analysis).

  At the end, the backend DB MUST contain a correct eHawk aeroplane
  with main_wing (13 x_secs, mh32 airfoil, symmetric, chord ~0.162m).

  Background:
    Given the backend is running
    And the frontend is running

  # ── Stage 0: Create aeroplane via UI ───────────────────────────

  Scenario: Create eHawk aeroplane via UI
    Given I am on the workbench
    When I click "Create New" and enter name "eHawk E2E Test"
    Then I see the construction workbench
    And the header shows project "eHawk E2E Test"

  # ── Stage 1: Load eHawk wing geometry ──────────────────────────
  #
  # The full eHawk wing config (from ehawk_workflow_helpers._build_main_wing)
  # is submitted via POST /from-wingconfig with exact parameters:
  #   Root: chord 162mm, airfoil mh32, dihedral 1°, length 20mm
  #   11 segments total (see fixture file for all parameters)
  #   Includes spars, ailerons on segments 2-5, tip segments 6-11

  Scenario: Load eHawk wing via from-wingconfig API
    Given the "eHawk E2E Test" aeroplane exists
    When I submit the eHawk wing config for "main_wing" via API
    And I reload the workbench
    Then the tree shows "main_wing" under the aeroplane

  # ── Stage 2: Verify wing in UI ─────────────────────────────────

  Scenario: Verify segment 0 properties in the UI
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 0" in the tree
    Then the property form shows "segment 0"
    And the airfoil field shows "mh32"
    And the chord field shows a value greater than 0

  # ── Stage 3: Run analysis via UI ───────────────────────────────

  Scenario: Run alpha sweep via the analysis page
    Given the "eHawk E2E Test" has wing "main_wing"
    When I click the "Analysis" step pill
    Then I see the analysis page
    When I click "Run Analysis"
    Then the analysis completes without error
    And the polar chart shows bars

  # ── Stage 4: Verify eHawk in backend DB ────────────────────────
  #
  # These assertions verify the DB state matches the exact
  # eHawk parameters from _build_main_wing:
  #   - 13 x_secs (12 segments + 1 terminal)
  #   - Root airfoil: mh32
  #   - Root chord: 0.162 m (162 mm in WingConfig)
  #   - Symmetric: true

  Scenario: Verify eHawk data in backend DB
    Given the "eHawk E2E Test" aeroplane exists
    When I query the wing "main_wing" from the API
    Then the wing has 13 cross sections
    And cross section 0 has airfoil containing "mh32"
    And cross section 0 has chord approximately 0.162
    And the wing is symmetric

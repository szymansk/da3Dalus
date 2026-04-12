Feature: eHawk Designer Workflow — End-to-End
  As a drone engineer using the da3Dalus workbench
  I want to construct an eHawk main wing and run aerodynamic analysis
  So that the backend DB contains a correct, fully configured eHawk

  This test uses the real UI and real backend. No mocks, no fakes.
  The eHawk wing config matches the backend fixture exactly
  (test/ehawk_workflow_helpers._build_main_wing with mh32 airfoil).

  At the end of this test, the backend DB MUST contain a correct
  eHawk aeroplane with main_wing, 13 x_secs, ailerons on segments
  2-5, spars on segments 0-6, and a successful alpha sweep result.

  Background:
    Given the backend is running
    And the frontend is running

  Scenario: Create eHawk aeroplane via UI
    Given I am on the workbench
    When I click "Create New" and enter name "eHawk E2E Test"
    Then I see the construction workbench
    And the header shows project "eHawk E2E Test"

  Scenario: Create main_wing via from-wingconfig API
    Given the "eHawk E2E Test" aeroplane exists
    When I submit the eHawk wing config for "main_wing" via API
    And I reload the workbench
    Then the tree shows "main_wing" under the aeroplane
    And "main_wing" has 13 cross sections in the tree

  Scenario: Select segment and verify property form
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 0" in the tree
    Then the property form shows "segment 0"
    And the airfoil field shows "mh32"
    And the chord field shows a value greater than 0

  Scenario: Navigate to analysis and run alpha sweep
    Given the "eHawk E2E Test" has wing "main_wing"
    When I click the "Analysis" step pill
    Then I see the analysis page
    When I set velocity to "20.0"
    And I set alpha start to "-4.0"
    And I set alpha end to "8.0"
    And I set alpha step to "2.0"
    And I click "Run Analysis"
    Then the analysis completes without error
    And the polar chart shows bars
    And the chart annotation shows a CL_max value

  Scenario: Verify eHawk in backend DB
    Given the "eHawk E2E Test" aeroplane exists
    When I query the wing "main_wing" from the API
    Then the wing has 13 cross sections
    And cross section 0 has airfoil "mh32"
    And cross section 0 has chord approximately 0.162
    And the wing is symmetric

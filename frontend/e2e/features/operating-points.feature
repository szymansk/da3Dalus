Feature: Operating Point Management

  Background:
    Given an aeroplane "IntegrationTest" with a main wing and elevator
    And design assumptions are seeded with mass 1.5 kg and CL_max 1.4

  Scenario: Generate and view operating points
    When I navigate to the analysis workbench
    And I click "Generate Default OPs"
    Then the operating point table shows at least 8 rows
    And each row has a status badge
    And the "cruise" OP has status "NOT_TRIMMED"

  Scenario: Trim an operating point with AeroBuildup
    Given operating points are generated
    When I click on the "cruise" operating point row
    Then the detail drawer opens
    When I select trim variable "elevator" and target "Cm" = 0
    And I click "Run AeroBuildup Trim"
    Then the trim result shows "Converged"
    And the status badge changes to "TRIMMED"

  Scenario: Override control surface deflection
    Given the "cruise" OP is trimmed
    When I open the "cruise" OP detail drawer
    And I expand the "Control Deflections" section
    And I set "elevator" deflection to 5.0 degrees
    And I click "Save Deflections"
    Then the status badge changes to "DIRTY"

  Scenario: Mass sweep visualization
    When I navigate to the assumptions tab
    And I enter velocity 15 m/s and altitude 0 m
    And I click "Compute Mass Sweep"
    Then the mass sweep chart is displayed
    And the current mass marker is at 1.5 kg
    And the infeasible region is highlighted in red

  Scenario: CG comparison warning
    Given weight items exist with total CG at 0.30m
    And design CG assumption is 0.25m
    When I navigate to the assumptions tab
    Then a CG warning banner is displayed in orange
    And the banner shows delta of 5 cm
    When I click "Update design CG"
    Then the warning banner disappears

Feature: Trim Interpretation UI

  Background:
    Given an aeroplane "IntegrationTest" with a main wing and elevator
    And design assumptions are seeded with mass 1.5 kg and CL_max 1.4
    And operating points are generated and trimmed

  Scenario: View analysis goal card with status badge
    When I click on the "cruise" operating point row
    Then the detail drawer opens
    And the analysis goal card shows "Analysis Goal"
    And the analysis goal card has a status badge

  Scenario: View control authority chart
    When I click on the "cruise" operating point row
    Then the detail drawer opens
    And the control authority chart is visible
    And the chart shows at least one surface bar

  Scenario: Expand design warning for details
    Given the "stall_approach" OP has a critical warning
    When I click on the "stall_approach" operating point row
    Then the detail drawer opens
    And warning badges are displayed
    When I click on the first warning badge
    Then warning details are expanded showing category and severity

  Scenario: View mixer values for dual-role surfaces
    Given the aircraft has elevon surfaces
    When I click on a trimmed operating point row
    Then the mixer setup card shows symmetric offset and differential throw

  Scenario: Compare trim results across operating points
    Then the OP comparison table is visible
    And the table shows columns for OP name, alpha, elevator, reserve, CL, CD, L/D
    And the worst-case row is highlighted in red
    When I click the "α (°)" column header
    Then the table rows are sorted by alpha

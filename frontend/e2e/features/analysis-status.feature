Feature: Analysis Status Indicator

  Scenario: Status updates after geometry change
    Given an aeroplane with trimmed operating points
    When I change the wing span
    Then the status indicator shows a dirty count badge
    And the operating point table shows DIRTY status badges
    When the auto-retrim completes
    Then the status indicator shows "All trimmed"
    And the OP table refreshes with TRIMMED badges

  Scenario: Flight envelope visualization
    Given an aeroplane with design assumptions
    And operating points are generated and trimmed
    When I navigate to the flight envelope tab
    And I click "Compute Flight Envelope"
    Then the V-n diagram is displayed
    And at least 6 KPIs are shown
    And operating point markers appear on the diagram

Feature: Expert View (gh-1282, gh-1330, ADR 0030)

  Background:
    Given the Expert View is open with a stubbed kernel backend

  Scenario: Selecting a node does not compute it
    When I click the "stall-speed" node in the navigator
    Then the navigator panel shows the value "not computed"
    And no computation was requested

  Scenario: Computing a node shows its value and its run time
    When I click the "stall-speed" node in the navigator
    And I choose "Compute" in the navigator panel
    Then the "stall-speed" node is marked as computed
    And the navigator panel shows the value "7.5 m/s"
    And the navigator panel shows the run time "12.3 ms"
    And the kernel log lists a record of the request

  Scenario: A failure leads to its cause
    Given the kernel fails "stall-speed" because "air-density" failed
    When I click the "stall-speed" node in the navigator
    And I choose "Compute" in the navigator panel
    Then the "stall-speed" node is marked as failed
    When I choose "Go to cause" in the navigator panel
    Then the navigator panel is about "air-density"

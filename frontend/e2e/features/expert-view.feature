Feature: Expert View (gh-1282, ADR 0030)

  Background:
    Given the Expert View is open with a stubbed kernel backend

  Scenario: Computing a node shows its value
    When I click the "stall-speed" node in the navigator
    Then the "stall-speed" node is marked as computed
    And the navigator panel shows the value "7.5 m/s"
    And the kernel log lists a record of the request

  Scenario: A failure leads to its cause
    Given the kernel fails "stall-speed" because "air-density" failed
    When I click the "stall-speed" node in the navigator
    Then the "stall-speed" node is marked as failed
    When I choose "Go to cause" in the navigator panel
    Then the navigator panel is about "air-density"

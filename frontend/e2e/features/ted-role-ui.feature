Feature: TED Role Dropdown and Pitch Warning (gh-450)
  As an aircraft designer using the da3Dalus workbench
  I want to assign roles to control surfaces via a dropdown
  So that the system can identify elevator, aileron, and other surfaces

  Background:
    Given the backend is running
    And the frontend is running

  Scenario: Pitch warning appears when no pitch surface exists
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    And no cross section has role "elevator" or "elevon" or "stabilator"
    Then the pitch warning is visible
    And the pitch warning text contains "No pitch control surface assigned"

  Scenario: Add TED with elevator role and verify chip in tree
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 0" in the tree
    And I click the add button on the segment
    And I select "Add Control Surface"
    And I select role "elevator" in the TED dialog
    And I fill label "Main Elevator" in the TED dialog
    And I click "Add"
    Then segment 0 shows an "↕ ELEVATOR" chip in the tree

  Scenario: Pitch warning disappears after elevator is assigned
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    And at least one cross section has a pitch role
    Then the pitch warning is not visible

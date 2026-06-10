Feature: Turbulator UI — add, edit, and preview (gh-936)
  As an aircraft designer using the da3Dalus workbench
  I want to add a turbulator strip to a wing segment
  So that I can configure and visualise the trip position

  Background:
    Given the backend is running
    And the frontend is running

  Scenario: Add a turbulator to a segment and see the chip in the tree
    Given the "eHawk E2E Test" has wing "main_wing" in the tree
    When I click on "segment 0" in the tree
    And I click the add button on the segment
    And I select "Add Turbulator"
    And I fill position root "0.1" in the turbulator dialog
    And I click "Add"
    Then segment 0 shows a "ZIGZAG" turbulator chip in the tree

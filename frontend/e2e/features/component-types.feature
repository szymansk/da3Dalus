Feature: Dynamic Component Types
  # BDD coverage for the #82 epic: user-managed types with validated specs.
  # Each scenario exercises one end-to-end slice through backend + UI.

  Background:
    Given I am on the workbench with an aeroplane
    When I click the "Components" step pill
    Then I see "Component Library" on the page

  Scenario: Seeded Material type exposes the density field
    When I open the "New Component" dialog
    And I select type "Material (3D-Druck)"
    Then I see "Dichte" on the page
    And I see "kg/m³" on the page
    And the Dichte input is marked required

  Scenario: Submitting without the required density is blocked
    When I open the "New Component" dialog
    And I enter "PLA+" in the Name field
    And I select type "Material (3D-Druck)"
    And I click the "Create" button
    Then the component is NOT saved
    And the dialog shows a validation error mentioning "Dichte"

  Scenario: A valid material component saves and shows the correct weight via tree
    When I open the "New Component" dialog
    And I enter "PLA+" in the Name field
    And I select type "Material (3D-Druck)"
    And I enter "1240" in the Dichte field
    And I click the "Create" button
    Then the dialog closes
    And "PLA+" is listed in the Library grid

  Scenario: User creates a custom type and uses it for a component
    When I click the "Manage Types" button
    And I click "+ New Type" in the Types dialog
    And I enter "carbon_tube" in the Name field
    And I enter "Carbon Tube" in the Label field
    And I add a number property "outer_diameter_mm" required with unit "mm"
    And I click "Save" in the Type dialog
    Then "Carbon Tube" appears in the types list
    And its reference-count is "0 components"
    When I close the Types dialog
    And I open the "New Component" dialog
    And I select type "Carbon Tube"
    Then I see an "outer_diameter_mm" input with unit "mm"

  Scenario: Seeded types cannot be deleted
    When I click the "Manage Types" button
    Then the delete button for "Material (3D-Druck)" is disabled
    And its tooltip mentions "Seeded type cannot be deleted"

  Scenario: User type with no references can be deleted
    Given a custom type "throwaway" exists with no references
    When I click the "Manage Types" button
    And I click the delete button for "throwaway"
    And I confirm the deletion
    Then "throwaway" is no longer listed

  Scenario: User type with references cannot be deleted
    Given a custom type "referenced_type" exists with 2 components referencing it
    When I click the "Manage Types" button
    Then the delete button for "referenced_type" is disabled
    And its tooltip mentions "Referenced by 2 components"

  Scenario: Unknown properties on an existing component are surfaced read-only
    Given a component "legacy" exists of type "Material (3D-Druck)" with unknown keys in its specs
    When I open the edit dialog for "legacy"
    Then I see a collapsible "Unknown properties (N)" section
    When I expand the Unknown properties section
    Then I see the unknown keys listed as read-only rows

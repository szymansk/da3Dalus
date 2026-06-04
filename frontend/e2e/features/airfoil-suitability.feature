Feature: Airfoil suitability surfacing on airfoil-preview page (gh-825)

  Scenario: Suitability card shows five lenses for the selected root airfoil
    Given I am on the airfoil-preview page with a stubbed suitability response
    Then the root suitability card shows the Re-agnostisch lens
    And the root suitability card shows the Mission lens
    And the root suitability card shows the Ziel-CL Cruise lens
    And the root suitability card shows the Ziel-CL Best-Glide lens
    And the root suitability card shows the Ziel-CL Min-Sink lens

  Scenario: Low-confidence airfoil shows amber chip and caveat
    Given I am on the airfoil-preview page with a low-confidence suitability response
    Then the root suitability card shows an amber confidence chip
    And the root suitability card shows a caveat callout

  Scenario: Tapered segment shows tip-Re warning banner
    Given I am on the airfoil-preview page with tip Re lower than root Re
    Then a tip-Re warning banner is visible with role "alert"

  Scenario: Passende finden re-orders the dropdown
    Given I am on the airfoil-preview page with a stubbed suitability response
    When I click the Passende finden toggle for the root selector
    Then the root airfoil dropdown shows airfoils sorted by suitability score

  Scenario: Suitability card shows provenance indicator when target_cl_provenance is present
    Given I am on the airfoil-preview page with a stubbed suitability response
    Then the root suitability card shows a provenance indicator

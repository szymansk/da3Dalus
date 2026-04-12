Feature: Workbench Navigation

  Scenario: Root URL redirects to workbench
    When I open the app at "/"
    Then the URL contains "/workbench"

  Scenario: Step pills navigate between pages
    Given I am on the workbench with an aeroplane
    When I click the "Mission" step pill
    Then I see "Mission Objectives" on the page
    When I click the "Analysis" step pill
    Then I see "Aerodynamic Analysis" on the page
    When I click the "Components" step pill
    Then I see "Component Library" on the page
    When I click the "Weight" step pill
    Then I see "Weight Items" on the page

  Scenario: Active pill reflects current page
    Given I am on the workbench with an aeroplane
    When I click the "Analysis" step pill
    Then the "Analysis" pill has the active style

  Scenario: Mission page shows alert banner
    Given I am on the workbench with an aeroplane
    When I click the "Mission" step pill
    Then I see "Coming soon" on the page

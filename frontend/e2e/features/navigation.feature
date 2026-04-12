Feature: Workbench Navigation

  Scenario: Root URL redirects to workbench
    When I navigate to "/"
    Then I am redirected to "/workbench"

  Scenario: Step pills navigate between pages
    Given I am on the workbench
    When I click the "Mission" step pill
    Then I see the "Mission Objectives" page
    When I click the "Analysis" step pill
    Then I see the "Aerodynamic Analysis" page
    When I click the "Components" step pill
    Then I see the "Component Library" page
    When I click the "Weight" step pill
    Then I see the "Weight Items" page

  Scenario: Active pill reflects current page
    Given I am on "/workbench/analysis"
    Then the "Analysis" pill is highlighted in orange
    And the other pills are not highlighted

  Scenario: Mission page shows alert banner
    Given I am on the mission page
    Then I see an alert banner with "Coming soon"

Feature: Polar fit design-warning badge (gh-630)

  Scenario: Design-category polar rejection surfaces a warning in the analysis dashboard
    Given an aeroplane whose clean parabolic-polar fit fails with a negative-slope design rejection
    When I open the analysis dashboard
    Then a visible design-warning badge displays the rejection hint
    And the badge has the accessible role "alert"

  Scenario: Sweep-category polar rejection stays invisible
    Given an aeroplane whose clean parabolic-polar fit fails with an insufficient-points sweep rejection
    When I open the analysis dashboard
    Then no polar-design-warning badge is visible

  Scenario: Successful polar fits show no warning
    Given an aeroplane whose three parabolic-polar fits all succeed
    When I open the analysis dashboard
    Then no polar-design-warning badge is visible

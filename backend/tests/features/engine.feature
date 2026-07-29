Feature: Deterministic Rules Engine
  The rules engine must produce identical results for identical inputs,
  with no randomness or AI calls. Physics checks and god interventions
  must be fully deterministic.

  Scenario: Brute force fails on protected future anchor
    Given the player has strength 60
    And the player targets "ancient_locked_door" with brute_force
    When the rules engine judges the action
    Then the result is forced_fail
    And god "Chronos the Order" intervened
    And the damage is 40

  Scenario: Brute force succeeds on non-protected target
    Given the player has strength 60
    And the player targets "priest_corpse_01" with brute_force
    When the rules engine judges the action
    Then the result is success
    And no god intervened

  Scenario: God intervention on holographic altar
    Given the player has strength 60
    And the player targets "holographic_altar" with investigate
    When the rules engine judges the action
    Then the result is forced_fail
    And god "Mnemosyne the Weaver" intervened
    And the damage is 25

  Scenario: Determinism - 100 identical inputs produce identical output
    Given the player has strength 60
    And the player targets "neon_circuit_pillar" with brute_force
    When the rules engine judges the action 100 times
    Then all 100 results are identical

  Scenario: No target defaults to success
    Given the player has strength 60
    And the player has no specific target with stealth
    When the rules engine judges the action
    Then the result is success
    And the reason contains "无特定目标"

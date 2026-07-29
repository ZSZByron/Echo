// Action types mirroring backend models

export type ActionType =
  | "brute_force"
  | "stealth"
  | "read_memory"
  | "negotiate"
  | "probe"
  | "god_provoke"
  | "investigate";

export type JudgmentOutcome = "success" | "fail" | "forced_fail";

export interface ParsedIntent {
  action_type: ActionType;
  target?: string;
  intensity: "low" | "medium" | "maximum";
  risk_acceptance: boolean;
  tool_used?: string;
  raw_input: string;
  confidence: number;
}

export interface StateChange {
  target_type: "player" | "object" | "scene";
  target_id: string;
  property_name: string;
  old_value: any;
  new_value: any;
}

export interface NarrativeContext {
  scene_id: string;
  previous_action?: string;
  active_gods: string[];
  atmosphere: string;
  tension_level: number;
}

export interface JudgmentResult {
  result: JudgmentOutcome;
  reason: string;
  damage: number;
  state_changes: StateChange[];
  god_intervention?: string;
  narrative_context: NarrativeContext;
  echo_triggered: boolean;
}

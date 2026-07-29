// API request/response types

import type { JudgmentResult } from "./action";
import type { PlayerState } from "./player";
import type { ParsedIntent } from "./action";

export interface ActionRequest {
  player_input: string;
}

export interface ActionResponse {
  judgment: JudgmentResult;
  narrative: string;
  updated_state: PlayerState;
  parsed_intent: ParsedIntent;
  echo_vision?: string | null;
  available_actions: string[];
}

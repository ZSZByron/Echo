// Player state types mirroring backend models

export interface PlayerState {
  id: string;
  energy: number;
  health: number;
  strength: number;
  intelligence: number;
  echo_mode_enabled: boolean;
  mental_stability: number;
  location: string;
  inventory: string[];
  status: string;  // 后端 PlayerStatus 枚举序列化为字符串，如 "normal" | "injured" | "dying" 等
  max_energy: number;
  max_health: number;
}

// Scene data transfer objects — shape mirrors backend GET /api/scene response.

export interface Position {
  x: number;
  y: number;
}

export interface SceneObjectDTO {
  id: string;
  name: string;
  type: string;
  description: string;
  position: Position;
  asset: string | null;
  is_primary: boolean;
  is_dangerous: boolean;
}

export interface SceneResponse {
  scene_id: string;
  name: string;
  description: string;
  atmosphere: string;
  background_asset: string | null;
  objects: SceneObjectDTO[];
}

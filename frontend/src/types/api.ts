export type ExpiryStatus = "expired" | "urgent" | "soon" | "normal" | "unknown";

export interface Ingredient {
  id: number;
  name: string;
  meal_count: number;
  created_at: string;
  expire_at: string | null;
  expiry_status: ExpiryStatus;
}

export interface Consumption {
  ingredient_name: string;
  quantity: number;
  unit: string;
}

export interface Recipe {
  id: number;
  dish_name: string;
  description: string;
  used_ingredients: string[];
  missing_ingredients: string[];
  consumptions: Consumption[];
  cooking_time: number;
  difficulty: string;
  steps: string[];
  reason: string;
  status: "recommended" | "cooked";
  ai_provider: string;
  created_at: string;
}

export interface CookingHistory {
  id: number;
  recommendation_id: number;
  dish_name: string;
  ingredients: Consumption[];
  cooked_at: string;
}

export interface RecommendationPreferences {
  style: "不限" | "家常菜" | "川菜" | "粤菜" | "汤羹" | "减脂";
  max_time: number | null;
  spicy: "不限" | "不辣" | "辣";
  equipment: "不限" | "炒锅" | "蒸锅" | "空气炸锅";
  pantry_items: string[];
  excluded_dishes: string[];
}

export interface RecommendationBatch {
  recipes: Recipe[];
  inventory_changed: boolean;
  preferences: RecommendationPreferences;
  created_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
  error: { code: string; details: unknown } | null;
}

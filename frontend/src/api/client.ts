import type { ApiResponse } from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  let payload: ApiResponse<T>;
  try {
    payload = (await response.json()) as ApiResponse<T>;
  } catch {
    throw new Error(response.ok ? "服务返回异常，请稍后重试" : `服务暂时不可用（${response.status}）`);
  }
  if (!response.ok || !payload.success) {
    throw new Error(payload.message || "请求失败，请稍后重试");
  }
  return payload.data;
}

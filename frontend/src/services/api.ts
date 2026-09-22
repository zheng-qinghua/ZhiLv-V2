import axios, { AxiosError } from "axios";

import type {
  ApiResponse,
  AuthResponse,
  ChatSession,
  ChatTurnResponse,
  Page,
  TripPlan,
  TripRecord,
  TripRequestPayload,
  WeatherForecastResponse,
} from "../types";

// 空 baseURL => 走 vite 代理(/api -> localhost:8080);也可用 VITE_API_BASE_URL 指到后端直连
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "") as string;

export const TOKEN_KEY = "zhilv_token";
export const USER_KEY = "zhilv_user";

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000, // 常规接口 2 分钟;生成行程单独在 createTrip 放宽到 5 分钟
});

// 请求拦截:自动带 Bearer token(与后端 static 登录页共用 localStorage)
http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应错误:token 失效/未登录 => 清掉本地状态回登录页
http.interceptors.response.use(
  (res) => res,
  (error: AxiosError<ApiResponse<unknown>>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

/** 统一取后端返回的 message,取不到退回兜底文案 */
export function errMessage(e: unknown, fallback = "请求失败"): string {
  if (axios.isAxiosError(e)) {
    const data = e.response?.data as ApiResponse<unknown> | undefined;
    if (data?.message) return data.message;
  }
  return fallback;
}

/** 是否是前端超时(axios 在 timeout 后抛 ECONNABORTED) */
export function isTimeoutError(e: unknown): boolean {
  return axios.isAxiosError(e) && (e.code === "ECONNABORTED" || e.code === "ETIMEDOUT");
}

export async function register(username: string, password: string): Promise<void> {
  const { data } = await http.post<ApiResponse<void>>("/api/auth/register", {
    username,
    password,
  });
  if (data.code !== 200) throw new Error(data.message);
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await http.post<ApiResponse<AuthResponse>>("/api/auth/login", {
    username,
    password,
  });
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

export async function logout(): Promise<void> {
  try {
    await http.post<ApiResponse<void>>("/api/auth/logout");
  } finally {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

/**
 * 提交表单 => 后端调 AI 生成完整行程并落库,返回 TripRecord(planJson 里是完整 TripPlan)。
 * 大行程(天数多/跨多城市)DeepSeek 生成可能长达几分钟,再加高德点位补全,
 * 单独放宽超时到 8 分钟,避免"慢但最终会成功"的请求被前端提前掐断而误报失败。
 */
export async function createTrip(payload: TripRequestPayload): Promise<TripRecord> {
  const { data } = await http.post<ApiResponse<TripRecord>>("/api/trips", payload, {
    timeout: 480_000,
  });
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

export async function listTrips(page: number, size: number): Promise<Page<TripRecord>> {
  const { data } = await http.get<ApiResponse<Page<TripRecord>>>("/api/trips", {
    params: { page, size },
  });
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

export async function deleteTrip(id: number): Promise<void> {
  const { data } = await http.delete<ApiResponse<void>>(`/api/trips/${id}`);
  if (data.code !== 200) throw new Error(data.message);
}

/** 导出完整 TripPlan(plan_json 反序列化 + 回填真实 id),用于结果页展示 */
export async function exportTrip(id: number): Promise<TripPlan> {
  const { data } = await http.get<ApiResponse<TripPlan>>(`/api/trips/${id}/export`);
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

/** 新建对话式规划会话,返回含 id */
export async function createChatSession(): Promise<ChatSession> {
  const { data } = await http.post<ApiResponse<ChatSession>>("/api/chat/sessions");
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

/**
 * 会话下发一轮发言/确认。action=confirm 走生成(那轮可能几分钟),放宽超时到 8 分钟。
 */
export async function sendChatMessage(
  sessionId: number,
  message: string,
  action: "chat" | "confirm" = "chat"
): Promise<ChatTurnResponse> {
  const { data } = await http.post<ApiResponse<ChatTurnResponse>>(
    `/api/chat/sessions/${sessionId}/messages`,
    { message, action },
    { timeout: 480_000 }
  );
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

/** 按城市查未来天气(后端先地理编码拿 adcode 再走高德天气) */
export async function fetchWeatherForecast(city: string): Promise<WeatherForecastResponse> {
  const { data } = await http.get<ApiResponse<WeatherForecastResponse>>("/api/weather/forecast", {
    params: { city },
  });
  if (data.code !== 200) throw new Error(data.message);
  return data.data;
}

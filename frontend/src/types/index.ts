// 后端统一响应与实体类型(与 backend 接口对齐)。
// TripPlan 结构见 ./trip.ts(跨服务契约,勿改字段名)。

export * from "./trip";

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

/** POST /api/auth/login 成功返回体 */
export interface AuthResponse {
  token: string;
  username: string;
}

/** 登录/注册入参 */
export interface AuthPayload {
  username: string;
  password: string;
}

/** POST /api/trips 入参(snake_case,与后端 TripRequest 逐字同名) */
export interface TripRequestPayload {
  title?: string | null;
  destination: string;
  departure?: string | null; // 出发城市(每单必填)
  start_date: string; // yyyy-MM-dd
  end_date: string; // yyyy-MM-dd
  travelers: number;
  budget: number;
  preferences: string[];
  pace?: string | null;
  hotel_level?: string | null; // 舒适型 / 高档型 / 经济型
  dietary_preferences?: string[]; // 如 ["少辣"]
  special_notes?: string | null;
}

/** 行程列表里的实体(Trip 实体 JSON,camelCase) */
export interface TripRecord {
  id: number;
  userId: number;
  title: string;
  destination: string;
  startDate: string;
  endDate: string;
  dayCount: number;
  travelers: number;
  budget: number;
  preferences: string; // JSON 数组字符串
  pace: string;
  specialNotes: string;
  summary: string;
  tips: string; // JSON 数组字符串
  planJson: string; // 完整 TripPlan 的 JSON 字符串
  source: "FORM" | "CHAT";
  createdAt: string;
  updatedAt: string;
}

/** Spring Data Page 的分页结构 */
export interface Page<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  number: number;
  size: number;
  numberOfElements: number;
  first: boolean;
  last: boolean;
  empty: boolean;
}

/** GET /api/weather/forecast 单日天气(高德口径,dayWeather/nightWeather 等为字符串) */
export interface WeatherForecastDay {
  date: string | null;
  week: string | null;
  dayWeather: string | null;
  nightWeather: string | null;
  dayTemp: string | null;
  nightTemp: string | null;
  dayWind: string | null;
  nightWind: string | null;
}

/** GET /api/weather/forecast 响应 */
export interface WeatherForecastResponse {
  city: string;
  province: string | null;
  adcode: string | null;
  reportTime: string | null;
  days: WeatherForecastDay[];
}

/** POST /api/chat/sessions 建会话返回(实体 JSON) */
export interface ChatSession {
  id: number;
  userId: number;
  title: string;
  createdAt: string;
}

/** 一轮对话返回(ai-service /chat 透传)
 *  status: collecting(继续聊) | await_confirm | budget_low(预算不足被拦截) | generated(已生成,待保存) | failed
 *  trip: 确认生成那轮后端已落库的 CHAT 行程实体;前端据此跳结果页
 *  lowBudget/minBudget: 预算低于路线最低花费时置位(minBudget 为预估最低总额,含往返大交通) */
export interface ChatTurnResponse {
  reply: string;
  status: string;
  ready: boolean;
  params: Record<string, unknown> | null; // 当前已确定的行程参数字典
  lowBudget?: boolean | null;
  minBudget?: number | null;
  trip?: TripRecord | null;
}

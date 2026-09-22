// TripPlan —— 统一行程模型(跨服务契约,改此处结构,必须同步另两处):
// 1) backend/src/main/java/com/zhilv/dto/TripPlan.java
// 2) docs/ARCHITECTURE.md 3.2
// 字段一律 snake_case,与契约 JSON 逐字同名。source 只允许 'FORM' 或 'CHAT'。

export interface TripPlan {
  id: number | null; // 生成后落库才有 id,此前为 null
  title: string;
  destination: string;
  departure?: string | null; // 出发城市(每单必填;旧数据可能没有,展示需降级)
  start_date: string;
  end_date: string;
  day_count: number;
  travelers: number;
  budget: number;
  budget_breakdown: BudgetBreakdown | null; // 预算明细:门票/酒店/餐饮/交通(元)
  estimated_budget: number | null; // 预估总花费(元,≈预算)
  preferences: string[];
  pace: string;
  special_notes: string;
  summary: string;
  tips: string[];
  days: TripDay[];
  source: 'FORM' | 'CHAT';
  created_at: string;
}

export interface BudgetBreakdown {
  tickets: number;
  hotel: number;
  meals: number;
  transport: number;
}

export interface TripDay {
  day_index: number;
  date: string;
  theme: string;
  city?: string | null; // 当天主要活动所在城市(模块7 地图按天定位用,AI 生成时标注)
  spots: TripSpot[];
  meals: TripMeal[];
  hotel?: TripHotel | null; // 当晚住宿(旧数据可能没有)
  transport: TripTransport;
  note: string;
}

export interface TripSpot {
  name: string;
  description: string;
  location: TripLocation | null;
  duration: string;
  image_url: string;
  estimated_cost?: number | null; // 门票估算(元,免费景点为 0)
  address?: string | null; // 高德 POI 地址(模块6 生成时补全)
  poi_id?: string | null; // 高德 POI id
}

export interface TripLocation {
  lat: number;
  lng: number;
}

export interface TripMeal {
  name: string;
  notes: string;
  estimated_cost?: number | null; // 一餐/人均估算(元)
  location?: TripLocation | null; // 高德坐标(模块6 补全)
  address?: string | null;
  image_url?: string | null;
  poi_id?: string | null;
}

export interface TripHotel {
  name: string;
  level?: string | null; // 舒适型 / 高档型 / 经济型
  estimated_cost?: number | null; // 当晚房价估算(元)
  location?: TripLocation | null; // 高德坐标(模块6 补全)
  address?: string | null;
  image_url?: string | null;
  poi_id?: string | null;
}

export interface TripTransport {
  mode: string;
  note: string;
  estimated_cost?: number | null; // 当天交通估算(元)
}

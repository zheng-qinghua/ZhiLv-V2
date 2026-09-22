package com.zhilv.dto;

import java.math.BigDecimal;
import java.util.List;

/**
 * 统一行程模型 TripPlan —— 跨服务契约(改此处结构,必须同步另两处):
 * 1) docs/ARCHITECTURE.md 3.2 的 JSON 结构
 * 2) frontend/src/types/trip.ts
 * 字段一律 snake_case,与契约 JSON 逐字同名;source 只允许 "FORM" 或 "CHAT"。
 * 生成前 id 为空(还没落库),落库后由后端回填。
 */
public record TripPlan(
        Long id,
        String title,
        String destination,
        String departure,               // 出发城市(每单必填;旧数据可为 null)
        String start_date,
        String end_date,
        int day_count,
        int travelers,
        BigDecimal budget,
        BudgetBreakdown budget_breakdown,
        BigDecimal estimated_budget,
        List<String> preferences,
        String pace,
        String special_notes,
        String summary,
        List<String> tips,
        List<Day> days,
        String source,
        String created_at
) {
    /** 预算明细:四类金额(元),与源项目 Result 页「预算明细」一一对应 */
    public record BudgetBreakdown(
            BigDecimal tickets,
            BigDecimal hotel,
            BigDecimal meals,
            BigDecimal transport
    ) {}

    public record Day(
            int day_index,
            String date,
            String theme,
            String city,               // 当天主要活动所在城市(模块7 地图按天定位用,AI 生成时标注;旧数据可为 null)
            List<Spot> spots,
            List<Meal> meals,
            Transport transport,
            String note,
            Hotel hotel
    ) {}

    public record Spot(
            String name,
            String description,
            Location location,
            String duration,
            String image_url,
            BigDecimal estimated_cost,   // 门票估算(元,免费景点为 0)
            String address,              // 高德 POI 地址(模块6 补全,可为 null)
            String poi_id                // 高德 POI id(可为 null)
    ) {}

    public record Location(double lat, double lng) {}

    public record Meal(
            String name,
            String notes,
            BigDecimal estimated_cost,    // 一餐/人均估算(元)
            Location location,           // 高德坐标(可为 null)
            String address,              // 高德地址(可为 null)
            String image_url,            // 高德图片(可为 null)
            String poi_id                // 高德 POI id(可为 null)
    ) {}

    public record Transport(
            String mode,
            String note,
            BigDecimal estimated_cost    // 当天交通估算(元)
    ) {}

    /** 当晚住宿:酒店名 + 档次 + 房价估算(元);location/address 等为模块6 高德补全字段 */
    public record Hotel(
            String name,
            String level,
            BigDecimal estimated_cost,
            Location location,           // 高德坐标(可为 null)
            String address,              // 高德地址(可为 null)
            String image_url,            // 高德图片(可为 null)
            String poi_id                // 高德 POI id(可为 null)
    ) {}
}

package com.zhilv.dto;

import java.math.BigDecimal;
import java.util.List;

/**
 * 表单式旅行规划请求(POST /api/trips 入参)。
 * 只有用户填的表单条件(目的地/日期/预算/偏好),不含每日安排 days——
 * 每日安排要等生成链路(D13+)跑完,放进 TripPlan 的 plan_json。
 * 字段名 snake_case,与前端表单字段一致。
 */
public record TripRequest(
        String title,
        String destination,
        String departure,               // 出发城市(每单必填)
        String start_date,
        String end_date,
        Integer travelers,
        BigDecimal budget,
        List<String> preferences,
        String pace,
        String hotel_level,              // 舒适型 / 高档型 / 经济型
        List<String> dietary_preferences, // 如 ["少辣"]
        String special_notes
) {}

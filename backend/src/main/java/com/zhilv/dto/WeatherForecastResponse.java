package com.zhilv.dto;

import java.util.List;

/**
 * 天气查询响应(与源项目 weather.py 的 WeatherForecastResponse 对齐)。
 * GET /api/weather/forecast?city=X 返回:城市/省份/adcode/预报发布时间 + 未来几天逐日天气。
 */
public record WeatherForecastResponse(
        String city,
        String province,
        String adcode,
        String reportTime,
        List<Day> days) {

    /** 单日天气:白天/夜间天气、温度、风向(字符串,高德原始口径)。 */
    public record Day(
            String date,
            String week,
            String dayWeather,
            String nightWeather,
            String dayTemp,
            String nightTemp,
            String dayWind,
            String nightWind) {
    }
}

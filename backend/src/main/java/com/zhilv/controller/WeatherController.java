package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import com.zhilv.common.BusinessException;
import com.zhilv.dto.WeatherForecastResponse;
import com.zhilv.service.AmapWeatherService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 天气接口(需登录):GET /api/weather/forecast?city=目的地
 * 由 AmapWeatherService 先地理编码再查天气,返回逐日预报。
 */
@RestController
@RequestMapping("/api/weather")
public class WeatherController {

    private final AmapWeatherService weatherService;

    public WeatherController(AmapWeatherService weatherService) {
        this.weatherService = weatherService;
    }

    @GetMapping("/forecast")
    public ApiResponse<WeatherForecastResponse> forecast(@RequestParam(required = false) String city) {
        if (city == null || city.isBlank()) {
            throw new BusinessException(400, "城市不能为空");
        }
        return ApiResponse.success(weatherService.forecast(city));
    }
}

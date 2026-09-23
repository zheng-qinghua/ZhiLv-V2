package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import com.zhilv.common.BusinessException;
import com.zhilv.dto.WeatherForecastResponse;
import com.zhilv.service.AmapWeatherService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 内部天气接口(给 ai-service 的 weather Agent 用,不面向前端):GET /internal/weather?city=大理
 *
 * 为什么不复用 /api/weather/forecast:那条走用户 JWT,而 Python 服务没有用户 token。
 * 这里改校验 X-AI-Service-Key(两边共享的密钥),密钥不对一律 401。
 *
 * 路径不在 /api/** 下,所以 SecurityConfig 的 anyRequest().permitAll() 会放行,
 * 真正的校验就在这个 Controller 里做 —— 放行不等于不鉴权,只是换了鉴权方式。
 */
@RestController
@RequestMapping("/internal/weather")
public class InternalWeatherController {

    private final AmapWeatherService weatherService;
    private final String serviceKey;

    public InternalWeatherController(AmapWeatherService weatherService,
                                     @Value("${app.ai.service-key:}") String serviceKey) {
        this.weatherService = weatherService;
        this.serviceKey = serviceKey == null ? "" : serviceKey.trim();
    }

    @GetMapping
    public ApiResponse<WeatherForecastResponse> forecast(
            @RequestParam(required = false) String city,
            @RequestHeader(value = "X-AI-Service-Key", required = false) String key) {
        if (serviceKey.isBlank()) {
            throw new BusinessException(500, "内部接口未配置共享密钥:后端缺 AI_SERVICE_KEY。");
        }
        if (key == null || !serviceKey.equals(key.trim())) {
            throw new BusinessException(401, "内部接口校验失败");
        }
        if (city == null || city.isBlank()) {
            throw new BusinessException(400, "城市不能为空");
        }
        return ApiResponse.success(weatherService.forecast(city));
    }
}

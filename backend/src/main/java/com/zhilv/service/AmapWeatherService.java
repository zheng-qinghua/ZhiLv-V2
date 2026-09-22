package com.zhilv.service;

import com.zhilv.common.BusinessException;
import com.zhilv.dto.WeatherForecastResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * 高德天气(D20,照源项目 weather.py 思路迁到 Java):
 * 1) 先按目的地城市名调地理编码 /geocode/geo 拿行政区编码 adcode;
 * 2) 再带 adcode 调天气 /weather/weatherInfo?extensions=all 拿逐日预报。
 * key 从 app.amap.key 读取(默认读 AMAP_API_KEY 环境变量),不写死进代码。
 */
@Service
public class AmapWeatherService {

    private final String key;
    private final String baseUrl;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public AmapWeatherService(@Value("${app.amap.key:}") String key,
                              @Value("${app.amap.base-url:https://restapi.amap.com/v3}") String baseUrl,
                              ObjectMapper objectMapper) {
        this.key = key == null ? "" : key.trim();
        this.baseUrl = baseUrl == null ? "" : baseUrl.trim();
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public WeatherForecastResponse forecast(String city) {
        if (key.isBlank()) {
            throw new BusinessException(502, "天气服务未配置:后端缺少高德 key(AMAP_API_KEY)。");
        }
        String cityName = city.trim();
        String adcode = resolveAdcode(cityName);
        return fetchWeather(cityName, adcode);
    }

    /** 地理编码:城市名 → adcode。搜索类接口可能因 key 未开通/未实名而返回失败,给可读中文报错。 */
    private String resolveAdcode(String city) {
        JsonNode root = callAmap("/geocode/geo", "address", city);
        JsonNode geocodes = root.path("geocodes");
        if (!geocodes.isArray() || geocodes.isEmpty()) {
            throw new BusinessException(502,
                    "高德找不到「" + city + "」的行政区划编码。请检查 key 的实名认证与地理编码配额是否开通。");
        }
        String adcode = geocodes.get(0).path("adcode").asText("").trim();
        if (adcode.isBlank()) {
            throw new BusinessException(502, "高德未能解析「" + city + "」的行政区划编码。");
        }
        return adcode;
    }

    private WeatherForecastResponse fetchWeather(String city, String adcode) {
        JsonNode root = callAmap("/weather/weatherInfo", "city", adcode, "extensions", "all");
        JsonNode forecasts = root.path("forecasts");
        if (!forecasts.isArray() || forecasts.isEmpty()) {
            throw new BusinessException(502, "高德未返回「" + city + "」的天气预报。");
        }
        JsonNode first = forecasts.get(0);
        List<WeatherForecastResponse.Day> days = new ArrayList<>();
        JsonNode casts = first.path("casts");
        if (casts.isArray()) {
            for (JsonNode c : casts) {
                days.add(new WeatherForecastResponse.Day(
                        textOrNull(c, "date"),
                        textOrNull(c, "week"),
                        textOrNull(c, "dayweather"),
                        textOrNull(c, "nightweather"),
                        textOrNull(c, "daytemp"),
                        textOrNull(c, "nighttemp"),
                        textOrNull(c, "daywind"),
                        textOrNull(c, "nightwind")));
            }
        }
        String returnedCity = first.path("city").asText("").trim();
        return new WeatherForecastResponse(
                returnedCity.isBlank() ? city : returnedCity,
                textOrNull(first, "province"),
                textOrNull(first, "adcode"),
                textOrNull(first, "reporttime"),
                days);
    }

    /** 调高德接口并校验 status,失败统一转可读 BusinessException(502)。 */
    private JsonNode callAmap(String path, String... kv) {
        StringBuilder q = new StringBuilder(baseUrl).append(path).append("?key=").append(enc(key));
        for (int i = 0; i + 1 < kv.length; i += 2) {
            q.append("&").append(kv[i]).append("=").append(enc(kv[i + 1]));
        }
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(q.toString()))
                    .timeout(Duration.ofSeconds(15))
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            JsonNode root = objectMapper.readTree(response.body());
            if (!"1".equals(root.path("status").asText())) {
                String info = root.path("info").asText("未知错误");
                throw new BusinessException(502, "高德接口调用失败:" + info);
            }
            return root;
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            throw new BusinessException(502, "调用高德服务失败:" + e.getMessage());
        }
    }

    private String enc(String v) {
        return URLEncoder.encode(v, StandardCharsets.UTF_8);
    }

    private String textOrNull(JsonNode node, String field) {
        String v = node.path(field).asText("").trim();
        return v.isEmpty() ? null : v;
    }
}

package com.zhilv.ai;

import com.zhilv.common.BusinessException;
import com.zhilv.dto.TripPlan;
import com.zhilv.dto.TripRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import tools.jackson.databind.ObjectMapper;

/**
 * Python ai-service 的 Java 客户端(D18)。
 * RestClient 把 TripRequest 序列化成 snake_case JSON POST 到 /generate,
 * 响应反序列化成 TripPlan。ai-service 没启动 / 返回错误时转成可读的中文异常。
 */
@Service
public class AiServiceClient {

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public AiServiceClient(@Value("${app.ai.base-url:http://localhost:8100}") String baseUrl,
                           ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.restClient = RestClient.builder().baseUrl(baseUrl).build();
    }

    /** 把用户表单交给 DeepSeek,拿回一份 TripPlan(若 AI 调用失败抛 BusinessException) */
    public TripPlan generate(TripRequest req) {
        try {
            return restClient.post()
                    .uri("/generate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(req)
                    .retrieve()
                    .body(TripPlan.class);
        } catch (RestClientResponseException e) {
            throw new BusinessException(502,
                    "AI 服务返回错误(HTTP " + e.getStatusCode().value() + "):" + extractDetail(e.getResponseBodyAsString()));
        } catch (ResourceAccessException e) {
            throw new BusinessException(502, "AI 服务(8100)连不上,请先启动 ai-service");
        }
    }

    /** ai-service 出错时返回 {"detail":"..."},把 detail 抠出来给用户看 */
    private String extractDetail(String body) {
        if (body == null || body.isBlank()) {
            return "";
        }
        try {
            String detail = objectMapper.readTree(body).path("detail").asText("");
            return detail.isBlank() ? body : detail;
        } catch (Exception e) {
            return body.length() > 200 ? body.substring(0, 200) : body;
        }
    }
}

package com.zhilv.ai;

import com.zhilv.common.BusinessException;
import com.zhilv.dto.ChatTurnResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Python ai-service 对话客户端(与表单生成共用 base-url)。
 * 生成行程那一轮可能长达几分钟,用 8 分钟请求超时(与前端一致),不让慢请求被提前掐断。
 */
@Service
public class ChatAiClient {

    private final String baseUrl;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public ChatAiClient(@Value("${app.ai.base-url:http://localhost:8100}") String baseUrl,
                        ObjectMapper objectMapper) {
        this.baseUrl = (baseUrl == null ? "" : baseUrl.trim()).replaceAll("/+$", "");
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    /** 发一轮对话给 ai-service /chat,返回规范化结果;连不上/出错抛可读 BusinessException */
    public ChatTurnResponse chat(Long threadId, String message, String action) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("thread_id", threadId.toString());
        body.put("message", message == null ? "" : message);
        body.put("action", action == null || action.isBlank() ? "chat" : action);

        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "/chat"))
                    .timeout(Duration.ofSeconds(480))
                    .header("Content-Type", "application/json; charset=utf-8")
                    .POST(HttpRequest.BodyPublishers.ofString(
                            objectMapper.writeValueAsString(body), StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> resp = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                throw new BusinessException(502,
                        "AI 对话服务返回错误(HTTP " + resp.statusCode() + "):" + extractDetail(resp.body()));
            }
            JsonNode root = objectMapper.readTree(resp.body());
            boolean lowBudget = root.path("low_budget").asBoolean(false);
            Double minBudget = root.hasNonNull("min_budget") ? root.get("min_budget").asDouble() : null;
            return new ChatTurnResponse(
                    text(root, "reply", ""),
                    text(root, "status", "collecting"),
                    root.hasNonNull("ready") && root.get("ready").asBoolean(false),
                    nodeToParams(root.get("params")),
                    nodeToParams(root.get("plan")),
                    null,
                    lowBudget,
                    minBudget,
                    text(root, "intent", null));
        } catch (BusinessException e) {
            throw e;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BusinessException(502, "AI 对话请求被中断");
        } catch (Exception e) {
            throw new BusinessException(502, "AI 对话服务(8100)连不上,请先启动 ai-service");
        }
    }

    private Map<String, Object> nodeToParams(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = objectMapper.convertValue(node, Map.class);
            return map;
        } catch (Exception e) {
            return null;
        }
    }

    private String text(JsonNode root, String field, String fallback) {
        JsonNode n = root.get(field);
        return n == null || n.isNull() ? fallback : n.asText();
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

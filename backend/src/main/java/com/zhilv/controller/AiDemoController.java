package com.zhilv.controller;

import com.zhilv.ai.AiServiceClient;
import com.zhilv.common.ApiResponse;
import com.zhilv.dto.TripPlan;
import com.zhilv.dto.TripRequest;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * D18 临时验证接口:确认 Spring Boot 能调到 Python ai-service。
 * POST /api/ai/generate-test:接收与 /api/trips 相同的表单 → 调 AiServiceClient 生成 TripPlan。
 * D19 会把生成逻辑并进 POST /api/trips(提交即生成落库),届时本接口可删。
 */
@RestController
@RequestMapping("/api/ai")
public class AiDemoController {

    private final AiServiceClient aiServiceClient;

    public AiDemoController(AiServiceClient aiServiceClient) {
        this.aiServiceClient = aiServiceClient;
    }

    @PostMapping("/generate-test")
    public ApiResponse<TripPlan> generateTest(@RequestBody TripRequest req) {
        return ApiResponse.success(aiServiceClient.generate(req));
    }
}

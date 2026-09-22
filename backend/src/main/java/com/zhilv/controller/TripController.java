package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import com.zhilv.common.BusinessException;
import com.zhilv.dto.TripPlan;
import com.zhilv.dto.TripRequest;
import com.zhilv.entity.Trip;
import com.zhilv.repository.UserRepository;
import com.zhilv.service.TripService;
import org.springframework.data.domain.Page;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 行程接口(需登录,token 由 SecurityConfig 拦截):
 * POST 提交表单请求→落草稿;GET 查当前用户的历史行程列表。
 * 当前登录用户名由 JwtAuthenticationFilter 放进 SecurityContext。
 */
@RestController
@RequestMapping("/api/trips")
public class TripController {

    private final TripService tripService;
    private final UserRepository userRepository;

    public TripController(TripService tripService, UserRepository userRepository) {
        this.tripService = tripService;
        this.userRepository = userRepository;
    }

    @PostMapping
    public ApiResponse<Trip> create(@RequestBody TripRequest req) {
        return ApiResponse.success(tripService.create(currentUserId(), req));
    }

    @GetMapping
    public ApiResponse<Page<Trip>> list(@RequestParam(defaultValue = "0") int page,
                                        @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.success(tripService.pageByUser(currentUserId(), page, size));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        tripService.delete(currentUserId(), id);
        return ApiResponse.success();
    }

    /** 导出行程全量 TripPlan(当前草稿为无 days 的基础版,生成链路落库后自动导出完整版) */
    @GetMapping("/{id}/export")
    public ApiResponse<TripPlan> export(@PathVariable Long id) {
        return ApiResponse.success(tripService.export(currentUserId(), id));
    }

    /** 从 SecurityContext 里的用户名反查 userId */
    private Long currentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String username = auth.getName();
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new BusinessException(401, "未登录"))
                .getId();
    }
}

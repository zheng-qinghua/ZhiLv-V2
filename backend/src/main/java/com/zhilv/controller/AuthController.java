package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import com.zhilv.config.JwtUtil;
import com.zhilv.config.TokenBlacklist;
import com.zhilv.dto.AuthRequest;
import com.zhilv.dto.AuthResponse;
import com.zhilv.service.UserService;
import io.jsonwebtoken.Claims;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证接口:/register 建账号,/login 换 token。
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserService userService;
    private final JwtUtil jwtUtil;
    private final TokenBlacklist tokenBlacklist;

    public AuthController(UserService userService, JwtUtil jwtUtil, TokenBlacklist tokenBlacklist) {
        this.userService = userService;
        this.jwtUtil = jwtUtil;
        this.tokenBlacklist = tokenBlacklist;
    }

    @PostMapping("/register")
    public ApiResponse<Void> register(@RequestBody AuthRequest req) {
        userService.register(req.username(), req.password());
        return ApiResponse.success();
    }

    @PostMapping("/login")
    public ApiResponse<AuthResponse> login(@RequestBody AuthRequest req) {
        return ApiResponse.success(userService.login(req.username(), req.password()));
    }

    /** 登出:把当前 token 拉黑,TTL 设为它剩余的寿命;之后同 token 访问受保护接口一律 401 */
    @PostMapping("/logout")
    public ApiResponse<Void> logout(@RequestHeader("Authorization") String authHeader) {
        String token = authHeader.substring("Bearer ".length());
        Claims claims = jwtUtil.parseToken(token);
        long ttlSeconds = Math.max(1, (claims.getExpiration().getTime() - System.currentTimeMillis()) / 1000);
        tokenBlacklist.add(token, ttlSeconds);
        return ApiResponse.success();
    }
}

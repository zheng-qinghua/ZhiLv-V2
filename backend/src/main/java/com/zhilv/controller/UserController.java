package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 需要登录才能访问的示例接口:返回当前登录用户。
 * D9 用它来演示"不带 token 被拦、带 token 放行"。
 */
@RestController
@RequestMapping("/api/user")
public class UserController {

    @GetMapping("/me")
    public ApiResponse<Map<String, String>> me() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        return ApiResponse.success(Map.of("username", auth.getName()));
    }
}

package com.zhilv.dto;

/** 登录成功的响应:前端拿到 token,之后每个请求都带上它证明身份 */
public record AuthResponse(String token, String username) {
}

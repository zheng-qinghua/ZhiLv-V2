package com.zhilv.dto;

/** 注册/登录共用的请求体 */
public record AuthRequest(String username, String password) {
}

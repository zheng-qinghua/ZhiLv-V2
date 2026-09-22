package com.zhilv.common;

/**
 * 业务异常:业务规则不满足时抛出(如用户名已存在、密码错误)。
 * code 同时作为 HTTP 状态码和响应体里的 code。由全局异常处理器统一转成 ApiResponse。
 */
public class BusinessException extends RuntimeException {

    private final int code;

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}

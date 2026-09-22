package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @GetMapping("/")
    public ApiResponse<String> hello() {
        return ApiResponse.success("你好!智旅云图 Spring Boot 后端启动成功!");
    }

    /** 演示用:故意抛异常,验证全局异常处理器把它变成统一 JSON。 */
    @GetMapping("/demo/error")
    public String demoError() {
        throw new IllegalStateException("这是演示异常:全局处理器应该把它变成统一 JSON");
    }
}

package com.zhilv.controller;

import com.zhilv.common.ApiResponse;
import com.zhilv.common.BusinessException;
import com.zhilv.dto.ChatTurnRequest;
import com.zhilv.dto.ChatTurnResponse;
import com.zhilv.entity.ChatSession;
import com.zhilv.repository.UserRepository;
import com.zhilv.service.ChatService;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 对话式规划接口(需登录):建会话 + 每轮发言/确认。
 * 归属由 ChatService 判定;当前登录用户名由 JwtAuthenticationFilter 放进 SecurityContext。
 */
@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;
    private final UserRepository userRepository;

    public ChatController(ChatService chatService, UserRepository userRepository) {
        this.chatService = chatService;
        this.userRepository = userRepository;
    }

    /** 新建一个对话式规划会话,返回含 id */
    @PostMapping("/sessions")
    public ApiResponse<ChatSession> createSession() {
        return ApiResponse.success(chatService.createSession(currentUserId()));
    }

    /** 会话下发一轮发言/确认 */
    @PostMapping("/sessions/{id}/messages")
    public ApiResponse<ChatTurnResponse> send(@PathVariable Long id, @RequestBody ChatTurnRequest req) {
        return ApiResponse.success(chatService.send(currentUserId(), id, req));
    }

    private Long currentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String username = auth.getName();
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new BusinessException(401, "未登录"))
                .getId();
    }
}

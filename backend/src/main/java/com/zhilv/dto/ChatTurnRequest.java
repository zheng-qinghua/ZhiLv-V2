package com.zhilv.dto;

/**
 * 对话一轮入参(POST /api/chat/sessions/{id}/messages)。
 * action: chat=普通发言;confirm=点「确认行程」触发生成(不带用户气泡)。
 */
public record ChatTurnRequest(
        String message,
        String action
) {}

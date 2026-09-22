package com.zhilv.service;

import com.zhilv.ai.ChatAiClient;
import com.zhilv.common.BusinessException;
import com.zhilv.dto.ChatTurnRequest;
import com.zhilv.dto.ChatTurnResponse;
import com.zhilv.dto.TripPlan;
import com.zhilv.entity.ChatMessage;
import com.zhilv.entity.ChatSession;
import com.zhilv.entity.Trip;
import com.zhilv.repository.ChatMessageRepository;
import com.zhilv.repository.ChatSessionRepository;
import org.springframework.stereotype.Service;
import tools.jackson.databind.ObjectMapper;

/**
 * 对话会话业务(M2):
 *  - createSession:建一个"对话式规划"会话(归属当前用户)。
 *  - send:收用户消息 → 落 chat_messages → 转发 ai-service /chat(thread=会话id) → 落 AI 回复。
 * 规则:会话归属判定在这里做(拿别人的 sessionId 一律按不存在处理)。
 * 说明:真正的"对话状态"在 ai-service 侧(Redis)维护;这里只做会话归属与消息落库。
 * M4:confirm 生成那轮,ai-service 返回完整 TripPlan,这里落库成 CHAT 来源行程,
 *     并把已落库行程随响应带回,前端据此跳结果页。
 */
@Service
public class ChatService {

    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final ChatAiClient chatAiClient;
    private final TripService tripService;
    private final ObjectMapper objectMapper;

    public ChatService(ChatSessionRepository chatSessionRepository,
                       ChatMessageRepository chatMessageRepository,
                       ChatAiClient chatAiClient,
                       TripService tripService,
                       ObjectMapper objectMapper) {
        this.chatSessionRepository = chatSessionRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.chatAiClient = chatAiClient;
        this.tripService = tripService;
        this.objectMapper = objectMapper;
    }

    public ChatSession createSession(Long userId) {
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle("对话规划");
        return chatSessionRepository.save(session);
    }

    public ChatTurnResponse send(Long userId, Long sessionId, ChatTurnRequest req) {
        ChatSession session = chatSessionRepository.findById(sessionId)
                .orElseThrow(() -> new BusinessException(404, "会话不存在"));
        if (!userId.equals(session.getUserId())) {
            throw new BusinessException(404, "会话不存在");
        }

        boolean confirm = req.action() != null && "confirm".equalsIgnoreCase(req.action().trim());
        // confirm 是点按钮触发的"生成指令",不产生用户气泡,也不落 USER 消息
        String message = confirm ? "" : (req.message() == null ? "" : req.message());
        if (!confirm && !message.isBlank()) {
            saveMessage(sessionId, "USER", message);
        }

        ChatTurnResponse resp = chatAiClient.chat(sessionId, message,
                confirm ? "confirm" : "chat");

        String reply = resp.reply();
        if (reply != null && !reply.isBlank()) {
            saveMessage(sessionId, "ASSISTANT", reply);
        }

        // M4:生成闭环 —— 把 ai 返回的 TripPlan 落库成 CHAT 行程,随响应带回给前端
        if ("generated".equalsIgnoreCase(resp.status()) && resp.plan() != null) {
            TripPlan plan = objectMapper.convertValue(resp.plan(), TripPlan.class);
            Trip trip = tripService.createFromPlan(userId, plan);
            return new ChatTurnResponse(resp.reply(), resp.status(), resp.ready(),
                    resp.params(), null, trip, resp.lowBudget(), resp.minBudget());
        }
        return resp;
    }

    private void saveMessage(Long sessionId, String role, String content) {
        ChatMessage msg = new ChatMessage();
        msg.setSessionId(sessionId);
        msg.setRole(role);
        msg.setContent(content);
        chatMessageRepository.save(msg);
    }
}

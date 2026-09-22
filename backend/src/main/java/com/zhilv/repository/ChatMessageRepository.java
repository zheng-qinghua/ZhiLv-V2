package com.zhilv.repository;

import com.zhilv.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

    /** 按会话查消息,按时间从旧到新(聊天顺序) */
    List<ChatMessage> findBySessionIdOrderByCreatedAtAsc(Long sessionId);
}

package com.zhilv.repository;

import com.zhilv.entity.ChatSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ChatSessionRepository extends JpaRepository<ChatSession, Long> {

    /** 按用户查会话列表,新的排前面 */
    List<ChatSession> findByUserIdOrderByCreatedAtDesc(Long userId);
}

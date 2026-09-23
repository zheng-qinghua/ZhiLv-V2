package com.zhilv.dto;

import com.zhilv.entity.Trip;

import java.util.Map;

/**
 * 对话一轮结果(ai-service /chat 透传)。
 * status: collecting(继续聊) | await_confirm | budget_low(预算不足已拦截) | generated(已生成) | failed
 * ready:  目的地+时间已确定,可点「确认行程」;预算过低时 ai-service 会把它压成 false
 * params: 当前已确定参数字典(前端参数条展示)
 * plan:   ai-service 返回的原始 TripPlan(snake_case JSON),仅 generated 轮有;
 *         ChatService 用它落库,再换成 trip 回给前端。
 * trip:   已落库的行程实体(CHAT 来源),仅 generated 轮有(前端据此跳结果页)。
 * lowBudget / minBudget: ai-service 判定"用户预算低于路线最低花费"时置位;
 *         minBudget 为预估最低总花费(含往返大交通),前端据此提示用户加预算/接受压缩。
 * intent: supervisor 判定的本轮意图(chitchat/guide/weather/budget/collect/plan/revise)。
 *         只透传,Java 不解读 —— 前端拿它做气泡小标签,测试拿它统计路由准确率。
 */
public record ChatTurnResponse(
        String reply,
        String status,
        Boolean ready,
        Map<String, Object> params,
        Map<String, Object> plan,
        Trip trip,
        Boolean lowBudget,
        Double minBudget,
        String intent
) {
    /** 普通对话轮:没有生成结果,也没有预算拦截 */
    public ChatTurnResponse(String reply, String status, Boolean ready, Map<String, Object> params) {
        this(reply, status, ready, params, null, null, null, null, null);
    }

    /** 携带完整 TripPlan 的构造(落库与否由 ChatService 判断) */
    public ChatTurnResponse(String reply, String status, Boolean ready,
                            Map<String, Object> params, Map<String, Object> plan) {
        this(reply, status, ready, params, plan, null, null, null, null);
    }
}

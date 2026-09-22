package com.zhilv.config;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * token 黑名单:登出时把 token 记进 Redis,TTL 等于该 token 剩余有效期,
 * 到期自动消失,不需要手动清理。key 形如 jwt:blacklist:<完整token>。
 */
@Component
public class TokenBlacklist {

    private static final String PREFIX = "jwt:blacklist:";

    private final StringRedisTemplate redis;

    public TokenBlacklist(StringRedisTemplate redis) {
        this.redis = redis;
    }

    public void add(String token, long ttlSeconds) {
        redis.opsForValue().set(PREFIX + token, "1", Duration.ofSeconds(ttlSeconds));
    }

    public boolean contains(String token) {
        return Boolean.TRUE.equals(redis.hasKey(PREFIX + token));
    }
}

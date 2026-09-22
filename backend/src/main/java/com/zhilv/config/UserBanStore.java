package com.zhilv.config;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * 用户封禁(账号拉黑):被封禁的账号不能登录,已签发的 token 也全部失效。
 * key 形如 user:ban:<用户名>,置 1 即封禁;删除该 key 即解封。
 * 演示阶段先用 redis-cli 手动置位,以后可接管理后台接口。
 */
@Component
public class UserBanStore {

    private static final String PREFIX = "user:ban:";

    private final StringRedisTemplate redis;

    public UserBanStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    public void ban(String username) {
        redis.opsForValue().set(PREFIX + username, "1");
    }

    public void unban(String username) {
        redis.delete(PREFIX + username);
    }

    public boolean isBanned(String username) {
        return Boolean.TRUE.equals(redis.hasKey(PREFIX + username));
    }
}

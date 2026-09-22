package com.zhilv.service;

import com.zhilv.common.BusinessException;
import com.zhilv.config.JwtUtil;
import com.zhilv.config.UserBanStore;
import com.zhilv.dto.AuthResponse;
import com.zhilv.entity.User;
import com.zhilv.repository.UserRepository;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

/**
 * 注册/登录业务:密码 BCrypt 哈希存储,登录成功签发 JWT。
 * 校验失败抛 BusinessException,由全局异常处理器统一转成 JSON。
 */
@Service
public class UserService {

    private final UserRepository userRepository;
    private final JwtUtil jwtUtil;
    private final UserBanStore userBanStore;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public UserService(UserRepository userRepository, JwtUtil jwtUtil, UserBanStore userBanStore) {
        this.userRepository = userRepository;
        this.jwtUtil = jwtUtil;
        this.userBanStore = userBanStore;
    }

    public void register(String username, String password) {
        if (userRepository.existsByUsername(username)) {
            throw new BusinessException(400, "用户名已存在");
        }
        User user = new User();
        user.setUsername(username);
        user.setPassword(passwordEncoder.encode(password));
        userRepository.save(user);
    }

    public AuthResponse login(String username, String password) {
        if (userBanStore.isBanned(username)) {
            throw new BusinessException(403, "你已被拉黑,无法登录");
        }
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new BusinessException(401, "用户名或密码错误"));
        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new BusinessException(401, "用户名或密码错误");
        }
        String token = jwtUtil.generateToken(user.getUsername(), user.getId());
        return new AuthResponse(token, user.getUsername());
    }
}

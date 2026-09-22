package com.zhilv.config;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * 安全配置:定义哪些路径放行、哪些路径要带 token,以及 401 时返回统一 JSON。
 * 规则(按顺序匹配):登录/注册、登录页面、静态资源放行;其余 /api/** 必须已登录。
 * 无状态(STATELESS):服务器不存 session,全靠每个请求带的 token 判断身份。
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtUtil jwtUtil;
    private final TokenBlacklist tokenBlacklist;
    private final UserBanStore userBanStore;

    public SecurityConfig(JwtUtil jwtUtil, TokenBlacklist tokenBlacklist, UserBanStore userBanStore) {
        this.jwtUtil = jwtUtil;
        this.tokenBlacklist = tokenBlacklist;
        this.userBanStore = userBanStore;
    }

    /** JWT 过滤器作为 bean 提供,并加进下面的过滤器链 */
    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter(jwtUtil, tokenBlacklist, userBanStore);
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/login", "/api/auth/register", "/error").permitAll()
                .requestMatchers("/", "/demo/**", "/login.html", "/favicon.ico").permitAll()
                .requestMatchers("/*.html", "/*.css", "/*.js").permitAll()
                .requestMatchers("/api/**").authenticated()
                .anyRequest().permitAll())
            .exceptionHandling(ex -> ex.authenticationEntryPoint(unauthorizedEntryPoint()))
            .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    /** 未登录/被拦截时,写统一 JSON 而不是 Spring 默认的空 401 页面 */
    private AuthenticationEntryPoint unauthorizedEntryPoint() {
        return (request, response, authException) -> {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":401,\"message\":\"未登录或 token 无效\",\"data\":null}");
        };
    }
}

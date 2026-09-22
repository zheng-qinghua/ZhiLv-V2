package com.zhilv.service;

import com.zhilv.ai.AiServiceClient;
import com.zhilv.common.BusinessException;
import com.zhilv.dto.TripPlan;
import com.zhilv.dto.TripRequest;
import com.zhilv.entity.Trip;
import com.zhilv.repository.TripRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 行程业务(D19):提交表单 → 调 ai-service 生成完整 TripPlan → 落库。
 * plan_json 存完整行程 JSON(含每日安排 days),顶层字段拆出来供列表展示;
 * summary/tips 一并落库。ai-service 不可用/生成失败时抛 502,本次提交失败。
 */
@Service
public class TripService {

    private final TripRepository tripRepository;
    private final ObjectMapper objectMapper;
    private final AiServiceClient aiServiceClient;
    private final AmapPlaceService amapPlaceService;

    public TripService(TripRepository tripRepository, ObjectMapper objectMapper,
                       AiServiceClient aiServiceClient, AmapPlaceService amapPlaceService) {
        this.tripRepository = tripRepository;
        this.objectMapper = objectMapper;
        this.aiServiceClient = aiServiceClient;
        this.amapPlaceService = amapPlaceService;
    }

    public Trip create(Long userId, TripRequest req) {
        if (req.departure() == null || req.departure().isBlank()) {
            throw new BusinessException(400, "出发地不能为空");
        }
        if (req.destination() == null || req.destination().isBlank()) {
            throw new BusinessException(400, "目的地不能为空");
        }
        if (req.start_date() == null || req.end_date() == null) {
            throw new BusinessException(400, "开始日期和结束日期不能为空");
        }
        if (req.travelers() == null || req.travelers() < 1) {
            throw new BusinessException(400, "出行人数至少为 1");
        }
        if (req.budget() == null || req.budget().signum() <= 0) {
            throw new BusinessException(400, "预算需大于 0");
        }

        LocalDate start;
        LocalDate end;
        try {
            start = LocalDate.parse(req.start_date());
            end = LocalDate.parse(req.end_date());
        } catch (Exception e) {
            throw new BusinessException(400, "日期格式须为 yyyy-MM-dd,如 2026-09-01");
        }
        if (end.isBefore(start)) {
            throw new BusinessException(400, "结束日期不能早于开始日期");
        }
        int dayCount = (int) ChronoUnit.DAYS.between(start, end) + 1;

        // D19:提交即调 ai-service 生成完整行程(不再落空草稿);AI 不可用/生成失败会抛 502
        TripPlan plan = aiServiceClient.generate(req);
        // D21(模块6):生成后先让高德给每个景点/餐饮/住宿补真实坐标、地址、图片,再一起落库
        plan = amapPlaceService.enrich(plan);
        String planJson;
        try {
            planJson = objectMapper.writeValueAsString(plan);
        } catch (Exception e) {
            throw new BusinessException(500, "行程序列化失败");
        }

        // 标题:用户自己填的优先,没填用 AI 起的
        String title = (req.title() == null || req.title().isBlank()) ? plan.title() : req.title();

        Trip trip = new Trip();
        trip.setUserId(userId);
        trip.setTitle(title);
        trip.setDestination(plan.destination());
        trip.setStartDate(start);
        trip.setEndDate(end);
        trip.setDayCount(dayCount);
        trip.setTravelers(req.travelers());
        trip.setBudget(req.budget());
        trip.setPreferences(toJsonArray(plan.preferences() == null ? req.preferences() : plan.preferences()));
        trip.setPace(plan.pace());
        trip.setSpecialNotes(plan.special_notes());
        trip.setSummary(plan.summary());
        trip.setTips(toJsonArray(plan.tips()));
        trip.setSource("FORM");
        trip.setPlanJson(planJson);
        return tripRepository.save(trip);
    }

    /**
     * 对话式确认生成(CHAT):ai-service /chat 已返回完整 TripPlan,这里补高德点位后直接落库。
     * 与 create(FORM)同构,只是日期/预算/标题等都以 AI 返回为准(对话端无表单强校验)。
     */
    public Trip createFromPlan(Long userId, TripPlan plan) {
        if (plan == null || plan.destination() == null || plan.destination().isBlank()) {
            throw new BusinessException(500, "AI 未返回有效行程,请重试");
        }
        LocalDate start = null;
        LocalDate end = null;
        try {
            if (plan.start_date() != null) {
                start = LocalDate.parse(plan.start_date());
            }
            if (plan.end_date() != null) {
                end = LocalDate.parse(plan.end_date());
            }
        } catch (Exception e) {
            throw new BusinessException(400, "行程日期格式错误");
        }
        int dayCount = plan.day_count();
        if (dayCount <= 0 && start != null && end != null) {
            dayCount = (int) ChronoUnit.DAYS.between(start, end) + 1;
        }

        // 与 create 同路:高德补全后再序列化落库,保证结果页坐标/图片齐全
        plan = amapPlaceService.enrich(plan);
        String planJson;
        try {
            planJson = objectMapper.writeValueAsString(plan);
        } catch (Exception e) {
            throw new BusinessException(500, "行程序列化失败");
        }

        Trip trip = new Trip();
        trip.setUserId(userId);
        trip.setTitle(plan.title());
        trip.setDestination(plan.destination());
        trip.setStartDate(start);
        trip.setEndDate(end);
        trip.setDayCount(dayCount);
        trip.setTravelers(plan.travelers());
        trip.setBudget(plan.budget());
        trip.setPreferences(toJsonArray(plan.preferences()));
        trip.setPace(plan.pace());
        trip.setSpecialNotes(plan.special_notes());
        trip.setSummary(plan.summary());
        trip.setTips(toJsonArray(plan.tips()));
        trip.setSource("CHAT");
        trip.setPlanJson(planJson);
        return tripRepository.save(trip);
    }

    public Page<Trip> pageByUser(Long userId, int page, int size) {
        Pageable pageable = PageRequest.of(Math.max(page, 0), Math.max(size, 1));
        return tripRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    public void delete(Long userId, Long id) {
        tripRepository.delete(getOwned(userId, id));
    }

    /**
     * 导出行程全量:若 plan_json 已有完整行程(生成链路落库后),直接解析成 TripPlan;
     * 否则(草稿阶段)由实体基础字段构造一份没有每日安排的 TripPlan。
     * 导出时统一回填:id 换成真实行程 id(AI 输出恒为 null);title 换成 trips 表权威标题
     * (用户填了自己的标题时,plan_json 里还是 AI 起的标题,列表与详情会不一致)。
     */
    public TripPlan export(Long userId, Long id) {
        Trip trip = getOwned(userId, id);
        String planJson = trip.getPlanJson();
        if (planJson != null && !planJson.isBlank()) {
            try {
                TripPlan plan = objectMapper.readValue(planJson, TripPlan.class);
                boolean needId = plan.id() == null;
                boolean needTitle = !trip.getTitle().equals(plan.title());
                // plan_json 落库时 TripPlan.source 恒为 null,导出时用 trips.source(FORM/CHAT)回填,
                // 这样无论从首页生成还是历史打开,结果页都能标出行程来源
                boolean needSource = trip.getSource() != null && !trip.getSource().equals(plan.source());
                return (needId || needTitle || needSource)
                        ? copyWith(plan, trip.getId(), trip.getTitle(),
                        trip.getSource(), trip.getCreatedAt() == null ? null : trip.getCreatedAt().toString())
                        : plan;
            } catch (Exception e) {
                throw new BusinessException(500, "行程数据解析失败");
            }
        }
        return buildBasePlan(trip);
    }

    /** 复制一份 TripPlan,把 id/title/source/created_at 换成 trips 表权威值(AI 输出这些字段恒为空) */
    private TripPlan copyWith(TripPlan plan, Long id, String title, String source, String createdAt) {
        return new TripPlan(
                id,
                title,
                plan.destination(),
                plan.departure(),
                plan.start_date(),
                plan.end_date(),
                plan.day_count(),
                plan.travelers(),
                plan.budget(),
                plan.budget_breakdown(),
                plan.estimated_budget(),
                plan.preferences(),
                plan.pace(),
                plan.special_notes(),
                plan.summary(),
                plan.tips(),
                plan.days(),
                source != null ? source : plan.source(),
                createdAt != null ? createdAt : plan.created_at());
    }

    /** 查到一条属于该用户的行程,否则 404(也能挡住"拿别人的行程 id") */
    private Trip getOwned(Long userId, Long id) {
        return tripRepository.findById(id)
                .filter(t -> t.getUserId().equals(userId))
                .orElseThrow(() -> new BusinessException(404, "行程不存在"));
    }

    /** 草稿基础字段凑一份 TripPlan,days 暂时为空 */
    private TripPlan buildBasePlan(Trip trip) {
        return new TripPlan(
                trip.getId(),
                trip.getTitle(),
                trip.getDestination(),
                null,   // 草稿/旧数据无独立出发地列,只随 planJson 走
                trip.getStartDate() == null ? null : trip.getStartDate().toString(),
                trip.getEndDate() == null ? null : trip.getEndDate().toString(),
                trip.getDayCount() == null ? 0 : trip.getDayCount(),
                trip.getTravelers() == null ? 0 : trip.getTravelers(),
                trip.getBudget(),
                null,   // 草稿无预算明细
                null,
                parseJsonArray(trip.getPreferences()),
                trip.getPace(),
                trip.getSpecialNotes(),
                trip.getSummary(),
                parseJsonArray(trip.getTips()),
                List.of(),
                trip.getSource(),
                trip.getCreatedAt() == null ? null : trip.getCreatedAt().toString());
    }

    /** 把库里存的 JSON 数组字符串(如 ["美食","文化"])还原成 List */
    private List<String> parseJsonArray(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<?> list = objectMapper.readValue(json, List.class);
            return list.stream().map(String::valueOf).toList();
        } catch (Exception e) {
            return List.of();
        }
    }

    /** 偏好列表转成 JSON 数组字符串(如 ["美食","文化"]),与实体约定一致 */
    private String toJsonArray(List<String> values) {
        if (values == null || values.isEmpty()) {
            return "[]";
        }
        return values.stream()
                .map(v -> "\"" + v.replace("\\", "\\\\").replace("\"", "\\\"") + "\"")
                .collect(Collectors.joining(",", "[", "]"));
    }
}

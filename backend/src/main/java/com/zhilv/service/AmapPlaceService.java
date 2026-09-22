package com.zhilv.service;

import com.zhilv.dto.TripPlan;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 地图点位补全(D21,模块6):AI 生成行程后落库前,逐个把 景点/餐饮/住宿 的名词交给高德
 * 搜索成真实 POI,补上 坐标(location)、address、image_url、poi_id。搜索失败再退回 geocode
 * 只补坐标+地址。全程 best-effort:解析不出的点位原样保留,不让整条行程生成失败。
 * 搜索范围(D22,模块7 修复):每天先取 AI 标注的当天所在城市(city)限定搜索,避免跨城市
 * 行程里"栈桥"这类通用名在全国范围被匹配到异地;AI 没标才退回目的地整体。
 */
@Service
public class AmapPlaceService {

    private final String key;
    private final String baseUrl;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public AmapPlaceService(@Value("${app.amap.key:}") String key,
                            @Value("${app.amap.base-url:https://restapi.amap.com/v3}") String baseUrl,
                            ObjectMapper objectMapper) {
        this.key = key == null ? "" : key.trim();
        this.baseUrl = baseUrl == null ? "" : baseUrl.trim();
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    /** 只兜一层:任何点位补全都失败时返回原 plan,不阻断落库 */
    public TripPlan enrich(TripPlan plan) {
        if (plan == null || plan.days() == null || plan.days().isEmpty() || key.isBlank()) {
            return plan;
        }
        try {
            return rebuild(plan);
        } catch (Exception e) {
            return plan;
        }
    }

    private TripPlan rebuild(TripPlan plan) {
        String dest = plan.destination();
        List<TripPlan.Day> days = new ArrayList<>();
        for (TripPlan.Day day : plan.days()) {
            // 模块7:AI 为每天标注所在城市(city),用它限定当天所有点位的高德搜索范围,
            // 避免"栈桥"这类通用名在全国范围被匹配到异地。旧数据没 city 才退回目的地整体。
            String city = (day.city() == null || day.city().isBlank()) ? dest : day.city().trim();

            List<TripPlan.Spot> spots = new ArrayList<>();
            for (TripPlan.Spot sp : day.spots()) {
                spots.add(enrichSpot(sp, city));
            }
            List<TripPlan.Meal> meals = new ArrayList<>();
            for (TripPlan.Meal m : day.meals()) {
                meals.add(enrichMeal(m, city));
            }
            TripPlan.Hotel hotel = day.hotel() == null ? null : enrichHotel(day.hotel(), city);
            days.add(new TripPlan.Day(
                    day.day_index(), day.date(), day.theme(), day.city(),
                    spots, meals, day.transport(), day.note(), hotel));
        }
        return new TripPlan(
                plan.id(), plan.title(), plan.destination(), plan.departure(),
                plan.start_date(), plan.end_date(), plan.day_count(),
                plan.travelers(), plan.budget(), plan.budget_breakdown(),
                plan.estimated_budget(), plan.preferences(), plan.pace(),
                plan.special_notes(), plan.summary(), plan.tips(), days,
                plan.source(), plan.created_at());
    }

    private TripPlan.Spot enrichSpot(TripPlan.Spot sp, String city) {
        if (sp == null || sp.name() == null || sp.name().isBlank()) {
            return sp;
        }
        Lookup hit = find(sp.name(), city);
        if (hit == null) {
            return sp;
        }
        return new TripPlan.Spot(
                sp.name(), sp.description(),
                hit.location(sp.location()), sp.duration(),
                sp.image_url() == null ? hit.imageUrl : sp.image_url(),
                sp.estimated_cost(), hit.address, hit.poiId);
    }

    private TripPlan.Meal enrichMeal(TripPlan.Meal m, String city) {
        if (m == null || m.name() == null || m.name().isBlank()) {
            return m;
        }
        Lookup hit = find(m.name(), city);
        if (hit == null) {
            return m;
        }
        return new TripPlan.Meal(m.name(), m.notes(), m.estimated_cost(),
                hit.location(m.location()), hit.address,
                m.image_url() == null ? hit.imageUrl : m.image_url(), hit.poiId);
    }

    private TripPlan.Hotel enrichHotel(TripPlan.Hotel h, String city) {
        if (h == null || h.name() == null || h.name().isBlank()) {
            return h;
        }
        Lookup hit = find(h.name(), city);
        if (hit == null) {
            return h;
        }
        return new TripPlan.Hotel(h.name(), h.level(), h.estimated_cost(),
                hit.location(h.location()), hit.address,
                h.image_url() == null ? hit.imageUrl : h.image_url(), hit.poiId);
    }

    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(AmapPlaceService.class);

    /** 优先高德 POI 搜索(能拿图/地址/poi_id),失败退回 geocode(只有坐标+地址)。 */
    private Lookup find(String name, String city) {
        String keyword = cleanKeyword(name);
        try {
            JsonNode root = search(keyword, city);
            JsonNode best = pickBest(root.path("pois"), keyword);
            if (best != null) {
                double[] ll = splitLocation(best.path("location").asText(""));
                if (ll != null) {
                    String img = firstPhoto(best);
                    return new Lookup(ll[0], ll[1],
                            textOrNull(best, "address"),
                            textOrNull(best, "id"), img);
                }
            }
        } catch (Exception e) {
            log.warn("[amap] POI 搜索失败 name={} err={}", name, e.toString());
        }
        try {
            JsonNode root = get("/geocode/geo", Map.of(
                    "address", keyword,
                    "city", city == null ? "" : city,
                    "key", key));
            JsonNode gc = root.path("geocodes");
            if (gc.isArray() && !gc.isEmpty()) {
                JsonNode first = gc.get(0);
                double[] ll = splitLocation(first.path("location").asText(""));
                if (ll != null) {
                    return new Lookup(ll[0], ll[1], textOrNull(first, "formatted_address"),
                            null, null);
                }
            }
        } catch (Exception e) {
            log.warn("[amap] geocode 失败 name={} err={}", name, e.toString());
        }
        return null;
    }

    /** AI 造的名常带括号消歧后缀(如"××(小吃店)"),搜索前切掉,只留主干提高命中率 */
    private String cleanKeyword(String name) {
        String n = name == null ? "" : name.trim();
        int idx = n.indexOf('（');
        if (idx < 0) {
            idx = n.indexOf('(');
        }
        return idx > 0 ? n.substring(0, idx).trim() : n;
    }

    private JsonNode search(String keyword, String city) throws Exception {
        Map<String, String> params = new LinkedHashMap<>();
        params.put("keywords", keyword);
        params.put("city", city == null ? "" : city);
        params.put("offset", "5");
        params.put("page", "1");
        params.put("extensions", "all");
        params.put("citylimit", "true");
        params.put("key", key);
        return get("/place/text", params);
    }

    /** 挑候选:名称重叠且带图 > 名称重叠 > 首条,避免 AI 造的词条搜到无关 POI */
    private JsonNode pickBest(JsonNode pois, String keyword) {
        if (!pois.isArray()) {
            return null;
        }
        JsonNode first = null;
        JsonNode bestName = null;
        JsonNode bestNameImage = null;
        for (JsonNode poi : pois) {
            if (first == null) {
                first = poi;
            }
            String name = poi.path("name").asText("");
            boolean overlap = overlap(name, keyword);
            boolean hasImg = firstPhoto(poi) != null;
            if (overlap && hasImg && bestNameImage == null) {
                bestNameImage = poi;
            } else if (overlap && bestName == null) {
                bestName = poi;
            }
        }
        return bestNameImage != null ? bestNameImage : (bestName != null ? bestName : first);
    }

    private boolean overlap(String a, String b) {
        String na = a == null ? "" : a.toLowerCase();
        String nb = b == null ? "" : b.toLowerCase();
        if (na.isEmpty() || nb.isEmpty()) {
            return false;
        }
        return na.contains(nb) || nb.contains(na);
    }

    /** "经度,纬度" → [lat, lng];解析不出返回 null */
    private double[] splitLocation(String location) {
        if (location == null || !location.contains(",")) {
            return null;
        }
        try {
            String[] parts = location.split(",", 2);
            double lng = Double.parseDouble(parts[0].trim());
            double lat = Double.parseDouble(parts[1].trim());
            return new double[]{lat, lng};
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private String firstPhoto(JsonNode poi) {
        JsonNode photos = poi.path("photos");
        if (photos.isArray() && !photos.isEmpty()) {
            String url = photos.get(0).path("url").asText("").trim();
            return url.isEmpty() ? null : url;
        }
        return null;
    }

    private JsonNode get(String path, Map<String, String> params) throws Exception {
        // 个人开发者 key 默认并发配额约 3 QPS,逐个点位串行时也须限速,否则报 CUQPS_HAS_EXCEEDED_THE_LIMIT
        Thread.sleep(400);
        StringBuilder q = new StringBuilder(baseUrl).append(path).append("?");
        boolean first = true;
        for (Map.Entry<String, String> e : params.entrySet()) {
            if (!first) {
                q.append("&");
            }
            q.append(e.getKey()).append("=").append(enc(e.getValue()));
            first = false;
        }
        HttpRequest request = HttpRequest.newBuilder(URI.create(q.toString()))
                .timeout(Duration.ofSeconds(15))
                .GET()
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        JsonNode root = objectMapper.readTree(response.body());
        if (!"1".equals(root.path("status").asText())) {
            throw new RuntimeException("amap error:" + root.path("info").asText());
        }
        return root;
    }

    private String enc(String v) {
        return URLEncoder.encode(v == null ? "" : v, StandardCharsets.UTF_8);
    }

    private String textOrNull(JsonNode node, String field) {
        String v = node.path(field).asText("").trim();
        return v.isEmpty() ? null : v;
    }

    /** 解析出来的点位信息;location() 保留原坐标或改用查到的坐标。 */
    private record Lookup(Double lat, Double lng, String address, String poiId, String imageUrl) {
        TripPlan.Location location(TripPlan.Location original) {
            if (lat == null || lng == null) {
                return original;
            }
            return new TripPlan.Location(lat, lng);
        }
    }
}

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { marked } from "marked";

import { fetchWeatherForecast } from "../services/api";
import type { TripDay, TripPlan, WeatherForecastResponse } from "../types";
import AmapTripMap from "../components/AmapTripMap.vue";

const props = defineProps<{ plan: TripPlan | null }>();
const emit = defineEmits<{ backHome: []; viewHistory: [] }>();

/** 行程来源标签:后端落库后 source=FORM/CHAT,结果页据此提示该条怎么来的 */
const sourceLabel = computed(() =>
  props.plan?.source === "CHAT" ? "对话式生成" : props.plan?.source === "FORM" ? "表单式生成" : ""
);

function money(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return "-";
  return `¥${Number(n).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
}

/** null/undefined/非数一律当 0,便于按天汇总 */
function costNum(n: number | null | undefined): number {
  return n == null || Number.isNaN(Number(n)) ? 0 : Number(n);
}

/** 按天花费只对新生成(每天带 hotel)的行程渲染,旧数据提示 */
const hasDayCosts = computed(() => {
  const days = props.plan?.days;
  return !!days && days.length > 0 && days.some((d) => d.hotel != null);
});

/** 每天四项 + 合计:门票=Σ景点 estimated_cost,餐饮=Σ餐厅,交通=transport,住宿=hotel */
const dayCosts = computed(() => {
  const plan = props.plan;
  if (!plan || !hasDayCosts.value) return [];
  return (plan.days ?? []).map((day) => {
    const tickets = (day.spots ?? []).reduce((s, sp) => s + costNum(sp.estimated_cost), 0);
    const meals = (day.meals ?? []).reduce((s, m) => s + costNum(m.estimated_cost), 0);
    const transport = costNum(day.transport?.estimated_cost);
    const hotel = costNum(day.hotel?.estimated_cost);
    return {
      key: dayKey(day, day.day_index - 1),
      title: `第${day.day_index}天`,
      subtitle: day.theme || "",
      tickets,
      meals,
      transport,
      hotel,
      total: tickets + meals + transport + hotel,
    };
  });
});

/* ===== 天气(照源项目 Result.vue:按目的地拉高德天气,展示逐日预报) ===== */

const weather = ref<WeatherForecastResponse | null>(null);
const weatherLoading = ref(false);
const weatherError = ref("");

const WEATHER_WEEK: Record<string, string> = {
  "1": "周一", "2": "周二", "3": "周三", "4": "周四",
  "5": "周五", "6": "周六", "7": "周日",
};

function fmtWeatherDate(date?: string | null, week?: string | null): string {
  const md = date && date.length >= 10 ? date.slice(5) : "";
  const wk = week ? (WEATHER_WEEK[week] || "") : "";
  return md ? `${md} ${wk}`.trim() : wk || "待定";
}

async function loadWeather() {
  const dest = props.plan?.destination?.trim();
  if (!dest) {
    weather.value = null;
    return;
  }
  weatherLoading.value = true;
  weatherError.value = "";
  try {
    weather.value = await fetchWeatherForecast(dest);
  } catch {
    weather.value = null;
    weatherError.value = "天气信息加载失败,请稍后重试。";
  } finally {
    weatherLoading.value = false;
  }
}

watch(() => props.plan?.destination, () => { void loadWeather(); }, { immediate: true });

/** transport 兼容字符串或 {mode, note} 两种形状 */
function fmtTransport(transport: TripDay["transport"] | string | null): string {
  if (!transport) return "";
  if (typeof transport === "string") return transport;
  const parts = [transport.mode, transport.note].filter(Boolean);
  return parts.join(" · ");
}

function fmtLocation(spot: { location: { lat?: number | null; lng?: number | null } | null }): string {
  const loc = spot.location;
  if (!loc) return "";
  if (loc.lat != null && loc.lng != null) return `${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}`;
  return "";
}

function dayKey(day: TripDay, i: number): string {
  return `${day.day_index ?? i + 1}-${day.date ?? i}`;
}

/* ===== 地图点位明细 ===== */

type PointCat = "spot" | "meal" | "hotel";

interface PointInfo {
  key: string;
  dayIndex: number;
  date: string;
  name: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  imageUrl: string | null;
  desc: string;
  cat: PointCat;
}

const POINT_CAT_LABEL: Record<PointCat, string> = {
  spot: "景点",
  meal: "餐饮",
  hotel: "住宿",
};

function pointCatLabel(cat: PointCat): string {
  return POINT_CAT_LABEL[cat];
}

/** 把每天 景点/餐饮/住宿 拉平成点位列表(模块6;坐标等由后端生成时用高德补全) */
const mapPoints = computed<PointInfo[]>(() => {
  const plan = props.plan;
  if (!plan) return [];
  const points: PointInfo[] = [];
  for (const day of plan.days ?? []) {
    const date = day.date || "";
    for (const s of day.spots ?? []) {
      points.push({
        key: `d${day.day_index}-spot-${s.name}`,
        dayIndex: day.day_index ?? 0,
        date,
        name: s.name,
        address: s.address || "待补充",
        latitude: s.location?.lat ?? null,
        longitude: s.location?.lng ?? null,
        imageUrl: s.image_url || null,
        desc: s.description || "暂无说明",
        cat: "spot",
      });
    }
    for (const m of day.meals ?? []) {
      points.push({
        key: `d${day.day_index}-meal-${m.name}`,
        dayIndex: day.day_index ?? 0,
        date,
        name: m.name,
        address: m.address || "待补充",
        latitude: m.location?.lat ?? null,
        longitude: m.location?.lng ?? null,
        imageUrl: m.image_url || null,
        desc: m.notes || "暂无说明",
        cat: "meal",
      });
    }
    const h = day.hotel;
    if (h) {
      points.push({
        key: `d${day.day_index}-hotel-${h.name}`,
        dayIndex: day.day_index ?? 0,
        date,
        name: h.name,
        address: h.address || "待补充",
        latitude: h.location?.lat ?? null,
        longitude: h.location?.lng ?? null,
        imageUrl: h.image_url || null,
        desc: h.level ? `住宿档次:${h.level}` : "当晚住宿",
        cat: "hotel",
      });
    }
  }
  return points;
});

const brokenPointImgs = ref(new Set<string>());

function pointImgBroken(key: string): boolean {
  return brokenPointImgs.value.has(key);
}

function markPointImgBroken(key: string): void {
  brokenPointImgs.value = new Set(brokenPointImgs.value).add(key);
}

/* ===== 景点地图(模块7,只标景点,坐标由模块6落库时高德补全) ===== */

interface MapSpotPoint {
  key: string;
  dayIndex: number;
  date: string;
  theme: string;
  name: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  imageUrl: string | null;
  description: string;
}

const mapSpots = computed<MapSpotPoint[]>(() => {
  const plan = props.plan;
  if (!plan) return [];
  const out: MapSpotPoint[] = [];
  for (const day of plan.days ?? []) {
    for (const s of day.spots ?? []) {
      out.push({
        key: `map-d${day.day_index}-${s.name}`,
        dayIndex: day.day_index ?? 0,
        date: day.date || "",
        theme: day.theme || "",
        name: s.name,
        address: s.address || "待补充",
        latitude: s.location?.lat ?? null,
        longitude: s.location?.lng ?? null,
        imageUrl: s.image_url || null,
        description: s.description || "",
      });
    }
  }
  return out;
});

/* ===== 导出 Markdown ===== */

function mdYuan(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return "¥0";
  return `¥${Number(n).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
}

function mdPushCost(lines: string[], label: string, n: number | null | undefined): void {
  if (n != null && !Number.isNaN(Number(n))) lines.push(`  - ${label}:${mdYuan(n)}`);
}

function buildMarkdown(plan: TripPlan): string {
  const L: string[] = [];
  const dest = plan.destination || "未知目的地";

  L.push(`# ${dest} 行程单`, "");
  L.push(`- 行程 ID:${plan.id ?? "-"}`);
  L.push(`- 目的地:${dest}`);
  if (plan.departure?.trim()) L.push(`- 出发地:${plan.departure.trim()}`);
  L.push(`- 出行日期:${plan.start_date ?? "-"} ~ ${plan.end_date ?? "-"}`);
  L.push(`- 行程天数:${plan.day_count ?? plan.days?.length ?? 0} 天`);
  L.push(`- 出行人数:${plan.travelers ?? "-"} 人`);
  L.push(`- 出行节奏:${plan.pace || "适中"}`);
  if (plan.budget != null) L.push(`- 预算:${mdYuan(plan.budget)}`);
  if (plan.preferences?.length) L.push(`- 偏好:${plan.preferences.join("、")}`);

  L.push("", "## 行程概述");
  L.push(plan.summary?.trim() || "（暂无概述）");

  L.push("", "## 每日安排");
  for (const day of plan.days ?? []) {
    L.push("", `### Day ${day.day_index} ${day.theme?.trim() || "今日行程"}`.trimEnd());
    L.push(`- 日期:${day.date || "待定"}`);
    for (const sp of day.spots ?? []) {
      L.push(`- 主要景点:${sp.name}`);
      if (sp.duration?.trim()) L.push(`  - 游玩时长:${sp.duration.trim()}`);
      mdPushCost(L, "门票估算", sp.estimated_cost);
      L.push(`  - 说明:${sp.description?.trim() || "无"}`);
    }
    for (const meal of day.meals ?? []) {
      L.push(`- 餐饮建议:${meal.name}`);
      mdPushCost(L, "一餐/人均估算", meal.estimated_cost);
      L.push(`  - 说明:${meal.notes?.trim() || "无"}`);
    }
    if (day.hotel) {
      const cost = day.hotel.estimated_cost != null ? `(${mdYuan(day.hotel.estimated_cost)}/晚)` : "";
      L.push(`- 住宿安排:${day.hotel.name}(${day.hotel.level || "未标注档次"})${cost}`);
    }
    const tr = day.transport;
    if (tr?.mode?.trim()) {
      const notePart = tr.note?.trim() ? `;${tr.note.trim()}` : "";
      const cost = tr.estimated_cost != null ? `(${mdYuan(tr.estimated_cost)})` : "";
      L.push(`- 交通安排:${tr.mode.trim()}${notePart}${cost}`);
    }
    if (day.note?.trim()) L.push(`- 备注:${day.note.trim()}`);
  }

  L.push("", "## 预算拆分");
  if (plan.budget_breakdown) {
    const bb = plan.budget_breakdown;
    L.push(`- 门票:${mdYuan(bb.tickets)}`);
    L.push(`- 住宿:${mdYuan(bb.hotel)}`);
    L.push(`- 餐饮:${mdYuan(bb.meals)}`);
    L.push(`- 交通:${mdYuan(bb.transport)}`);
    if (plan.estimated_budget != null) L.push(`- 预估总花费:${mdYuan(plan.estimated_budget)}`);
  } else {
    L.push(`- 总预算:${mdYuan(plan.budget)}`);
  }

  if (plan.tips?.length) {
    L.push("", "## 旅行提示");
    for (const tip of plan.tips) {
      if (tip?.trim()) L.push(`- ${tip.trim()}`);
    }
  }

  return L.join("\n").trimEnd() + "\n";
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** 预览页里渲染的是 LLM 产出文本,落库后可能夹带原始 HTML,渲染前剥离 script/iframe 与事件属性 */
function sanitizeMdHtml(html: string): string {
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<iframe\b[^>]*>[\s\S]*?<\/iframe>/gi, "")
    .replace(/(<[a-z][a-z0-9]*)([^>]*>)/gi, (_whole, open: string, attrs: string) => {
      const clean = attrs.replace(/\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "");
      return `${open}${clean}`;
    })
    .replace(/javascript\s*:/gi, "");
}

function buildPreviewDoc(md: string, filename: string, title: string): string {
  const jsFilename = JSON.stringify(filename);
  const bodyHtml = sanitizeMdHtml(marked.parse(md) as string);
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${escapeHtml(title)}</title>
<style>
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f2f2f7; color: #1c1c1e; }
  .wrap { max-width: 860px; margin: 0 auto; padding: 24px 20px 60px; }
  .head { background: #ffffff; border: 1px solid #e5e5ea; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; }
  .head h1 { margin: 0 0 6px; font-size: 18px; }
  .head p { margin: 0; font-size: 13px; color: #8e8e93; }
  /* 渲染区:仿 VS Code markdown 预览 */
  .md-body { background: #ffffff; border: 1px solid #e5e5ea; border-radius: 14px; padding: 26px 32px 30px; font-size: 15px; line-height: 1.7; overflow-wrap: break-word; }
  .md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6 { margin: 26px 0 10px; line-height: 1.3; font-weight: 700; color: #1c1c1e; }
  .md-body h1:first-child, .md-body h2:first-child { margin-top: 0; }
  .md-body h1 { font-size: 30px; border-bottom: 1px solid #e5e5ea; padding-bottom: 12px; }
  .md-body h2 { font-size: 24px; border-bottom: 1px solid #e5e5ea; padding-bottom: 9px; }
  .md-body h3 { font-size: 19px; }
  .md-body h4 { font-size: 16px; }
  .md-body h5 { font-size: 14px; }
  .md-body h6 { font-size: 13px; color: #8e8e93; }
  .md-body p { margin: 10px 0; }
  .md-body ul, .md-body ol { margin: 10px 0; padding-left: 26px; }
  .md-body li { margin: 3px 0; }
  .md-body li > p { margin: 4px 0; }
  .md-body blockquote { margin: 12px 0; padding: 2px 16px; border-left: 4px solid #d0d7de; color: #57606a; background: #f6f8fa; border-radius: 0 6px 6px 0; }
  .md-body code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 13px; background: rgba(175, 184, 193, 0.2); border-radius: 4px; padding: 2px 5px; }
  .md-body pre { background: #f6f8fa; border: 1px solid #e5e5ea; border-radius: 8px; padding: 14px 16px; overflow-x: auto; margin: 12px 0; }
  .md-body pre code { background: none; padding: 0; font-size: 13px; line-height: 1.6; }
  .md-body hr { border: none; border-top: 2px solid #e5e5ea; margin: 26px 0; }
  .md-body a { color: #0366d6; text-decoration: none; }
  .md-body a:hover { text-decoration: underline; }
  .md-body img { max-width: 100%; border-radius: 6px; }
  .md-body table { border-collapse: collapse; margin: 12px 0; width: 100%; font-size: 14px; }
  .md-body th, .md-body td { border: 1px solid #d0d7de; padding: 6px 12px; text-align: left; }
  .md-body th { background: #f6f8fa; font-weight: 600; }
  .md-body input[type="checkbox"] { margin-right: 6px; }
  .dl-wrap { text-align: center; margin: 24px 0 8px; }
  .dl { border: none; border-radius: 12px; padding: 12px 34px; font-size: 15px; font-weight: 600; color: #ffffff; background: #007aff; cursor: pointer; }
  .dl:active { transform: scale(0.98); }
</style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <h1>📄 ${escapeHtml(title)}</h1>
      <p>下方为渲染后的 Markdown 预览(样式参考 VS Code),最下方有「下载 Markdown」按钮,下载的是原始 .md 文件。</p>
    </div>
    <div class="md-body">${bodyHtml}</div>
    <textarea id="raw" hidden>${escapeHtml(md)}</textarea>
    <div class="dl-wrap"><button class="dl" id="dl">⬇ 下载 Markdown</button></div>
  </div>
<script>
(function () {
  var raw = document.getElementById('raw');
  var btn = document.getElementById('dl');
  var filename = ${jsFilename};
  if (raw && btn) {
    btn.addEventListener('click', function () {
      var blob = new Blob([raw.value], { type: 'text/markdown;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(url); if (a.parentNode) a.parentNode.removeChild(a); }, 200);
    });
  }
})();
<\/script>
</body>
</html>`;
}

function exportMarkdown(): void {
  const plan = props.plan;
  if (!plan) return;
  const dest = plan.destination || "行程";
  const filename = `${dest.replace(/[\\/:*?"<>|]/g, "")}行程单.md`;
  const title = `${plan.title || dest} · Markdown 预览`;
  const win = window.open("", "_blank");
  if (!win) {
    window.alert("浏览器拦截了弹窗,请允许本站打开新窗口后再试一次。");
    return;
  }
  win.document.write(buildPreviewDoc(buildMarkdown(plan), filename, title));
  win.document.close();
}
</script>

<template>
  <section v-if="!plan" class="empty-state">
    <div class="ios-card empty-card">
      <h2>还没有生成结果</h2>
      <p class="empty-tip">先回到规划页,用「表单式」或「对话式」生成一条行程;生成后会自动保存、可到历史里查看。</p>
      <button class="ios-button ios-button--primary" @click="emit('backHome')">返回规划页</button>
    </div>
  </section>

  <section v-else class="result-page">
    <!-- 操作侧栏 -->
    <aside class="sidebar">
      <div class="sidebar__section">
        <div class="sidebar__label">操作</div>
        <button class="side-btn" @click="emit('backHome')">← 返回规划</button>
        <button class="side-btn" @click="emit('viewHistory')">历史列表</button>
      </div>

      <div class="sidebar__divider" />

      <div class="sidebar__section">
        <div class="sidebar__label">导出</div>
        <button class="side-btn" @click="exportMarkdown">⬇ 导出 Markdown</button>
      </div>

      <div class="sidebar__divider" />

      <div class="saved-box">
        <div class="sidebar__label">保存状态</div>
        <p class="saved-title">✓ 已自动保存</p>
        <p class="saved-id">行程 ID:{{ plan.id ?? "-" }}</p>
        <p class="saved-hint">本版本「提交即落库」,这条行程已在历史列表里,无需手动保存。</p>
      </div>
    </aside>

    <!-- 主内容 -->
    <div class="result-content">
      <!-- 行程概览 -->
      <div class="ios-card overview">
        <div class="overview-head">
          <h2 class="overview-title">{{ plan.title || `${plan.destination}旅行计划` }}</h2>
          <span v-if="sourceLabel" :class="['source-chip', { 'source-chip--chat': sourceLabel === '对话式生成' }]">{{ sourceLabel }}</span>
        </div>
        <div class="info-grid">
          <div v-if="plan.departure" class="info-row"><span class="info-label">出发地</span><span>{{ plan.departure }}</span></div>
          <div class="info-row"><span class="info-label">目的地</span><span>{{ plan.destination }}</span></div>
          <div class="info-row"><span class="info-label">日期</span><span>{{ plan.start_date }} ~ {{ plan.end_date }}</span></div>
          <div class="info-row"><span class="info-label">天数</span><span>{{ plan.day_count }} 天</span></div>
          <div class="info-row"><span class="info-label">人数</span><span>{{ plan.travelers }} 人</span></div>
          <div class="info-row"><span class="info-label">预算</span><span>{{ money(plan.budget) }}</span></div>
          <div class="info-row"><span class="info-label">节奏</span><span>{{ plan.pace || "-" }}</span></div>
        </div>
        <div v-if="plan.preferences?.length" class="chip-line">
          <span v-for="p in plan.preferences" :key="p" class="ios-tag">{{ p }}</span>
        </div>

        <p v-if="plan.special_notes" class="notes-line"><span class="info-label">特别备注:</span>{{ plan.special_notes }}</p>

        <p v-if="plan.summary" class="summary">{{ plan.summary }}</p>

        <div v-if="plan.tips?.length" class="tips-box">
          <div class="tips-title">旅行提示</div>
          <ul>
            <li v-for="(tip, i) in plan.tips" :key="i">{{ tip }}</li>
          </ul>
        </div>
      </div>

      <!-- 预算明细 -->
      <div class="ios-card budget-card">
        <div class="card-head">预算明细</div>
        <template v-if="plan.budget_breakdown">
          <div class="budget-grid">
            <div class="budget-item">
              <span class="info-label">景点门票</span>
              <b>{{ money(plan.budget_breakdown.tickets) }}</b>
            </div>
            <div class="budget-item">
              <span class="info-label">酒店住宿</span>
              <b>{{ money(plan.budget_breakdown.hotel) }}</b>
            </div>
            <div class="budget-item">
              <span class="info-label">餐饮费用</span>
              <b>{{ money(plan.budget_breakdown.meals) }}</b>
            </div>
            <div class="budget-item">
              <span class="info-label">交通费用</span>
              <b>{{ money(plan.budget_breakdown.transport) }}</b>
            </div>
          </div>
          <div class="budget-total">
            <span>预估总费用</span>
            <strong>{{ money(plan.estimated_budget) }}</strong>
          </div>
        </template>
        <p v-else class="old-tip">这条行程是旧数据,没有预算明细;重新生成一条即可查看。</p>
      </div>

      <!-- 按天花费 -->
      <div class="ios-card day-cost-card">
        <div class="card-head">按天花费</div>
        <template v-if="hasDayCosts">
          <div class="day-cost-grid">
            <div v-for="c in dayCosts" :key="c.key" class="day-cost-cell">
              <div class="day-cost-head">
                <span>{{ c.title }}</span>
                <span class="muted">{{ c.subtitle }}</span>
              </div>
              <div class="day-cost-body">
                <div class="cost-row"><span>门票</span><span class="cost-amt">{{ money(c.tickets) }}</span></div>
                <div class="cost-row"><span>餐饮</span><span class="cost-amt">{{ money(c.meals) }}</span></div>
                <div class="cost-row"><span>交通</span><span class="cost-amt">{{ money(c.transport) }}</span></div>
                <div class="cost-row"><span>住宿</span><span class="cost-amt">{{ money(c.hotel) }}</span></div>
                <div class="cost-row cost-row--total">
                  <span>当日合计</span>
                  <span class="cost-amt">{{ money(c.total) }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
        <p v-else class="old-tip">这条行程是旧数据,没有按天花费;重新生成一条即可查看。</p>
      </div>

      <!-- 天气信息 -->
      <div class="ios-card weather-card">
        <div class="card-head">天气信息<span v-if="weather?.city" class="weather-city">· {{ weather.city }}</span></div>
        <p v-if="weatherLoading" class="old-tip">正在加载天气…</p>
        <p v-else-if="weatherError" class="old-tip">{{ weatherError }}</p>
        <div v-else-if="weather && weather.days.length" class="weather-grid">
          <div v-for="(d, wi) in weather.days" :key="d.date || wi" class="weather-item">
            <div class="weather-item__date">{{ fmtWeatherDate(d.date, d.week) }}</div>
            <div class="weather-item__temp">{{ d.dayTemp || "-" }}° / {{ d.nightTemp || "-" }}°</div>
            <div class="weather-item__desc">
              {{ d.dayWeather || "未知" }} / {{ d.nightWeather || "未知" }}
            </div>
          </div>
        </div>
        <p v-else class="old-tip">暂无该城市天气信息。</p>
        <p v-if="weather?.reportTime" class="weather-report">预报发布:{{ weather.reportTime }}</p>
      </div>

      <!-- 景点地图(模块7) -->
      <div class="ios-card map-card">
        <div class="card-head">景点地图<span class="card-sub">景点按天连线,点标记看详情</span></div>
        <div class="map-holder">
          <AmapTripMap :points="mapSpots" />
        </div>
      </div>

      <!-- 地图点位明细 -->
      <div class="ios-card point-card">
        <div class="card-head">地图点位明细<span class="card-sub">景点 · 餐饮 · 住宿(坐标由高德补全)</span></div>
        <div v-if="mapPoints.length" class="point-grid">
          <div v-for="p in mapPoints" :key="p.key" class="point-cell">
            <div class="point-top">
              <span class="point-day">第{{ p.dayIndex }}天</span>
              <span :class="['point-tag', 'point-tag--' + p.cat]">{{ pointCatLabel(p.cat) }}</span>
              <span class="point-name">{{ p.name }}</span>
            </div>
            <img
              v-if="p.imageUrl && !pointImgBroken(p.key)"
              class="point-img"
              :src="p.imageUrl"
              :alt="p.name"
              loading="lazy"
              @error="markPointImgBroken(p.key)"
            />
            <div v-else class="point-img point-img--empty">暂无图片</div>
            <p class="point-line"><span class="muted">地址:</span>{{ p.address }}</p>
            <p class="point-desc">{{ p.desc }}</p>
            <p v-if="p.latitude != null && p.longitude != null" class="point-line point-coord">
              <span class="muted">坐标:</span>{{ Number(p.longitude).toFixed(5) }}, {{ Number(p.latitude).toFixed(5) }}
            </p>
          </div>
        </div>
        <p v-else class="old-tip">暂无点位(新生成的行程会带高德坐标)。</p>
      </div>

      <!-- 每日行程 -->
      <div class="ios-card day-card">
        <div class="card-head">每日行程</div>
        <p v-if="!plan.days || plan.days.length === 0" class="empty-tip">该行程暂无每日安排。</p>

        <div v-else class="day-list">
          <details
            v-for="(day, i) in plan.days"
            :key="dayKey(day, i)"
            class="day-item"
            :open="day.day_index === 1 || plan.days.length === 1"
          >
            <summary class="day-head">
              <span>第{{ day.day_index ?? i + 1 }}天 · {{ day.theme || "今日行程" }}</span>
              <span class="muted">{{ day.date || "" }}</span>
            </summary>

            <div class="day-body">
              <!-- 景点 -->
              <div v-if="day.spots?.length" class="block">
                <div class="block-label">📍 景点安排</div>
                <div v-for="(spot, si) in day.spots" :key="si" class="spot">
                  <div class="spot-head">
                    <span class="spot-name">{{ si + 1 }}. {{ spot.name }}</span>
                    <span v-if="spot.duration" class="ios-tag ios-tag--gray">{{ spot.duration }}</span>
                  </div>
                  <p v-if="spot.description" class="spot-desc">{{ spot.description }}</p>
                  <p v-if="fmtLocation(spot)" class="muted small">坐标:{{ fmtLocation(spot) }}</p>
                </div>
              </div>

              <!-- 餐饮 -->
              <div v-if="day.meals?.length" class="block">
                <div class="block-label">🍽️ 餐饮建议</div>
                <ul class="plain-list">
                  <li v-for="(meal, mi) in day.meals" :key="mi">
                    <span class="meal-name">{{ meal.name }}</span>
                    <span v-if="meal.notes" class="muted"> — {{ meal.notes }}</span>
                  </li>
                </ul>
              </div>

              <!-- 交通 -->
              <div v-if="fmtTransport(day.transport)" class="block">
                <div class="block-label">🚌 交通</div>
                <p class="body-text">{{ fmtTransport(day.transport) }}</p>
              </div>

              <!-- 住宿安排 -->
              <div v-if="day.hotel" class="block">
                <div class="block-label">🏨 住宿安排</div>
                <p class="body-text hotel-line">
                  <span class="hotel-name">{{ day.hotel.name }}</span>
                  <span v-if="day.hotel.level" class="ios-tag ios-tag--gray">{{ day.hotel.level }}</span>
                </p>
              </div>

              <!-- 备注 -->
              <p v-if="day.note" class="day-note">{{ day.note }}</p>
            </div>
          </details>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.result-page {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 16px;
  align-items: start;
}

/* 侧栏 */
.sidebar {
  position: sticky;
  top: 76px;
  padding: 16px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.sidebar__section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar__label {
  font-size: 12px;
  font-weight: 600;
  color: #8e8e93;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 8px;
  margin-bottom: 4px;
}

.side-btn {
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
  color: #007aff;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
}

.side-btn:hover {
  background: rgba(0, 122, 255, 0.06);
}

.side-btn:active {
  transform: scale(0.97);
}

.sidebar__divider {
  height: 0.5px;
  background: rgba(0, 0, 0, 0.06);
  margin: 12px 0;
}

.saved-box {
  background: #ecf9ee;
  border-radius: 10px;
  padding: 10px 8px;
}

.saved-title {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 600;
  color: #1a7f37;
  padding: 0 4px;
}

.saved-id {
  margin: 0 0 6px;
  font-size: 12px;
  color: #1a7f37;
  padding: 0 4px;
}

.saved-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #3f6b4c;
  padding: 0 4px;
}

/* 主内容 */
.result-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  min-width: 0;
}

.ios-card {
  padding: 20px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.overview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.overview-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1c1c1e;
  line-height: 1.4;
}

.source-chip {
  flex: none;
  font-size: 12px;
  font-weight: 600;
  color: #007aff;
  background: rgba(0, 122, 255, 0.08);
  border-radius: 999px;
  padding: 3px 10px;
  white-space: nowrap;
}

.source-chip--chat {
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.1);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 6px 18px;
  background: #f2f2f7;
  border-radius: 10px;
  padding: 10px 14px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  color: #3c3c43;
}

.info-label {
  color: #8e8e93;
  font-size: 13px;
  white-space: nowrap;
}

.chip-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.notes-line {
  margin: 12px 0 0;
  font-size: 13px;
  color: #3c3c43;
  line-height: 1.6;
}

.summary {
  margin: 14px 0 0;
  font-size: 14px;
  line-height: 1.75;
  color: #3c3c43;
}

.tips-box {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #f2f2f7;
}

.tips-title {
  font-size: 13px;
  font-weight: 600;
  color: #3c3c43;
  margin-bottom: 8px;
}

.tips-box ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #636366;
  line-height: 1.8;
}

.card-head {
  font-size: 15px;
  font-weight: 600;
  color: #1c1c1e;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.06);
}

.day-list {
  display: grid;
  gap: 8px;
}

.day-item {
  border-radius: 10px;
  border: 0.5px solid rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.day-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: #f2f2f7;
  font-size: 14px;
  font-weight: 600;
  color: #1c1c1e;
  cursor: pointer;
  list-style: none;
}

.day-head::-webkit-details-marker {
  display: none;
}

.day-head::after {
  content: "▸";
  font-size: 14px;
  color: #8e8e93;
  transition: transform 0.2s ease;
}

.day-item[open] .day-head::after {
  transform: rotate(90deg);
}

.day-body {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-top: 0.5px solid rgba(0, 0, 0, 0.06);
}

.block {
  display: grid;
  gap: 6px;
}

.block-label {
  font-size: 13px;
  font-weight: 600;
  color: #3c3c43;
}

.spot {
  border-left: 3px solid #007aff;
  background: rgba(0, 122, 255, 0.04);
  border-radius: 0 8px 8px 0;
  padding: 8px 12px;
}

.spot-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.spot-name {
  font-size: 14px;
  font-weight: 600;
  color: #1c1c1e;
}

.spot-desc {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: #48484a;
}

.plain-list {
  margin: 0;
  padding-left: 2px;
  list-style: none;
  display: grid;
  gap: 4px;
}

.meal-name {
  color: #007aff;
}

.body-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #48484a;
}

.day-note {
  margin: 0;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.03);
  font-size: 13px;
  line-height: 1.6;
  color: #48484a;
}

.muted {
  color: #8e8e93;
  font-size: 13px;
}

.small {
  font-size: 12px;
  margin: 4px 0 0;
}

/* 预算明细 */
.budget-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.budget-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 8px;
  background: #f2f2f7;
}

.budget-item b {
  font-size: 15px;
  font-weight: 600;
  color: #007aff;
}

.budget-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  background: #007aff;
  color: #ffffff;
  font-size: 14px;
}

.budget-total strong {
  font-size: 20px;
}

.old-tip {
  margin: 0;
  font-size: 13px;
  color: #8e8e93;
}

/* 按天花费 */
.day-cost-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.day-cost-cell {
  border: 0.5px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  overflow: hidden;
  background: #fbfbfd;
}

.day-cost-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f2f2f7;
  font-size: 13px;
  font-weight: 600;
  color: #1c1c1e;
}

.day-cost-body {
  display: grid;
  gap: 5px;
  padding: 8px 12px 10px;
}

.cost-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #3c3c43;
}

.cost-amt {
  color: #48484a;
  font-variant-numeric: tabular-nums;
}

.cost-row--total {
  font-weight: 700;
  border-top: 0.5px solid rgba(0, 0, 0, 0.06);
  margin-top: 3px;
  padding-top: 7px;
}

.cost-row--total .cost-amt {
  color: #007aff;
  font-size: 15px;
}

/* 天气 */
.weather-city {
  font-weight: 400;
  font-size: 13px;
  color: #8e8e93;
}

.weather-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 8px;
}

.weather-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f2f2f7;
}

.weather-item__date {
  font-size: 13px;
  font-weight: 600;
  color: #3c3c43;
}

.weather-item__temp {
  font-size: 18px;
  font-weight: 700;
  color: #007aff;
  font-variant-numeric: tabular-nums;
}

.weather-item__desc {
  font-size: 13px;
  color: #636366;
}

.weather-report {
  margin: 10px 0 0;
  font-size: 12px;
  color: #8e8e93;
}

/* 景点地图(模块7) */
.map-holder {
  height: 360px;
  width: 100%;
}

/* 地图点位明细 */
.card-sub {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 400;
  color: #8e8e93;
}

.point-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 10px;
}

.point-cell {
  display: grid;
  align-content: start;
  gap: 6px;
  border: 0.5px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 10px;
  background: #fbfbfd;
}

.point-top {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.point-day {
  font-size: 12px;
  font-weight: 700;
  color: #007aff;
}

.point-tag {
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  padding: 1px 7px;
  color: #fff;
}

.point-tag--spot {
  background: #007aff;
}

.point-tag--meal {
  background: #e8843c;
}

.point-tag--hotel {
  background: #34a853;
}

.point-name {
  font-size: 14px;
  font-weight: 600;
  color: #1c1c1e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.point-img {
  width: 100%;
  height: 110px;
  object-fit: cover;
  border-radius: 8px;
  background: #eef1f6;
}

.point-img--empty {
  display: grid;
  place-items: center;
  font-size: 12px;
  color: #b0b3bc;
  background: linear-gradient(135deg, #eef1f6, #e6e9f2);
}

.point-line {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #48484a;
  word-break: break-all;
}

.point-coord {
  color: #8e8e93;
  font-variant-numeric: tabular-nums;
}

.point-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #636366;
}

.hotel-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hotel-name {
  color: #1c1c1e;
  font-weight: 600;
}

/* 空状态 */
.empty-state {
  padding: 20px 0;
}

.empty-card {
  max-width: 480px;
  margin: 60px auto;
  text-align: center;
}

.empty-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
}

.empty-tip {
  margin: 0 0 18px;
  font-size: 13px;
  color: #8e8e93;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .result-page {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    padding: 12px;
  }

  .sidebar__section {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
  }

  .saved-box {
    flex: 1;
    min-width: 200px;
  }

  .sidebar__divider {
    display: none;
  }
}
</style>

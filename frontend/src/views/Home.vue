<script setup lang="ts">
import { computed, reactive, ref } from "vue";

import { createTrip, errMessage, isTimeoutError } from "../services/api";
import type { TripPlan, TripRequestPayload, TripRecord } from "../types";
import ChatPanel from "../components/chat-panel/ChatPanel.vue";

const emit = defineEmits<{ generated: [plan: TripPlan] }>();

// 规划模式:表单式 / 对话式,前端二选一互斥
const mode = ref<"form" | "chat">("form");

// M4 起:对话式生成完成,与表单同路跳 Result
function onChatGenerated(plan: TripPlan) {
  emit("generated", plan);
}

const preferenceOptions = ["自然风景", "拍照", "美食", "古镇", "休闲"];
const dietaryOptions = ["少辣", "不吃香菜", "不吃葱"];
const hotelLevelOptions = ["舒适型", "高档型", "经济型"];

function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const today = new Date();
const todayPlus2 = new Date(today);
todayPlus2.setDate(todayPlus2.getDate() + 2);

const form = reactive({
  destination: "大理",
  departure: "",
  startDate: formatDate(today),
  endDate: formatDate(todayPlus2),
  travelers: 2,
  budget: 3200,
  pace: "轻松",
  hotelLevel: "舒适型",
  preferences: ["自然风景", "拍照", "美食"] as string[],
  dietaryPreferences: ["少辣"] as string[],
  notes: "",
});

const isSubmitting = ref(false);
const errorMsg = ref("");

const dayCount = computed(() => {
  const s = new Date(form.startDate);
  const e = new Date(form.endDate);
  const diff = e.getTime() - s.getTime();
  return Number.isNaN(diff) ? 0 : Math.max(Math.floor(diff / 86400000) + 1, 0);
});

function toggle(list: string[], value: string) {
  const idx = list.indexOf(value);
  if (idx >= 0) list.splice(idx, 1);
  else list.push(value);
}

/** createTrip 返回 TripRecord;planJson 是完整 TripPlan JSON,解析后回填真实 id/source */
function toPlan(record: TripRecord): TripPlan {
  const plan = JSON.parse(record.planJson || "{}") as TripPlan;
  plan.id = record.id;
  if (record.source && !plan.source) plan.source = record.source;
  return plan;
}

async function submit() {
  if (isSubmitting.value) return;
  errorMsg.value = "";
  if (!form.departure.trim()) {
    errorMsg.value = "请填写出发城市(从哪个城市出发)";
    return;
  }
  if (!form.destination.trim()) {
    errorMsg.value = "请填写目的地城市";
    return;
  }
  const payload: TripRequestPayload = {
    title: null,
    destination: form.destination.trim(),
    departure: form.departure.trim(),
    start_date: form.startDate,
    end_date: form.endDate,
    travelers: form.travelers,
    budget: form.budget,
    preferences: form.preferences,
    pace: form.pace,
    hotel_level: form.hotelLevel,
    dietary_preferences: form.dietaryPreferences,
    special_notes: form.notes.trim() || null,
  };

  isSubmitting.value = true;
  try {
    const record = await createTrip(payload);
    emit("generated", toPlan(record));
  } catch (e) {
    if (isTimeoutError(e)) {
      errorMsg.value =
        "等待超过 8 分钟,大概率已超时失败。若「历史」里没有该行程,可稍后重试(条件完全一致会命中缓存、立即返回);仍失败请把目的地/天数缩小或拆分。";
    } else {
      errorMsg.value = errMessage(e, "行程生成失败,请确认 ai-service(8100)与后端(8080)都在运行");
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <section class="page-stack">
    <!-- 模式切换:表单式 / 对话式(前端二选一互斥) -->
    <div class="ios-card mode-card">
      <div class="segmented">
        <button
          :class="['seg-btn', { 'seg-btn--active': mode === 'form' }]"
          type="button"
          @click="mode = 'form'"
        >
          表单式
        </button>
        <button
          :class="['seg-btn', { 'seg-btn--active': mode === 'chat' }]"
          type="button"
          @click="mode = 'chat'"
        >
          对话式
        </button>
      </div>
      <p class="mode-hint">
        {{ mode === 'form' ? '填写表单后由 AI 生成完整行程' : '和 AI 边聊边安排,聊完点「确认行程」生成' }}
      </p>
    </div>

    <template v-if="mode === 'form'">
    <!-- 目的地与日期 -->
    <div class="ios-card">
      <div class="ios-card__header">
        <span class="ios-card__icon">📍</span>
        <span class="ios-card__title">目的地与日期</span>
      </div>

      <label class="ios-label">出发城市</label>
      <input v-model.trim="form.departure" class="ios-input" placeholder="请输入出发城市(如:北京)" />

      <div style="margin-top: 12px"></div>
      <label class="ios-label">目的地城市</label>
      <input v-model.trim="form.destination" class="ios-input" placeholder="请输入目的地" />

      <div class="grid-3">
        <div>
          <label class="ios-label">开始日期</label>
          <input v-model="form.startDate" type="date" class="ios-input" />
        </div>
        <div>
          <label class="ios-label">结束日期</label>
          <input v-model="form.endDate" type="date" class="ios-input" />
        </div>
        <div>
          <label class="ios-label">出行人数</label>
          <input v-model.number="form.travelers" type="number" class="ios-input" min="1" />
        </div>
      </div>

      <div class="day-row">
        <span class="day-label">旅行天数</span>
        <span class="ios-badge">{{ dayCount }} 天</span>
      </div>
    </div>

    <!-- 偏好设置 -->
    <div class="ios-card">
      <div class="ios-card__header">
        <span class="ios-card__icon">⚙️</span>
        <span class="ios-card__title">偏好设置</span>
      </div>

      <div class="grid-3">
        <div>
          <label class="ios-label">节奏偏好</label>
          <select v-model="form.pace" class="ios-select">
            <option value="轻松">轻松</option>
            <option value="适中">适中</option>
            <option value="紧凑">紧凑</option>
          </select>
        </div>
        <div>
          <label class="ios-label">住宿档次</label>
          <select v-model="form.hotelLevel" class="ios-select">
            <option v-for="lv in hotelLevelOptions" :key="lv" :value="lv">{{ lv }}</option>
          </select>
        </div>
        <div>
          <label class="ios-label">预算(元)</label>
          <input v-model.number="form.budget" type="number" class="ios-input" min="0" />
        </div>
      </div>

      <p class="budget-note">预算为含往返大交通的总预算;第 1 天会安排从出发城市前往目的地的交通。</p>

      <div style="margin-top: 16px">
        <label class="ios-label">旅行偏好</label>
        <div class="ios-chips">
          <button
            v-for="opt in preferenceOptions"
            :key="opt"
            :class="['ios-chip', { 'ios-chip--active': form.preferences.includes(opt) }]"
            type="button"
            @click="toggle(form.preferences, opt)"
          >
            {{ opt }}
          </button>
        </div>
      </div>

      <div style="margin-top: 16px">
        <label class="ios-label">饮食偏好</label>
        <div class="ios-chips">
          <button
            v-for="opt in dietaryOptions"
            :key="opt"
            :class="['ios-chip', { 'ios-chip--active': form.dietaryPreferences.includes(opt) }]"
            type="button"
            @click="toggle(form.dietaryPreferences, opt)"
          >
            {{ opt }}
          </button>
        </div>
      </div>
    </div>

    <!-- 额外要求 -->
    <div class="ios-card">
      <div class="ios-card__header">
        <span class="ios-card__icon">💬</span>
        <span class="ios-card__title">额外要求</span>
      </div>
      <textarea
        v-model="form.notes"
        class="ios-textarea"
        rows="3"
        placeholder="输入想保留的偏好与备注,如:想看日落"
      />
    </div>

    <p v-if="errorMsg" class="home-error">{{ errorMsg }}</p>

    <div class="submit-area">
      <button class="ios-button ios-button--primary" :disabled="isSubmitting" @click="submit">
        {{ isSubmitting ? "AI 生成中(通常 1~3 分钟,首次较慢)…" : "开始规划" }}
      </button>
      <p class="submit-hint">提交后由 AI 实时生成,可在结果页查看每日安排</p>
    </div>
    </template>

    <ChatPanel v-else @generated="onChatGenerated" />
  </section>
</template>

<style scoped>
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.day-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 0.5px solid rgba(0, 0, 0, 0.06);
}

.day-label {
  font-size: 13px;
  color: #8e8e93;
}

.budget-note {
  margin: 8px 0 0;
  font-size: 12px;
  color: #8e8e93;
  line-height: 1.6;
}

.home-error {
  margin: 0;
  font-size: 13px;
  color: #d70015;
  text-align: center;
}

.submit-area {
  text-align: center;
  padding: 8px 0;
}

.submit-hint {
  margin-top: 10px;
  font-size: 13px;
  color: #8e8e93;
}

.mode-card {
  padding: 12px 16px 14px;
}

.segmented {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.04);
}

.seg-btn {
  flex: 1;
  border: none;
  padding: 8px 0;
  border-radius: 8px;
  background: transparent;
  color: #8e8e93;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.seg-btn--active {
  background: #ffffff;
  color: #1c1c1e;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.mode-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: #8e8e93;
  text-align: center;
}

@media (max-width: 768px) {
  .grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>

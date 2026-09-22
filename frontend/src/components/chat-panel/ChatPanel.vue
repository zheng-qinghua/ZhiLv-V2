<script setup lang="ts">
import { computed, nextTick, ref } from "vue";

import { createChatSession, errMessage, sendChatMessage } from "../../services/api";
import type { ChatTurnResponse, TripPlan, TripRecord } from "../../types";

// M4 接通用:对话生成完成后携带 TripPlan 通知父级跳 Result
const emit = defineEmits<{ generated: [plan: TripPlan] }>();

// 确认生成返回 TripRecord,planJson 是完整 TripPlan,解析后回填真实 id/source(与表单同路)
function toPlan(record: TripRecord): TripPlan {
  const plan = JSON.parse(record.planJson || "{}") as TripPlan;
  plan.id = record.id;
  if (record.source && !plan.source) plan.source = record.source;
  return plan;
}

interface ChatMsg {
  role: "user" | "ai";
  content: string;
}

const messages = ref<ChatMsg[]>([]);
const input = ref("");
const sending = ref(false);
const scrollEl = ref<HTMLElement | null>(null);
const sessionId = ref<number | null>(null);

/** 已了解行程信息条:每轮按后端返回的 params 实时刷新。
 * 说过的字段显示用户给的值(isDefault=false);没说的才标记为默认(isDefault=true)。
 * 预算尤其注意:用户给过就显示给的值(哪怕只给人均也如实显示),没给才显示"将自动估算"。 */
interface ParamItem {
  label: string;
  value: string;
  isDefault?: boolean;
}

function defaultItems(): ParamItem[] {
  return [
    { label: "出发地", value: "待说明" },
    { label: "目的地", value: "待说明" },
    { label: "出行时间", value: "待说明" },
    { label: "人数", value: "3 人", isDefault: true },
    { label: "预算", value: "将自动估算(含往返大交通)", isDefault: true },
  ];
}

const paramItems = ref<ParamItem[]>(defaultItems());

function fmtMoney(n: number): string {
  return "¥" + n.toLocaleString("zh-CN");
}

/** 把后端本轮 params(只含用户明说过的)映射到参数条芯片;null/未给字段保持默认位。 */
function applyParams(p: Record<string, unknown> | null | undefined) {
  lastParams.value = p ?? null;
  const items = defaultItems();
  if (!p) {
    paramItems.value = items;
    return;
  }
  const dep = p.departure;
  if (typeof dep === "string" && dep) {
    items[0] = { label: "出发地", value: dep };
  }
  const dest = p.destination;
  if (typeof dest === "string" && dest) {
    items[1] = { label: "目的地", value: dest };
  }
  const s = p.start_date;
  const e = p.end_date;
  const days = p.total_days;
  if (typeof s === "string" && s && typeof e === "string" && e) {
    items[2] = { label: "出行时间", value: `${s} ~ ${e}` };
  } else if (typeof days === "number" && days > 0) {
    items[2] = { label: "出行时间", value: `${days} 天` };
  }
  const tr = p.travelers;
  if (typeof tr === "number" && tr > 0) {
    items[3] = { label: "人数", value: `${tr} 人` };
  }
  const b = p.budget;
  if (typeof b === "number" && b > 0) {
    const unit = p.budget_unit === "per_person" ? "/人" : "";
    items[4] = { label: "预算", value: fmtMoney(b) + unit };
  }
  paramItems.value = items;
}

/** 同步预算拦截状态:后端 ready=false(预算低于路线最低花费)时,按钮下方给醒目提示 */
function applyBudgetFlag(t: ChatTurnResponse) {
  lowBudget.value = !!t.lowBudget;
  minBudget.value = typeof t.minBudget === "number" ? t.minBudget : null;
}

// M4:对话式生成闭环 —— 参数条没到 ready 时按钮禁用;ready(出发地+目的地+时间齐)才可点
const confirmReady = ref(false); // 最近一轮后端是否判定可确认
const generating = ref(false); // 点「确认行程」后正在生成
const generatedDone = ref(false); // 已成功生成过一条,防止重复点确认
const lastParams = ref<Record<string, unknown> | null>(null); // 最近一轮后端参数(日期提示用)
const lowBudget = ref(false); // 预算低于路线最低花费:确认被按灰,提示加预算/接受压缩
const minBudget = ref<number | null>(null); // ai-service 给的预估最低总额(含往返大交通)
const confirmEnabled = computed(
  () => confirmReady.value && !sending.value && !generating.value && !generatedDone.value
);
const confirmLabel = computed(() => {
  if (generating.value) return "AI 生成中(通常 1~3 分钟)…";
  if (generatedDone.value) return "已生成";
  return "确认行程";
});

/** 只说了大概天数、没给具体起止日期时,提示生成会默认从今天起(口径透明,不靠猜) */
const dateNotice = computed(() => {
  const p = lastParams.value;
  if (!p) return "";
  const s = p.start_date;
  const e = p.end_date;
  const hasExact =
    typeof s === "string" && !!s && typeof e === "string" && !!e;
  if (hasExact) return "";
  const d = p.total_days;
  if (typeof d === "number" && d > 0) {
    return `你只说了大概天数,没给具体起止日期:将默认从今天起生成 ${d} 天行程。想固定日期就把「几月几号到几号」补清楚再点确认。`;
  }
  return "";
});

function scrollToBottom() {
  nextTick(() => {
    const el = scrollEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

function startNewConversation() {
  messages.value = [
    {
      role: "ai",
      content:
        "你好，我是你的行程规划助手。想去哪里玩、大概什么时间、几个人、预算多少，直接告诉我即可；我会边聊边整理，聊得差不多时点下方「确认行程」就能生成完整行程。",
    },
  ];
  input.value = "";
  sessionId.value = null;
  paramItems.value = defaultItems();
  confirmReady.value = false;
  generating.value = false;
  generatedDone.value = false;
  lastParams.value = null;
  lowBudget.value = false;
  minBudget.value = null;
  scrollToBottom();
}

async function onSend() {
  const text = input.value.trim();
  if (!text || sending.value) return;
  messages.value.push({ role: "user", content: text });
  input.value = "";
  sending.value = true;
  confirmReady.value = false; // 这轮还没回来前,先收掉"可确认"态
  generatedDone.value = false; // 用户继续补充/改口径,视为想重新规划
  lowBudget.value = false; // 预算拦截状态等这轮服务端返回再刷新
  scrollToBottom(); // 立即滚到底,让"正在准备回复"加载气泡可见
  try {
    if (!sessionId.value) {
      const created = await createChatSession();
      sessionId.value = created.id;
    }
    const turn = await sendChatMessage(sessionId.value, text, "chat");
    if (turn.reply) messages.value.push({ role: "ai", content: turn.reply });
    applyParams(turn.params);
    confirmReady.value = !!turn.ready;
    applyBudgetFlag(turn);
  } catch (e) {
    messages.value.push({ role: "ai", content: "出错了：" + errMessage(e, "对话服务不可用,请确认 ai-service(8100)与后端(8080)都在运行") });
  } finally {
    sending.value = false;
    scrollToBottom();
  }
}

/** 点「确认行程」:让 ai-service 按对话参数生成完整行程,后端落库成 CHAT 行程后跳 Result */
async function onConfirm() {
  if (!sessionId.value || !confirmEnabled.value) return;
  generatedDone.value = false;
  generating.value = true;
  scrollToBottom();
  try {
    const turn = await sendChatMessage(sessionId.value, "", "confirm");
    if (turn.status === "generated" && turn.trip) {
      generatedDone.value = true; // 防止 KeepAlive 切回后误重复点确认
      lowBudget.value = false;
      emit("generated", toPlan(turn.trip)); // 父级切到 Result 展示
      return;
    }
    // 没成功生成(如预算不足/生成失败):展示原因并保持继续聊
    if (turn.reply) messages.value.push({ role: "ai", content: turn.reply });
    applyParams(turn.params);
    confirmReady.value = !!turn.ready;
    applyBudgetFlag(turn);
  } catch (e) {
    messages.value.push({
      role: "ai",
      content:
        "生成出错：" +
        errMessage(e, "行程生成失败,请稍后重试(跨城市/天数太多时可能较久或超时)"),
    });
  } finally {
    generating.value = false;
    scrollToBottom();
  }
}

/** 加载气泡文案:确认生成那轮耗时以分钟计,文案要说明清楚 */
const loadingText = computed(() =>
  generating.value ? "正在按对话整理生成完整行程,通常 1~3 分钟…" : "正在准备回复…"
);

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    void onSend();
  }
}

startNewConversation();
</script>

<template>
  <section class="page-stack chat-panel">
    <!-- 已了解信息条:随对话实时更新 -->
    <div class="ios-card param-card">
      <div class="param-card__head">
        <span class="param-card__title">已了解行程信息</span>
        <span class="param-card__hint">说过的以你为准,没说的才按默认</span>
      </div>
      <div class="param-chips">
        <span v-for="(p, i) in paramItems" :key="i" class="param-chip">
          <span class="param-chip__label">{{ p.label }}</span>
          <span class="param-chip__value">{{ p.value }}</span>
          <span v-if="p.isDefault" class="param-chip__tag">默认</span>
        </span>
      </div>
    </div>

    <!-- 对话消息区 -->
    <div class="ios-card chat-card">
      <div class="chat-card__head">
        <span class="chat-card__title">对话式规划</span>
        <button class="chat-reset" @click="startNewConversation">新对话</button>
      </div>
      <div ref="scrollEl" class="chat-scroll">
        <div
          v-for="(m, i) in messages"
          :key="i"
          :class="['msg-row', m.role === 'user' ? 'msg-row--user' : 'msg-row--ai']"
        >
          <div :class="['msg-bubble', m.role === 'user' ? 'msg-bubble--user' : 'msg-bubble--ai']">
            {{ m.content }}
          </div>
        </div>
        <!-- 等待 Agent 回复/生成行程中的加载气泡 -->
        <div v-if="sending || generating" class="msg-row msg-row--ai">
          <div class="msg-bubble msg-bubble--ai typing-bubble">
            <span class="typing-ring" aria-hidden="true"></span>
            <span class="typing-text">{{ loadingText }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 确认行程 -->
    <div class="confirm-area">
      <button class="ios-button ios-button--primary confirm-btn" :disabled="!confirmEnabled" @click="onConfirm">
        {{ confirmLabel }}
      </button>
      <p v-if="dateNotice && !generatedDone" class="confirm-notice">{{ dateNotice }}</p>
      <p v-if="lowBudget && !generatedDone" class="confirm-notice confirm-notice--warn">
        预算提示:你给的预算低于这趟路线的预估最低花费(约 {{ fmtMoney(minBudget ?? 0) }},含往返大交通、按最省方式估),「确认行程」已暂不可点。把预算加到 {{ fmtMoney(minBudget ?? 0) }} 以上,或回复「就按最省的吧」让我按最省方式压缩排期。
      </p>
      <p v-if="generatedDone" class="confirm-done">✅ 行程已生成并打开结果页。想再规划一轮就点上方「新对话」；也能去导航栏「历史」查看。</p>
      <p class="confirm-hint">
        把「从哪出发 + 去哪里 + 大概什么时间去」说清就能点。人数/节奏/住宿没说的用默认(3 人、节奏适中、舒适型)；预算你没给就按 每人每天约 200 当地花费 + 800 往返大交通 粗略估算,给过就一定按你的算。预算口径默认含往返大交通。
      </p>
    </div>

    <!-- 输入区 -->
    <div class="ios-card input-card">
      <div class="input-row">
        <input
          v-model="input"
          class="ios-input chat-input"
          placeholder="说点什么，比如：从北京出发,带爸妈去大理玩 5 天"
          @keydown="onKeydown"
        />
        <button class="ios-button ios-button--secondary send-btn" :disabled="sending" @click="onSend">
          {{ sending ? "…" : "发送" }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.param-card {
  padding: 14px 16px;
}

.param-card__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.param-card__title {
  font-size: 13px;
  font-weight: 600;
  color: #1c1c1e;
}

.param-card__hint {
  font-size: 12px;
  color: #8e8e93;
}

.param-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.param-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #48484a;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 14px;
  padding: 4px 12px;
}

.param-chip__label {
  color: #8e8e93;
}

.param-chip__value {
  color: #1c1c1e;
  font-weight: 500;
}

.param-chip__tag {
  font-size: 11px;
  color: #b25000;
  background: rgba(255, 149, 0, 0.14);
  border-radius: 8px;
  padding: 1px 6px;
}

.chat-card {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
}

.chat-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.chat-card__title {
  font-size: 15px;
  font-weight: 600;
  color: #1c1c1e;
}

.chat-reset {
  border: none;
  background: none;
  color: #007aff;
  font-size: 13px;
  cursor: pointer;
}

.chat-scroll {
  height: 46vh;
  min-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 2px 8px;
}

.msg-row {
  display: flex;
}

.msg-row--user {
  justify-content: flex-end;
}

.msg-row--ai {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-bubble--user {
  background: #007aff;
  color: #ffffff;
  border-bottom-right-radius: 6px;
}

.msg-bubble--ai {
  background: #f2f2f7;
  color: #1c1c1e;
  border-bottom-left-radius: 6px;
}

/* 等待 Agent 回复:圈式加载 + 文案 */
.typing-bubble {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
}

.typing-ring {
  flex: none;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(0, 122, 255, 0.18);
  border-top-color: #007aff;
  animation: typing-spin 0.8s linear infinite;
}

.typing-text {
  font-size: 13px;
  color: #8e8e93;
}

@keyframes typing-spin {
  to {
    transform: rotate(360deg);
  }
}

.confirm-area {
  text-align: center;
}

.confirm-btn {
  width: 100%;
  max-width: 360px;
}

.confirm-hint {
  margin: 8px auto 0;
  max-width: 480px;
  font-size: 12px;
  color: #8e8e93;
}

.confirm-notice {
  margin: 8px auto 0;
  max-width: 480px;
  font-size: 12px;
  line-height: 1.6;
  color: #b25000;
}

.confirm-done {
  margin: 8px auto 0;
  max-width: 480px;
  font-size: 13px;
  line-height: 1.6;
  color: #1a7f37;
}

.input-card {
  padding: 12px 16px;
}

.input-row {
  display: flex;
  gap: 10px;
}

.chat-input {
  flex: 1;
}

.send-btn {
  flex: none;
  padding: 0 22px;
  height: 36px;
  font-size: 15px;
}
</style>

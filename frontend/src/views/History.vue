<script setup lang="ts">
import { onActivated, ref } from "vue";

import { deleteTrip, errMessage, exportTrip, listTrips } from "../services/api";
import type { Page, TripPlan, TripRecord } from "../types";

const emit = defineEmits<{ open: [plan: TripPlan] }>();

const pageData = ref<Page<TripRecord> | null>(null);
const page = ref(0);
const size = 10;
const loading = ref(false);
const errorMsg = ref("");

async function load() {
  loading.value = true;
  errorMsg.value = "";
  try {
    pageData.value = await listTrips(page.value, size);
  } catch (e) {
    errorMsg.value = errMessage(e, "加载历史失败");
  } finally {
    loading.value = false;
  }
}

async function viewTrip(id: number) {
  try {
    emit("open", await exportTrip(id));
  } catch (e) {
    window.alert("加载行程详情失败:" + errMessage(e, "未知错误"));
  }
}

async function remove(id: number) {
  if (!window.confirm("确认删除这条行程?")) return;
  try {
    await deleteTrip(id);
    const cur = pageData.value;
    // 删空本页最后一条则往前翻一页
    if (cur && cur.content.length === 1 && page.value > 0) page.value -= 1;
    load();
  } catch (e) {
    window.alert("删除失败:" + errMessage(e, "未知错误"));
  }
}

function go(delta: number) {
  if (!pageData.value) return;
  const next = page.value + delta;
  if (next < 0 || next >= pageData.value.totalPages) return;
  page.value = next;
  load();
}

// 组件在 KeepAlive 内:每次切回历史页都会重新激活并刷新列表
onActivated(load);
</script>

<template>
  <section class="page-stack">
    <div v-if="loading" class="list-hint">加载中…</div>
    <p v-else-if="errorMsg" class="list-error">{{ errorMsg }}</p>

    <template v-else>
      <p v-if="!pageData || pageData.empty" class="list-hint">
        还没有行程记录,先去「规划」生成一条吧。
      </p>

      <div v-for="t in pageData?.content ?? []" :key="t.id" class="ios-card hist-card">
        <div class="hist-top">
          <div>
            <span class="hist-title">{{ t.title }}</span>
            <span :class="['ios-tag', t.source === 'CHAT' ? 'hist-chat' : '']">{{ t.source }}</span>
          </div>
          <button class="link-btn" @click="viewTrip(t.id)">查看详情</button>
        </div>
        <p class="hist-meta">
          {{ t.destination }} · {{ t.startDate }} ~ {{ t.endDate }} · {{ t.dayCount }}天 ·
          {{ t.travelers }}人 · 预算 ¥{{ Number(t.budget).toLocaleString() }}
        </p>
        <div class="hist-ops">
          <button class="danger-btn" @click="remove(t.id)">删除</button>
        </div>
      </div>

      <div v-if="pageData && pageData.totalPages > 1" class="pager">
        <button class="page-btn" :disabled="pageData.first" @click="go(-1)">上一页</button>
        <span class="page-info">{{ pageData.number + 1 }} / {{ pageData.totalPages }} · 共 {{ pageData.totalElements }} 条</span>
        <button class="page-btn" :disabled="pageData.last" @click="go(1)">下一页</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.list-hint {
  text-align: center;
  color: #8e8e93;
  padding: 40px 0;
  font-size: 14px;
}

.list-error {
  text-align: center;
  color: #d70015;
  font-size: 14px;
}

.hist-card {
  padding: 14px 16px;
}

.hist-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.hist-title {
  font-size: 15px;
  font-weight: 600;
  margin-right: 8px;
}

.hist-chat {
  background: rgba(124, 58, 237, 0.1);
  color: #7c3aed;
}

.hist-meta {
  margin: 6px 0 0;
  font-size: 13px;
  color: #8e8e93;
}

.hist-ops {
  margin-top: 10px;
  text-align: right;
}

.link-btn {
  border: none;
  background: none;
  color: #007aff;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 0;
}

.danger-btn {
  border: 1px solid #ffd1d6;
  background: #ffffff;
  color: #d70015;
  font-size: 13px;
  border-radius: 8px;
  padding: 5px 14px;
  cursor: pointer;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 10px 0;
}

.page-btn {
  border: 1px solid #d1d1d6;
  background: #ffffff;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 13px;
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #8e8e93;
}
</style>

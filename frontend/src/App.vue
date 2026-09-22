<script setup lang="ts">
import { ref } from "vue";

import { logout, TOKEN_KEY, USER_KEY } from "./services/api";
import type { TripPlan } from "./types";
import History from "./views/History.vue";
import Home from "./views/Home.vue";
import Login from "./views/Login.vue";
import Result from "./views/Result.vue";

const authed = ref(!!localStorage.getItem(TOKEN_KEY));
const username = ref(localStorage.getItem(USER_KEY) || "");
const currentView = ref<"home" | "result" | "history">("home");
const latestPlan = ref<TripPlan | null>(null);

function onAuthed(name: string) {
  username.value = name;
  authed.value = true;
  currentView.value = "home";
}

function onGenerated(plan: TripPlan) {
  latestPlan.value = plan;
  currentView.value = "result";
}

function onOpenTrip(plan: TripPlan) {
  latestPlan.value = plan;
  currentView.value = "result";
}

async function doLogout() {
  await logout();
  authed.value = false;
  latestPlan.value = null;
  currentView.value = "home";
}
</script>

<template>
  <Login v-if="!authed" @authed="onAuthed" />

  <div v-else class="app-shell">
    <header class="nav-bar">
      <div class="nav-bar__inner">
        <span class="nav-bar__title">智旅云图</span>
        <div class="nav-bar__tabs">
          <button
            :class="['nav-tab', { 'nav-tab--active': currentView === 'home' }]"
            @click="currentView = 'home'"
          >
            规划
          </button>
          <button
            :class="['nav-tab', { 'nav-tab--active': currentView === 'result' }, { 'nav-tab--disabled': !latestPlan }]"
            :disabled="!latestPlan"
            @click="currentView = 'result'"
          >
            结果
          </button>
          <button
            :class="['nav-tab', { 'nav-tab--active': currentView === 'history' }]"
            @click="currentView = 'history'"
          >
            历史
          </button>
        </div>
        <div class="nav-bar__user">
          <span class="nav-user">{{ username }}</span>
          <button class="nav-logout" @click="doLogout">退出</button>
        </div>
      </div>
    </header>

    <main class="page-content">
      <!-- KeepAlive:切换 tab 不销毁组件,规划页生成中的 loading/请求得以保留 -->
      <KeepAlive>
        <Home v-if="currentView === 'home'" @generated="onGenerated" />
        <Result
          v-else-if="currentView === 'result'"
          :plan="latestPlan"
          @back-home="currentView = 'home'"
          @view-history="currentView = 'history'"
        />
        <History v-else @open="onOpenTrip" />
      </KeepAlive>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding-top: 56px;
}

.nav-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.1);
}

.nav-bar__inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 56px;
  gap: 16px;
}

.nav-bar__title {
  font-size: 17px;
  font-weight: 600;
  color: #1c1c1e;
  white-space: nowrap;
}

.nav-bar__tabs {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.04);
}

.nav-tab {
  border: none;
  border-radius: 8px;
  padding: 6px 16px;
  background: transparent;
  color: #8e8e93;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-tab:active {
  transform: scale(0.97);
}

.nav-tab--active {
  background: #ffffff;
  color: #1c1c1e;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.nav-tab--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.nav-bar__user {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.nav-user {
  font-size: 13px;
  color: #48484a;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-logout {
  border: none;
  border-radius: 8px;
  padding: 5px 12px;
  background: rgba(0, 0, 0, 0.05);
  color: #48484a;
  font-size: 13px;
  cursor: pointer;
}

.nav-logout:hover {
  background: rgba(0, 0, 0, 0.1);
}

.page-content {
  max-width: 1080px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}

@media (max-width: 768px) {
  .app-shell {
    padding-top: 104px;
  }

  .nav-bar__inner {
    height: auto;
    flex-wrap: wrap;
    padding: 8px 16px;
    gap: 8px;
  }

  .page-content {
    padding: 16px 16px 32px;
  }
}
</style>

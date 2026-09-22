<script setup lang="ts">
import { reactive, ref } from "vue";

import { errMessage, login as apiLogin, register as apiRegister, TOKEN_KEY, USER_KEY } from "../services/api";

const emit = defineEmits<{ authed: [username: string] }>();

const mode = ref<"login" | "register">("login");
const form = reactive({ username: "", password: "" });
const busy = ref(false);
const errorMsg = ref("");

async function submit() {
  errorMsg.value = "";
  const { username, password } = form;
  if (!username.trim() || !password) {
    errorMsg.value = "用户名和密码不能为空";
    return;
  }
  busy.value = true;
  try {
    if (mode.value === "register") {
      await apiRegister(username.trim(), password);
    }
    const res = await apiLogin(username.trim(), password);
    localStorage.setItem(TOKEN_KEY, res.token);
    localStorage.setItem(USER_KEY, res.username);
    emit("authed", res.username);
  } catch (e) {
    errorMsg.value = errMessage(e, mode.value === "register" ? "注册失败" : "登录失败");
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card ios-card">
      <div class="login-brand">
        <div class="login-logo">✈️</div>
        <h1>智旅云图</h1>
        <p>智能旅行行程助手</p>
      </div>

      <div class="login-mode">
        <button
          :class="['mode-btn', { 'mode-btn--active': mode === 'login' }]"
          @click="mode = 'login'; errorMsg = ''"
        >
          登录
        </button>
        <button
          :class="['mode-btn', { 'mode-btn--active': mode === 'register' }]"
          @click="mode = 'register'; errorMsg = ''"
        >
          注册
        </button>
      </div>

      <form @submit.prevent="submit">
        <div class="field">
          <label class="ios-label">用户名</label>
          <input v-model.trim="form.username" class="ios-input" autocomplete="username" placeholder="请输入用户名" />
        </div>
        <div class="field">
          <label class="ios-label">密码</label>
          <input v-model="form.password" type="password" class="ios-input" autocomplete="current-password" placeholder="请输入密码" />
        </div>

        <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>

        <button type="submit" class="ios-button ios-button--primary login-submit" :disabled="busy">
          {{ busy ? "请稍候…" : mode === "login" ? "登录" : "注册并登录" }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 380px;
}

.login-brand {
  text-align: center;
  margin-bottom: 20px;
}

.login-logo {
  font-size: 42px;
}

.login-brand h1 {
  margin: 8px 0 2px;
  font-size: 22px;
  font-weight: 700;
}

.login-brand p {
  margin: 0;
  font-size: 13px;
  color: #8e8e93;
}

.login-mode {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}

.mode-btn {
  flex: 1;
  border: none;
  border-radius: 8px;
  padding: 7px 0;
  background: transparent;
  color: #8e8e93;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.mode-btn--active {
  background: #ffffff;
  color: #1c1c1e;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.field {
  margin-bottom: 12px;
}

.login-submit {
  width: 100%;
  margin-top: 8px;
}

.login-error {
  margin: 8px 0 0;
  font-size: 13px;
  color: #d70015;
}
</style>

<script setup>
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { login, session, setBaseUrl } from "../services/api";

const router = useRouter();
const form = reactive({ username: "admin", password: "admin123" });
const status = reactive({ text: "未登录" });

async function onLogin() {
  try {
    setBaseUrl(session.baseUrl);
    const data = await login(form.username, form.password);
    status.text = `登录成功：${data.user.username}`;
    router.push("/store");
  } catch (err) {
    status.text = String(err);
  }
}
</script>

<template>
  <div class="bg"></div>
  <section class="auth-wrap">
    <div class="auth-card">
      <h1>aivuda AppStore</h1>
      <p>Developer Console</p>

      <form class="stack" @submit.prevent="onLogin">
        <label>
          Backend URL
          <input v-model.trim="session.baseUrl" placeholder="http://127.0.0.1:9001" />
        </label>
        <label>
          用户名
          <input v-model="form.username" required />
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" required />
        </label>
        <button>登录</button>
      </form>

      <div class="hint">{{ status.text }}</div>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useAuth } from "../composables/useAuth";

const router = useRouter();
const { session, form, status, loginWithForm } = useAuth();

async function onLogin() {
  await loginWithForm({
    onSuccess() {
      router.push("/store");
    },
  });
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

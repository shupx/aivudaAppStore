<script setup>
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuth } from "../composables/useAuth";

const router = useRouter();
const { t } = useI18n();
const { session, form, status, loginWithForm } = useAuth(t);

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
      <p>{{ t("login.console") }}</p>

      <form class="stack" @submit.prevent="onLogin">
        <label>
          {{ t("login.backendUrl") }}
          <input v-model.trim="session.baseUrl" :placeholder="t('login.backendUrlPlaceholder')" />
        </label>
        <label>
          {{ t("login.username") }}
          <input v-model="form.username" required />
        </label>
        <label>
          {{ t("login.password") }}
          <input v-model="form.password" type="password" required />
        </label>
        <button>{{ t("login.submit") }}</button>
      </form>

      <div class="hint">{{ status.text }}</div>
    </div>
  </section>
</template>

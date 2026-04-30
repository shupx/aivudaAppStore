<script setup>
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuth } from "../composables/useAuth";
import { Loader2 } from "lucide-vue-next";

const router = useRouter();
const { t } = useI18n();
const { form, status, loginWithForm } = useAuth(t);

async function onLogin() {
  await loginWithForm({
    onSuccess() {
      router.push("/store");
    },
  });
}
</script>

<template>
  <div class="bg-grid"></div>
  <section class="min-h-screen grid place-items-center p-5">
    <div class="w-[min(460px,95vw)] bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 rounded-3xl p-8 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 relative z-10">
      <div class="mb-8">
        <h1 class="text-3xl font-extrabold tracking-tight text-zinc-900 dark:text-zinc-100 m-0">aivuda AppStore</h1>
        <p class="text-zinc-500 dark:text-zinc-400 mt-2 m-0">{{ t("login.console") }}</p>
      </div>

      <form class="flex flex-col gap-5" @submit.prevent="onLogin">
        <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {{ t("login.username") }}
          <input 
            v-model="form.username" 
            required 
            class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all shadow-sm"
          />
        </label>
        <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {{ t("login.password") }}
          <input 
            v-model="form.password" 
            type="password" 
            required 
            class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all shadow-sm"
          />
        </label>
        <button 
          type="submit"
          :disabled="status.loading"
          class="mt-2 w-full flex justify-center items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold py-3 px-4 rounded-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed shadow-md shadow-emerald-500/20"
        >
          <Loader2 v-if="status.loading" class="w-5 h-5 animate-spin" />
          {{ t("login.submit") }}
        </button>
      </form>

      <div v-if="status.text" class="mt-4 text-center text-sm font-medium" :class="status.type === 'error' ? 'text-red-500 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'">
        {{ status.text }}
      </div>
    </div>
  </section>
</template>

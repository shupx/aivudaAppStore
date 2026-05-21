<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppTopBar from "../components/AppTopBar.vue";
import { changePassword, fetchMe, fetchUsers, resetUserPassword, session } from "../services/api";
import { KeyRound, Loader2, ShieldUser, UserRound } from "lucide-vue-next";

const router = useRouter();
const { t } = useI18n();

const selfForm = reactive({
  currentPassword: "",
  newPassword: "",
});
const resetForm = reactive({
  userId: "",
  newPassword: "",
});

const users = ref([]);
const loadingUsers = ref(false);
const savingSelf = ref(false);
const savingReset = ref(false);
const selfMessage = ref("");
const resetMessage = ref("");

const isAdmin = computed(() => session.user?.role === "admin");

async function load() {
  try {
    await fetchMe();
    if (isAdmin.value) {
      loadingUsers.value = true;
      const data = await fetchUsers();
      users.value = data.users || [];
    }
  } catch {
    router.push("/login");
  } finally {
    loadingUsers.value = false;
  }
}

async function submitSelfPassword() {
  savingSelf.value = true;
  selfMessage.value = "";
  try {
    await changePassword(selfForm.currentPassword, selfForm.newPassword);
    selfMessage.value = t("account.changePasswordSuccess");
    selfForm.currentPassword = "";
    selfForm.newPassword = "";
  } catch (err) {
    selfMessage.value = String(err);
  } finally {
    savingSelf.value = false;
  }
}

async function submitResetPassword() {
  if (!resetForm.userId) return;
  savingReset.value = true;
  resetMessage.value = "";
  try {
    await resetUserPassword(Number(resetForm.userId), resetForm.newPassword);
    resetMessage.value = t("account.resetPasswordSuccess");
    resetForm.newPassword = "";
  } catch (err) {
    resetMessage.value = String(err);
  } finally {
    savingReset.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="bg-grid"></div>
  <section class="w-[min(1100px,96vw)] mx-auto my-6 flex flex-col gap-6">
    <AppTopBar :title="t('account.title')" :subtitle="session.user?.username || ''" />

    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8">
        <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 mb-6 flex items-center gap-2">
          <KeyRound class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          {{ t("account.changePasswordTitle") }}
        </h2>
        <form class="flex flex-col gap-4" @submit.prevent="submitSelfPassword">
          <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {{ t("account.currentPassword") }}
            <input v-model="selfForm.currentPassword" type="password" required class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm" />
          </label>
          <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {{ t("account.newPassword") }}
            <input v-model="selfForm.newPassword" type="password" required class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm" />
          </label>
          <button type="submit" :disabled="savingSelf" class="mt-2 inline-flex justify-center items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold py-3 px-4 rounded-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed shadow-md shadow-emerald-500/20">
            <Loader2 v-if="savingSelf" class="w-4 h-4 animate-spin" />
            {{ t("account.changePasswordAction") }}
          </button>
          <p v-if="selfMessage" class="text-sm text-zinc-500 dark:text-zinc-400 m-0">{{ selfMessage }}</p>
        </form>
      </div>

      <div v-if="isAdmin" class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8">
        <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 mb-6 flex items-center gap-2">
          <ShieldUser class="w-5 h-5 text-amber-600 dark:text-amber-400" />
          {{ t("account.adminResetTitle") }}
        </h2>
        <form class="flex flex-col gap-4" @submit.prevent="submitResetPassword">
          <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {{ t("account.targetUser") }}
            <select v-model="resetForm.userId" required class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm">
              <option value="" disabled>{{ t("account.selectUser") }}</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.username }} ({{ user.role }})
              </option>
            </select>
          </label>
          <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {{ t("account.newPassword") }}
            <input v-model="resetForm.newPassword" type="password" required class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm" />
          </label>
          <button type="submit" :disabled="savingReset || loadingUsers" class="mt-2 inline-flex justify-center items-center gap-2 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold py-3 px-4 rounded-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed shadow-md shadow-amber-500/20">
            <Loader2 v-if="savingReset || loadingUsers" class="w-4 h-4 animate-spin" />
            {{ t("account.resetPasswordAction") }}
          </button>
          <p v-if="resetMessage" class="text-sm text-zinc-500 dark:text-zinc-400 m-0">{{ resetMessage }}</p>
        </form>
        <p class="mt-4 text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-2">
          <UserRound class="w-4 h-4" />
          {{ t("account.adminResetHint") }}
        </p>
      </div>
    </section>
  </section>
</template>

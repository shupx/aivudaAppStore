<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppTopBar from "../components/AppTopBar.vue";
import { batchUpdateAppMemberships, changePassword, fetchManageableApps, fetchMe, fetchUsers, resetUserPassword, session } from "../services/api";
import { Check, ChevronDown, KeyRound, Loader2, ShieldUser, UserRound, Users2 } from "lucide-vue-next";

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
const savingBatch = ref(false);
const selfMessage = ref("");
const resetMessage = ref("");
const batchMessage = ref("");
const manageableApps = ref([]);
const userSearch = ref("");
const appSearch = ref("");
const selectedUserIds = ref([]);
const selectedAppIds = ref([]);
const userDropdownOpen = ref(false);
const appDropdownOpen = ref(false);
const batchAction = ref("add_developer");
const batchResult = ref(null);
const userPickerRef = ref(null);
const appPickerRef = ref(null);

const isAdmin = computed(() => session.user?.role === "admin");
const filteredUsers = computed(() => {
  const keyword = userSearch.value.trim().toLowerCase();
  return users.value.filter((user) => {
    if (!keyword) return true;
    return String(user.username || "").toLowerCase().includes(keyword);
  });
});
const filteredApps = computed(() => {
  const keyword = appSearch.value.trim().toLowerCase();
  return manageableApps.value.filter((app) => {
    if (!keyword) return true;
    return [app.name, app.app_id, app.owner_username]
      .map((value) => String(value || "").toLowerCase())
      .some((value) => value.includes(keyword));
  });
});
const selectedUsers = computed(() => users.value.filter((user) => selectedUserIds.value.includes(user.id)));
const selectedApps = computed(() => manageableApps.value.filter((app) => selectedAppIds.value.includes(app.app_id)));
const canSubmitBatch = computed(() => {
  if (selectedUserIds.value.length === 0 || selectedAppIds.value.length === 0) return false;
  if (batchAction.value === "transfer_admin" && selectedUserIds.value.length !== 1) return false;
  return true;
});
const transferAdminHint = computed(() => batchAction.value === "transfer_admin" && selectedUserIds.value.length !== 1);

async function load() {
  try {
    await fetchMe();
    loadingUsers.value = true;
    const [userData, appData] = await Promise.all([
      fetchUsers(),
      fetchManageableApps(),
    ]);
    users.value = userData.users || [];
    manageableApps.value = appData.apps || [];
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

function toggleUserSelection(userId) {
  if (selectedUserIds.value.includes(userId)) {
    selectedUserIds.value = selectedUserIds.value.filter((item) => item !== userId);
    return;
  }
  selectedUserIds.value = [...selectedUserIds.value, userId];
}

function toggleAppSelection(appId) {
  if (selectedAppIds.value.includes(appId)) {
    selectedAppIds.value = selectedAppIds.value.filter((item) => item !== appId);
    return;
  }
  selectedAppIds.value = [...selectedAppIds.value, appId];
}

function selectAllUsers() {
  selectedUserIds.value = users.value.map((user) => user.id);
}

function clearUsers() {
  selectedUserIds.value = [];
}

function selectAllApps() {
  selectedAppIds.value = manageableApps.value.map((app) => app.app_id);
}

function clearApps() {
  selectedAppIds.value = [];
}

async function submitBatch() {
  if (!canSubmitBatch.value) return;
  savingBatch.value = true;
  batchMessage.value = "";
  try {
    batchResult.value = await batchUpdateAppMemberships({
      action: batchAction.value,
      target_user_ids: selectedUserIds.value,
      app_ids: selectedAppIds.value,
    });
    batchMessage.value = t("account.batchSuccess");
  } catch (err) {
    batchMessage.value = String(err);
  } finally {
    savingBatch.value = false;
  }
}

function handleDocumentClick(event) {
  if (userPickerRef.value && !userPickerRef.value.contains(event.target)) {
    userDropdownOpen.value = false;
  }
  if (appPickerRef.value && !appPickerRef.value.contains(event.target)) {
    appDropdownOpen.value = false;
  }
}

onMounted(() => {
  load();
  document.addEventListener("click", handleDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
});
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

    <section class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 mb-6 flex items-center gap-2">
        <Users2 class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
        {{ t("account.batchTitle") }}
      </h2>

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div ref="userPickerRef" class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-zinc-700 dark:text-zinc-300 m-0">{{ t("account.batchUsersTitle") }}</h3>
            <div class="flex items-center gap-3 text-xs">
              <button type="button" class="text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" @click="selectAllUsers">{{ t("account.selectAll") }}</button>
              <button type="button" class="text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" @click="clearUsers">{{ t("account.clearAll") }}</button>
            </div>
          </div>
          <div class="rounded-2xl border border-zinc-200 dark:border-zinc-700/60 bg-white/90 dark:bg-zinc-950/50">
            <div class="flex items-center gap-3 px-4 py-3">
              <input v-model.trim="userSearch" :placeholder="t('account.searchUsers')" class="min-w-0 flex-1 bg-transparent text-sm text-zinc-900 dark:text-zinc-100 outline-none" @focus="userDropdownOpen = true" />
              <button type="button" class="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200" @click="userDropdownOpen = !userDropdownOpen">
                <ChevronDown class="w-4 h-4" />
              </button>
            </div>
            <div v-if="userDropdownOpen" class="border-t border-zinc-200 dark:border-zinc-800 max-h-64 overflow-y-auto p-2">
              <button
                v-for="user in filteredUsers"
                :key="user.id"
                type="button"
                class="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition-colors"
                :class="selectedUserIds.includes(user.id) ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'"
                @click="toggleUserSelection(user.id)"
              >
                <span>{{ user.username }}</span>
                <Check v-if="selectedUserIds.includes(user.id)" class="w-4 h-4" />
              </button>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <span v-for="user in selectedUsers" :key="user.id" class="inline-flex items-center rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
              {{ user.username }}
            </span>
          </div>
        </div>

        <div ref="appPickerRef" class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-zinc-700 dark:text-zinc-300 m-0">{{ t("account.batchAppsTitle") }}</h3>
            <div class="flex items-center gap-3 text-xs">
              <button type="button" class="text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" @click="selectAllApps">{{ t("account.selectAll") }}</button>
              <button type="button" class="text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" @click="clearApps">{{ t("account.clearAll") }}</button>
            </div>
          </div>
          <div class="rounded-2xl border border-zinc-200 dark:border-zinc-700/60 bg-white/90 dark:bg-zinc-950/50">
            <div class="flex items-center gap-3 px-4 py-3">
              <input v-model.trim="appSearch" :placeholder="t('account.searchApps')" class="min-w-0 flex-1 bg-transparent text-sm text-zinc-900 dark:text-zinc-100 outline-none" @focus="appDropdownOpen = true" />
              <button type="button" class="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200" @click="appDropdownOpen = !appDropdownOpen">
                <ChevronDown class="w-4 h-4" />
              </button>
            </div>
            <div v-if="appDropdownOpen" class="border-t border-zinc-200 dark:border-zinc-800 max-h-64 overflow-y-auto p-2">
              <button
                v-for="app in filteredApps"
                :key="app.app_id"
                type="button"
                class="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition-colors"
                :class="selectedAppIds.includes(app.app_id) ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'"
                @click="toggleAppSelection(app.app_id)"
              >
                <span>{{ app.name || app.app_id }}</span>
                <Check v-if="selectedAppIds.includes(app.app_id)" class="w-4 h-4" />
              </button>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <span v-for="app in selectedApps" :key="app.app_id" class="inline-flex items-center rounded-full bg-zinc-100 dark:bg-zinc-800 px-3 py-1 text-xs font-medium text-zinc-700 dark:text-zinc-300">
              {{ app.name || app.app_id }}
            </span>
          </div>
        </div>
      </div>

      <div class="mt-6 flex flex-col gap-4">
        <div class="flex flex-wrap gap-3">
          <button type="button" class="px-4 py-2 rounded-xl font-semibold transition-colors" :class="batchAction === 'add_developer' ? 'bg-emerald-500 text-zinc-950' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300'" @click="batchAction = 'add_developer'">
            {{ t("account.batchAddDeveloper") }}
          </button>
          <button type="button" class="px-4 py-2 rounded-xl font-semibold transition-colors" :class="batchAction === 'remove_developer' ? 'bg-amber-500 text-zinc-950' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300'" @click="batchAction = 'remove_developer'">
            {{ t("account.batchRemoveDeveloper") }}
          </button>
          <button type="button" class="px-4 py-2 rounded-xl font-semibold transition-colors" :class="batchAction === 'transfer_admin' ? 'bg-red-500 text-white' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300'" @click="batchAction = 'transfer_admin'">
            {{ t("account.batchTransferAdmin") }}
          </button>
        </div>

        <p v-if="transferAdminHint" class="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl px-4 py-3 m-0">
          {{ t("account.transferAdminSingleUserHint") }}
        </p>

        <div class="flex items-center gap-3">
          <button type="button" :disabled="savingBatch || !canSubmitBatch" class="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold py-3 px-5 rounded-xl transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-md shadow-emerald-500/20" @click="submitBatch">
            <Loader2 v-if="savingBatch" class="w-4 h-4 animate-spin" />
            {{ t("account.applyBatchAction") }}
          </button>
          <p v-if="batchMessage" class="text-sm text-zinc-500 dark:text-zinc-400 m-0">{{ batchMessage }}</p>
        </div>

        <div v-if="batchResult" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="rounded-2xl border border-emerald-200 dark:border-emerald-500/20 bg-emerald-50 dark:bg-emerald-500/10 px-4 py-4">
            <div class="text-sm font-semibold text-emerald-700 dark:text-emerald-300">{{ t("account.batchSuccesses") }}</div>
            <div class="mt-2 text-2xl font-bold text-emerald-700 dark:text-emerald-300">{{ batchResult.successes?.length || 0 }}</div>
          </div>
          <div class="rounded-2xl border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/10 px-4 py-4">
            <div class="text-sm font-semibold text-amber-700 dark:text-amber-300">{{ t("account.batchSkipped") }}</div>
            <div class="mt-2 text-2xl font-bold text-amber-700 dark:text-amber-300">{{ batchResult.skipped?.length || 0 }}</div>
          </div>
          <div class="rounded-2xl border border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/10 px-4 py-4">
            <div class="text-sm font-semibold text-red-700 dark:text-red-300">{{ t("account.batchFailures") }}</div>
            <div class="mt-2 text-2xl font-bold text-red-700 dark:text-red-300">{{ batchResult.failures?.length || 0 }}</div>
          </div>
        </div>

        <div v-if="batchResult?.failures?.length || batchResult?.skipped?.length" class="rounded-2xl border border-zinc-200 dark:border-zinc-700/60 bg-white/70 dark:bg-zinc-950/40 px-4 py-4">
          <h3 class="text-sm font-semibold text-zinc-700 dark:text-zinc-300 m-0 mb-3">{{ t("account.batchDetails") }}</h3>
          <div class="flex flex-col gap-2 text-sm text-zinc-600 dark:text-zinc-400">
            <div v-for="item in [...(batchResult.failures || []), ...(batchResult.skipped || [])]" :key="`${item.app_id}-${item.target_user_id}-${item.message}`">
              {{ item.app_id || "-" }} / {{ item.target_user_id }}: {{ item.message }}
            </div>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

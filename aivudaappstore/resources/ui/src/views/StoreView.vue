<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppCard from "../components/AppCard.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreApps, logout, deleteApp, session } from "../services/api";
import { useAppDownload } from "../composables/useAppDownload";
import { Loader2, Inbox, Search, ArrowUpDown, Check, ArrowUp, ArrowDown, Funnel } from "lucide-vue-next";

const router = useRouter();
const { t } = useI18n();
const loading = ref(true);
const apps = ref([]);
const searchText = ref("");
const sortKey = ref("updated_at");
const sortDirection = ref("desc");
const downloadingId = ref("");
const deletingId = ref("");
const ownerFilterOpen = ref(false);
const selectedOwners = ref([]);
const ownerFilterRef = ref(null);
const { downloadAppPackage } = useAppDownload();
const sortOptions = computed(() => ([
  { key: "name", label: t("store.sortName") },
  { key: "created_at", label: t("store.sortCreatedAt") },
  { key: "updated_at", label: t("store.sortUpdatedAt") },
]));

const isAdmin = () => session.user?.role === "admin";
const ownerOptions = computed(() => {
  const seen = new Set();
  const currentUser = String(session.user?.username || "").trim();
  const options = [];

  if (currentUser) {
    seen.add(currentUser);
    options.push(currentUser);
  }

  for (const item of apps.value) {
    const owner = String(item?.owner_username || "").trim();
    if (!owner || seen.has(owner)) continue;
    seen.add(owner);
    options.push(owner);
  }

  return options;
});

const filteredApps = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  const list = apps.value.filter((item) => {
    if (selectedOwners.value.length > 0 && !selectedOwners.value.includes(item?.owner_username || "")) return false;
    if (!keyword) return true;
    const haystacks = [
      item?.manifest?.name,
      item?.app_id,
      item?.manifest?.description,
      item?.version,
      item?.owner_username,
    ]
      .map((value) => String(value || "").toLowerCase());
    return haystacks.some((value) => value.includes(keyword));
  });

  list.sort((a, b) => {
    const dir = sortDirection.value === "asc" ? 1 : -1;
    if (sortKey.value === "name") {
      const left = String(a?.manifest?.name || a?.app_id || "").toLowerCase();
      const right = String(b?.manifest?.name || b?.app_id || "").toLowerCase();
      return dir * left.localeCompare(right);
    }

    const left = Number(a?.[sortKey.value] || 0);
    const right = Number(b?.[sortKey.value] || 0);
    if (left === right) {
      const leftName = String(a?.manifest?.name || a?.app_id || "").toLowerCase();
      const rightName = String(b?.manifest?.name || b?.app_id || "").toLowerCase();
      return leftName.localeCompare(rightName);
    }
    return dir * (left - right);
  });

  return list;
});

async function load() {
  loading.value = true;
  try {
    await fetchMe();
    const data = await fetchStoreApps();
    apps.value = data.items || [];
  } catch {
    logout();
    router.push("/login");
  } finally {
    loading.value = false;
  }
}

function goDetail(appId) {
  router.push(`/apps/${encodeURIComponent(appId)}`);
}

async function downloadPackage(item) {
  const key = `${item.app_id}:${item.version}`;
  downloadingId.value = key;
  try {
    await downloadAppPackage(item.app_id, item.version);
  } catch (err) {
    window.alert(String(err));
  } finally {
    downloadingId.value = "";
  }
}

async function handleDeleteApp(item) {
  const name = item.manifest?.name || item.app_id;
  const confirmed = window.confirm(
    t("store.confirmDeleteAppMessage", { name })
  );
  if (!confirmed) return;
  const doubleConfirm = window.confirm(
    t("store.confirmDeleteAppAgain", { name })
  );
  if (!doubleConfirm) return;
  deletingId.value = item.app_id;
  try {
    await deleteApp(item.app_id);
    await load();
  } catch (err) {
    window.alert(String(err));
  } finally {
    deletingId.value = "";
  }
}

function setSortKey(nextKey) {
  if (sortKey.value === nextKey) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
    return;
  }
  sortKey.value = nextKey;
  sortDirection.value = nextKey === "name" ? "asc" : "desc";
}

function toggleOwnerFilter() {
  ownerFilterOpen.value = !ownerFilterOpen.value;
}

function toggleOwner(owner) {
  if (selectedOwners.value.includes(owner)) {
    selectedOwners.value = selectedOwners.value.filter((item) => item !== owner);
    return;
  }
  selectedOwners.value = [...selectedOwners.value, owner];
}

function clearOwnerFilter() {
  selectedOwners.value = [];
}

function selectAllOwners() {
  selectedOwners.value = [...ownerOptions.value];
}

function handleDocumentClick(event) {
  if (!ownerFilterOpen.value) return;
  const container = ownerFilterRef.value;
  if (!container) return;
  if (container.contains(event.target)) return;
  ownerFilterOpen.value = false;
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
  <section class="w-[min(1240px,96vw)] mx-auto my-6 flex flex-col gap-6">
    <AppTopBar :title="t('store.title')" :subtitle="t('store.subtitle')" :show-back="false" />

    <section class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 mb-6 flex items-center gap-2">
        {{ t("store.appList") }}
        <span class="bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 text-xs py-1 px-2.5 rounded-full font-medium" v-if="!loading">{{ apps.length }}</span>
      </h2>

      <div class="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-3 rounded-2xl border border-zinc-200 bg-white/90 px-4 py-3 text-sm text-zinc-500 shadow-sm transition-colors focus-within:border-emerald-500 dark:border-zinc-700/60 dark:bg-zinc-900/80 dark:text-zinc-400">
            <Search class="h-4 w-4" />
            <input
              v-model.trim="searchText"
              :placeholder="t('store.searchPlaceholder')"
              class="w-full min-w-0 bg-transparent text-sm text-zinc-900 outline-none placeholder:text-zinc-400 dark:text-zinc-100 dark:placeholder:text-zinc-500 md:w-80"
            />
          </label>
          <div ref="ownerFilterRef" class="relative">
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center text-zinc-500 transition-colors hover:text-emerald-600 dark:text-zinc-300 dark:hover:text-emerald-300"
              :class="selectedOwners.length > 0 ? 'text-emerald-600 dark:text-emerald-300' : ''"
              :title="t('store.filterByOwner')"
              @click="toggleOwnerFilter"
            >
              <Funnel class="h-4 w-4" />
            </button>
            <div v-if="ownerFilterOpen" class="absolute left-0 top-14 z-20 min-w-[260px] rounded-2xl border border-zinc-200 bg-white/95 p-3 shadow-xl dark:border-zinc-700/60 dark:bg-zinc-900/95">
              <div class="mb-2 flex items-center justify-between gap-3">
                <span class="text-sm font-semibold text-zinc-800 dark:text-zinc-200">{{ t("store.filterByOwner") }}</span>
                <div class="flex items-center gap-3">
                  <button type="button" class="text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" @click="selectAllOwners">
                    {{ t("store.selectAllOwners") }}
                  </button>
                  <button type="button" class="text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" @click="clearOwnerFilter">
                    {{ t("store.clearOwnerFilter") }}
                  </button>
                </div>
              </div>
              <div class="flex max-h-64 flex-col gap-1 overflow-auto">
                <button
                  v-for="owner in ownerOptions"
                  :key="owner"
                  type="button"
                  class="flex items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition-colors"
                  :class="selectedOwners.includes(owner)
                    ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                    : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'"
                  @click="toggleOwner(owner)"
                >
                  <span>
                    {{ owner }}
                    <span v-if="owner === session.user?.username" class="ml-2 text-xs text-zinc-500 dark:text-zinc-400">
                      {{ t("store.currentUserBadge") }}
                    </span>
                  </span>
                  <Check v-if="selectedOwners.includes(owner)" class="h-4 w-4 shrink-0" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-zinc-500 dark:text-zinc-400">{{ t("store.sortBy") }}</span>
          <button
            v-for="option in sortOptions"
            :key="option.key"
            type="button"
            class="inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition-all"
            :class="sortKey === option.key
              ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-zinc-200 bg-white/80 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700/60 dark:bg-zinc-900/70 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:bg-zinc-800/70'"
            @click="setSortKey(option.key)"
          >
            <Check v-if="sortKey === option.key" class="h-4 w-4" />
            <ArrowUpDown v-else class="h-4 w-4" />
            <span>{{ option.label }}</span>
            <ArrowUp v-if="sortKey === option.key && sortDirection === 'asc'" class="h-4 w-4" />
            <ArrowDown v-if="sortKey === option.key && sortDirection === 'desc'" class="h-4 w-4" />
          </button>
        </div>
      </div>
      
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-zinc-500 dark:text-zinc-400 gap-3">
        <Loader2 class="w-8 h-8 animate-spin text-emerald-500" />
        <span>{{ t("store.loading") }}</span>
      </div>
      
      <div v-else-if="apps.length === 0" class="flex flex-col items-center justify-center py-20 text-zinc-400 dark:text-zinc-500 gap-3">
        <Inbox class="w-12 h-12 opacity-50" />
        <span>{{ t("store.empty") }}</span>
      </div>

      <div v-else-if="filteredApps.length === 0" class="flex flex-col items-center justify-center py-20 text-zinc-400 dark:text-zinc-500 gap-3">
        <Search class="w-12 h-12 opacity-50" />
        <span>{{ t("store.noSearchResults") }}</span>
      </div>
      
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <AppCard
          v-for="item in filteredApps"
          :key="item.app_id"
          :title="item.manifest?.name || item.app_id"
          :subtitle="t('store.newestVersionPrefix', { version: item.version })"
          :description="item.manifest?.description || ''"
          :owner-username="item.owner_username || ''"
          :created-at="item.created_at"
          :updated-at="item.updated_at"
          :downloading="downloadingId === `${item.app_id}:${item.version}`"
          :show-delete="isAdmin()"
          :deleting="deletingId === item.app_id"
          @click="goDetail(item.app_id)"
          @download="downloadPackage(item)"
          @delete="handleDeleteApp(item)"
        />
      </div>
    </section>
  </section>
</template>

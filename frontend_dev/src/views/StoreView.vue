<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppCard from "../components/AppCard.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreApps, logout, deleteApp, session } from "../services/api";
import { useAppDownload } from "../composables/useAppDownload";

const router = useRouter();
const { t } = useI18n();
const loading = ref(true);
const apps = ref([]);
const downloadingId = ref("");
const deletingId = ref("");
const { downloadAppPackage } = useAppDownload();

const isAdmin = () => session.user?.role === "admin";

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

onMounted(load);
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar :title="t('store.title')" :subtitle="t('store.subtitle')" :show-back="false" />

    <section class="card list-wrap">
      <h2>{{ t("store.appList") }}</h2>
      <div v-if="loading" class="hint">{{ t("store.loading") }}</div>
      <div v-else-if="apps.length === 0" class="hint">{{ t("store.empty") }}</div>
      <div v-else class="card-grid">
        <AppCard
          v-for="item in apps"
          :key="item.app_id"
          :title="item.manifest?.name || item.app_id"
          :subtitle="t('store.versionPrefix', { version: item.version })"
          :description="item.manifest?.description || ''"
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

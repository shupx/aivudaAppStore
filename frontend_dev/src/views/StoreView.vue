<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppCard from "../components/AppCard.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreApps, logout, deleteApp, session } from "../services/api";
import { useAppDownload } from "../composables/useAppDownload";

const router = useRouter();
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
    `⚠️ 危险操作！\n\n确定要永久删除应用「${name}」吗？\n\n此操作将删除该应用的所有版本、安装包文件和全部记录，且不可恢复！`
  );
  if (!confirmed) return;
  const doubleConfirm = window.confirm(
    `再次确认：删除应用「${name}」后无法恢复，是否继续？`
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
    <AppTopBar title="应用商店" subtitle="全部应用" :show-back="false" />

    <section class="card list-wrap">
      <h2>应用列表</h2>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="apps.length === 0" class="hint">暂无应用</div>
      <div v-else class="card-grid">
        <AppCard
          v-for="item in apps"
          :key="item.app_id"
          :title="item.manifest?.name || item.app_id"
          :subtitle="`版本 ${item.version}`"
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

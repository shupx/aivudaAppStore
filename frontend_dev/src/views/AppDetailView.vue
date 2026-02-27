<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreAppDetail, logout } from "../services/api";
import { useAppDownload } from "../composables/useAppDownload";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const detail = ref(null);
const { downloading, progress: downloadProgress, downloadAppPackage } = useAppDownload();

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

async function downloadPackage() {
  if (!detail.value?.db_records?.app || !detail.value?.db_records?.app_version) {
    window.alert("获取应用信息失败");
    return;
  }

  try {
    const app = detail.value.db_records.app;
    const appVersion = detail.value.db_records.app_version;
    const appId = app.app_id;
    const version = Array.isArray(appVersion) && appVersion.length > 0 ? appVersion[0].version : "unknown";

    await downloadAppPackage(appId, version);
  } catch (err) {
    window.alert(String(err));
  }
}

async function load() {
  loading.value = true;
  try {
    await fetchMe();
    detail.value = await fetchStoreAppDetail(route.params.appId);
  } catch {
    logout();
    router.push("/login");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar title="应用详情" :subtitle="String(route.params.appId)" />

    <section class="card list-wrap detail-header">
      <div class="detail-header-content">
        <div>
          <p class="app-name">{{ detail?.db_records?.app?.name || "未知应用" }}</p>
          <p class="app-id">{{ detail?.db_records?.app?.app_id || "应用详情" }}</p>
          <p class="sub">版本 {{ detail?.db_records?.app_version?.[0]?.version || "未知" }}</p>
        </div>
        <button
          class="btn-download"
          @click="downloadPackage"
          :disabled="downloading"
          :title="downloading ? '下载中...' : '下载应用包'"
        >
          <span v-if="downloading">⏳ {{ downloadProgress }}%</span>
          <span v-else>⬇ 下载安装包</span>
        </button>
      </div>
    </section>

    <section class="card list-wrap">
      <h2>repo.db 记录</h2>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="!detail || !detail.db_records" class="hint">无记录</div>
      <div v-else class="version-list">
        <article class="version-item detail-section">
          <h3 class="detail-title">app</h3>
          <pre>{{ pretty(detail.db_records.app || {}) }}</pre>
        </article>
        <article class="version-item detail-section">
          <h3 class="detail-title">app_version</h3>
          <pre>{{ pretty(detail.db_records.app_version || []) }}</pre>
        </article>
        <article class="version-item detail-section">
          <h3 class="detail-title">app_target</h3>
          <pre>{{ pretty(detail.db_records.app_target || []) }}</pre>
        </article>
        <article class="version-item detail-section">
          <h3 class="detail-title">app_audit_log</h3>
          <pre>{{ pretty(detail.db_records.app_audit_log || []) }}</pre>
        </article>
      </div>
    </section>
  </section>
</template>

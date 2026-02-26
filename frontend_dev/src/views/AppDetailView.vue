<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreAppDetail, fetchStoreDownloadUrl, buildApiUrl, logout } from "../services/api";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const downloading = ref(false);
const detail = ref(null);

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

function triggerBrowserDownload(fileUrl, filename) {
  const link = document.createElement("a");
  link.href = fileUrl;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

async function downloadPackage() {
  if (!detail.value?.db_records?.app || !detail.value?.db_records?.app_version) {
    window.alert("获取应用信息失败");
    return;
  }

  downloading.value = true;
  try {
    const app = detail.value.db_records.app;
    const appVersion = detail.value.db_records.app_version;
    const appId = app.app_id;
    const version = Array.isArray(appVersion) && appVersion.length > 0 ? appVersion[0].version : "unknown";

    const info = await fetchStoreDownloadUrl(appId, version);
    const fileUrl = buildApiUrl(info.url);
    const filename = `${appId}-${version}.zip`;

    const res = await fetch(fileUrl);
    if (!res.ok) throw new Error(`下载失败: ${res.status}`);
    const blob = await res.blob();

    if ("showSaveFilePicker" in window && window.isSecureContext) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: filename,
          types: [{ description: "ZIP Package", accept: { "application/zip": [".zip"] } }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return;
      } catch (pickerErr) {
        const name = pickerErr?.name || "";
        if (name === "AbortError" || name === "NotAllowedError" || name === "SecurityError") {
          return;
        }
        throw pickerErr;
      }
    }

    const blobUrl = URL.createObjectURL(blob);
    triggerBrowserDownload(blobUrl, filename);
    URL.revokeObjectURL(blobUrl);
  } catch (err) {
    window.alert(String(err));
  } finally {
    downloading.value = false;
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
          <span v-if="downloading">⏳</span>
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

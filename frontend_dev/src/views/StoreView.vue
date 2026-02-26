<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppCard from "../components/AppCard.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { buildApiUrl, fetchMe, fetchStoreApps, fetchStoreDownloadUrl, logout } from "../services/api";

const router = useRouter();
const loading = ref(true);
const apps = ref([]);
const downloadingId = ref("");

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

function triggerBrowserDownload(fileUrl, filename) {
  const link = document.createElement("a");
  link.href = fileUrl;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

async function downloadPackage(item) {
  const key = `${item.app_id}:${item.version}`;
  downloadingId.value = key;
  try {
    const info = await fetchStoreDownloadUrl(item.app_id, item.version);
    const fileUrl = buildApiUrl(info.url);
    const filename = `${item.app_id}-${item.version}.zip`;

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
    downloadingId.value = "";
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
          @click="goDetail(item.app_id)"
          @download="downloadPackage(item)"
        />
      </div>
    </section>
  </section>
</template>

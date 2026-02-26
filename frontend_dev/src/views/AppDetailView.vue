<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreAppDetail, logout } from "../services/api";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const detail = ref(null);

function pretty(data) {
  return JSON.stringify(data, null, 2);
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

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreAppDetail, logout } from "../services/api";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const detail = ref(null);

function formatTs(ts) {
  if (!ts) return "-";
  const date = new Date(ts * 1000);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${d} ${hh}:${mm}`;
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
      <h2>版本列表</h2>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="!detail || !detail.items || detail.items.length === 0" class="hint">暂无可用版本</div>
      <div v-else class="version-list">
        <article v-for="item in detail.items" :key="item.version" class="version-item">
          <h3>{{ item.version }}</h3>
          <p class="sub">更新时间: {{ formatTs(item.updated_at) }}</p>
          <p>{{ item.manifest?.description || '暂无描述' }}</p>
          <p class="sub">运行时目标: {{ (item.manifest?.targets || []).map((t) => `${t.os}/${t.arch}`).join(', ') || '-' }}</p>
        </article>
      </div>
    </section>
  </section>
</template>

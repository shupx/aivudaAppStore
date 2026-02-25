<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppCard from "../components/AppCard.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchMyApps, logout } from "../services/api";

const router = useRouter();
const loading = ref(true);
const apps = ref([]);

async function load() {
  loading.value = true;
  try {
    await fetchMe();
    const data = await fetchMyApps();
    apps.value = data.items || [];
  } catch {
    logout();
    router.push("/login");
  } finally {
    loading.value = false;
  }
}

function goDetail(appId) {
  router.push(`/me/apps/${encodeURIComponent(appId)}`);
}

onMounted(load);
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar title="我的应用" subtitle="可管理与更新" />

    <section class="card list-wrap">
      <h2>应用列表</h2>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="apps.length === 0" class="hint">你还没有应用</div>
      <div v-else class="card-grid">
        <AppCard
          v-for="item in apps"
          :key="item.app_id"
          :title="item.name || item.app_id"
          :subtitle="item.app_id"
          :description="item.description || ''"
          :tag="item.category || ''"
          @click="goDetail(item.app_id)"
        />
      </div>
    </section>
  </section>
</template>

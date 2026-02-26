<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppCard from "../components/AppCard.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, fetchStoreApps, logout } from "../services/api";

const router = useRouter();
const loading = ref(true);
const apps = ref([]);

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
          @click="goDetail(item.app_id)"
        />
      </div>
    </section>
  </section>
</template>

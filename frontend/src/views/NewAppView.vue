<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { createApp, fetchMe, logout } from "../services/api";

const router = useRouter();
const output = ref("");
const form = reactive({ app_id: "", name: "", category: "general", description: "" });

function setOutput(data) {
  output.value = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function submit() {
  try {
    await fetchMe();
    const data = await createApp(form);
    setOutput(data);
    router.push(`/me/apps/${encodeURIComponent(form.app_id)}`);
  } catch (err) {
    if (String(err).includes("401")) {
      logout();
      router.push("/login");
      return;
    }
    setOutput(String(err));
  }
}
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar title="上传新应用" subtitle="先创建应用，再在详情页上传版本与构建" />

    <section class="card list-wrap">
      <h2>新建应用</h2>
      <form class="grid3" @submit.prevent="submit">
        <input v-model="form.app_id" placeholder="app_id" required />
        <input v-model="form.name" placeholder="name" required />
        <input v-model="form.category" placeholder="category" />
        <input v-model="form.description" class="full" placeholder="description" />
        <button class="full">创建</button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

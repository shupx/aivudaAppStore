<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, logout, uploadSimpleApp } from "../services/api";

const router = useRouter();
const output = ref("");
const fileRef = ref(null);
const form = reactive({ name: "", version: "0.1.0", description: "" });

function setOutput(data) {
  output.value = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function onFileChange(e) {
  fileRef.value = e.target.files && e.target.files.length ? e.target.files[0] : null;
}

async function submit() {
  try {
    await fetchMe();
    if (!fileRef.value) {
      setOutput("必须选择安装包文件");
      return;
    }
    const data = await uploadSimpleApp(form, fileRef.value);
    setOutput(data);
    router.push(`/apps/${encodeURIComponent(data.app_id)}`);
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
    <AppTopBar title="上传新应用" subtitle="极简上传：name + file" />

    <section class="card list-wrap">
      <h2>新建应用</h2>
      <form class="grid3" @submit.prevent="submit">
        <input v-model="form.name" placeholder="name" required />
        <input v-model="form.version" placeholder="version" />
        <input v-model="form.description" class="full" placeholder="description" />
        <input class="full" type="file" @change="onFileChange" />
        <button class="full">上传</button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

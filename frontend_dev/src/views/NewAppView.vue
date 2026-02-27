<script setup>
import { useRouter } from "vue-router";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { useAppUpload } from "../composables/useAppUpload";

const router = useRouter();
const { output, form, sampleUrl, bindFile, submitPackage } = useAppUpload();

async function submit() {
  await submitPackage({
    onSuccess(data) {
      router.push(`/apps/${encodeURIComponent(data.app_id)}`);
    },
    onAuthFail() {
      router.push("/login");
    },
  });
}
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar title="上传新应用" subtitle="按规范上传材料，后端统一打包" />

    <section class="card list-wrap">
      <h2>基础信息</h2>
      <form class="grid3" @submit.prevent="submit">
        <input v-model="form.name.value" placeholder="name" required />
        <input v-model="form.version.value" placeholder="version" required />
        <input v-model="form.description.value" class="full" placeholder="description" />

        <h2 class="full">必需材料</h2>
        <div class="file-row full">
          <span class="file-label">应用材料压缩包（zip）</span>
          <input type="file" accept=".zip" @change="bindFile('packageZip', $event)" />
        </div>
        <p class="hint full">必须包含：assets/icon.png。</p>
        <p class="hint full">
          <a class="link" :href="sampleUrl" target="_blank" rel="noreferrer">下载示例 package.zip</a>
        </p>

        <button class="full">上传</button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

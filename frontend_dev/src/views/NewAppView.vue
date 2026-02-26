<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { fetchMe, logout, session, uploadPackage } from "../services/api";

const router = useRouter();
const output = ref("");

const form = {
  name: ref(""),
  version: ref("0.1.0"),
  description: ref(""),
};

const files = {
  packageZip: ref(null),
};

const sampleUrl = computed(() => {
  const base = (session.baseUrl || "").replace(/\/$/, "");
  return base ? `${base}/store/sample-package` : "/store/sample-package";
});

function setOutput(data) {
  output.value = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function bindFile(refKey, e) {
  files[refKey].value = e.target.files && e.target.files.length ? e.target.files[0] : null;
}

async function submit() {
  try {
    await fetchMe();
    if (!form.name.value.trim() || !form.version.value.trim()) {
      setOutput("必须填写 name 与 version");
      return;
    }
    if (!files.packageZip.value) {
      setOutput("必须上传 package.zip");
      return;
    }

    const fd = new FormData();
    fd.append("name", form.name.value.trim());
    fd.append("version", form.version.value.trim());
    fd.append("description", form.description.value.trim());
    fd.append("package_zip", files.packageZip.value);

    const data = await uploadPackage(fd);
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
        <p class="hint full">必须包含：scripts/install.sh、scripts/uninstall.sh、scripts/start.sh、assets/icon.png。可包含 stop.sh、upgrade.sh、config/、README.md。</p>
        <p class="hint full">
          <a class="link" :href="sampleUrl" target="_blank" rel="noreferrer">下载示例 package.zip</a>
        </p>

        <button class="full">上传</button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

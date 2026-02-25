<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import {
  createVersion,
  fetchMe,
  fetchMyAppDetail,
  logout,
  publishVersion,
  unpublishVersion,
  uploadTarget,
} from "../services/api";

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const detail = ref(null);
const output = ref("");
const targetFile = ref(null);

const versionForm = reactive({ version: "", channel: "stable", run_entrypoint: "./run.sh" });
const targetForm = reactive({
  version: "",
  os: "linux",
  arch: "amd64",
  runtime: "docker",
  min_os_version: "",
  image_ref: "repo/demo:1.0.0",
  image_digest: "sha256:abc",
});
const publishForm = reactive({ version: "" });

function setOutput(data) {
  output.value = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function load() {
  loading.value = true;
  try {
    await fetchMe();
    detail.value = await fetchMyAppDetail(route.params.appId);
  } catch {
    logout();
    router.push("/login");
  } finally {
    loading.value = false;
  }
}

async function submitCreateVersion() {
  try {
    const data = await createVersion(route.params.appId, versionForm);
    setOutput(data);
    await load();
  } catch (err) {
    setOutput(String(err));
  }
}

function onTargetFileChange(e) {
  targetFile.value = e.target.files && e.target.files.length ? e.target.files[0] : null;
}

async function submitTarget() {
  if (targetForm.runtime === "host" && !targetFile.value) {
    setOutput("host 模式必须选择 artifact 文件");
    return;
  }

  const payload = { ...targetForm };
  if (payload.runtime === "host") {
    delete payload.image_ref;
    delete payload.image_digest;
  }

  try {
    const data = await uploadTarget(route.params.appId, targetForm.version, payload, targetFile.value);
    setOutput(data);
    await load();
  } catch (err) {
    setOutput(String(err));
  }
}

async function doPublish() {
  try {
    const data = await publishVersion(route.params.appId, publishForm.version);
    setOutput(data);
    await load();
  } catch (err) {
    setOutput(String(err));
  }
}

async function doUnpublish() {
  try {
    const data = await unpublishVersion(route.params.appId, publishForm.version);
    setOutput(data);
    await load();
  } catch (err) {
    setOutput(String(err));
  }
}

onMounted(load);
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar title="我的应用详情" :subtitle="String(route.params.appId)" />

    <section class="card list-wrap">
      <h2>基础信息</h2>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="!detail" class="hint">应用不存在</div>
      <div v-else>
        <p><strong>名称:</strong> {{ detail.app?.name }}</p>
        <p><strong>分类:</strong> {{ detail.app?.category }}</p>
        <p><strong>描述:</strong> {{ detail.app?.description || '-' }}</p>
      </div>
    </section>

    <section class="card list-wrap">
      <h2>版本列表</h2>
      <div v-if="!detail || !detail.versions || detail.versions.length === 0" class="hint">暂无版本</div>
      <div v-else class="version-list">
        <article v-for="v in detail.versions" :key="v.id" class="version-item">
          <h3>v{{ v.version }} <span class="chip">{{ v.status }}</span></h3>
          <p class="sub">channel: {{ v.channel }} | updated_at: {{ v.updated_at }}</p>
        </article>
      </div>
    </section>

    <section class="card list-wrap">
      <h2>更新操作</h2>
      <div class="ops-grid">
        <form class="grid3" @submit.prevent="submitCreateVersion">
          <h3 class="full">1. 新建版本</h3>
          <input v-model="versionForm.version" placeholder="version" required />
          <input v-model="versionForm.channel" placeholder="channel" />
          <input v-model="versionForm.run_entrypoint" placeholder="run_entrypoint" />
          <button class="full">创建版本</button>
        </form>

        <form class="grid3" @submit.prevent="submitTarget">
          <h3 class="full">2. 上传平台构建</h3>
          <input v-model="targetForm.version" placeholder="version" required />
          <input v-model="targetForm.os" placeholder="os" required />
          <input v-model="targetForm.arch" placeholder="arch" required />
          <select v-model="targetForm.runtime">
            <option value="docker">docker</option>
            <option value="podman">podman</option>
            <option value="host">host</option>
          </select>
          <input v-model="targetForm.min_os_version" placeholder="min_os_version" />
          <input
            v-model="targetForm.image_ref"
            class="full"
            placeholder="image_ref"
            :disabled="targetForm.runtime === 'host'"
          />
          <input
            v-model="targetForm.image_digest"
            class="full"
            placeholder="image_digest"
            :disabled="targetForm.runtime === 'host'"
          />
          <input class="full" type="file" :disabled="targetForm.runtime !== 'host'" @change="onTargetFileChange" />
          <button class="full">上传平台构建</button>
        </form>

        <form class="grid3" @submit.prevent>
          <h3 class="full">3. 发布/下架</h3>
          <input v-model="publishForm.version" placeholder="version" required />
          <div class="btnrow full">
            <button type="button" @click="doPublish">发布</button>
            <button type="button" @click="doUnpublish">下架</button>
          </div>
        </form>
      </div>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

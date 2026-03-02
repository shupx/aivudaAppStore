<script setup>
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { useAppUpload } from "../composables/useAppUpload";

const router = useRouter();
const { t } = useI18n();
const {
  output,
  parsingManifest,
  submitting,
  parsedReady,
  packageEntries,
  packageTreeLines,
  manifestFoundPath,
  form,
  sampleUrl,
  generateAppId,
  bindPackageZip,
  submitPackage,
} = useAppUpload(t);

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
    <AppTopBar :title="t('upload.title')" :subtitle="t('upload.subtitle')" />

    <section class="card list-wrap">
      <h2>{{ t("upload.stepPackage") }}</h2>
      <form class="grid3" @submit.prevent="submit">
        <div class="file-row full">
          <span class="file-label">{{ t("upload.packageZip") }}</span>
          <input type="file" accept=".zip" @change="bindPackageZip" />
        </div>
        <p class="hint full" v-if="parsingManifest">{{ t("upload.parsing") }}</p>
        <p class="hint full">{{ t("upload.hintManifest") }}</p>

        <p class="hint full">
          <a class="link" :href="sampleUrl" target="_blank" rel="noreferrer">{{ t("upload.downloadSample") }}</a>
        </p>

        <template v-if="parsedReady">
          <h2 class="full">{{ t("upload.stepManifest") }}</h2>
          <p class="hint full">{{ t("upload.manifestPath", { path: manifestFoundPath || 'manifest.yaml' }) }}</p>
          <p class="hint full">{{ t("upload.requiredFieldsOnly") }}</p>

          <label class="field-item">
            <span class="field-name">{{ t("fields.name") }}</span>
            <input v-model="form.name" :placeholder="t('fields.name')" required />
          </label>

          <label class="field-item">
            <span class="field-name">{{ t("fields.appId") }}</span>
            <div class="input-with-action">
              <input v-model="form.appId" :placeholder="t('fields.appId')" required />
              <button
                type="button"
                class="input-action-btn"
                :title="t('upload.generateAppIdTooltip')"
                @click="generateAppId"
              >
                {{ t("upload.generateAppId") }}
              </button>
            </div>
            <span class="input-hint">{{ t("upload.appIdHint") }}</span>
          </label>

          <label class="field-item">
            <span class="field-name">{{ t("fields.version") }}</span>
            <input v-model="form.version" :placeholder="t('upload.versionPlaceholder')" required />
            <span class="input-hint">{{ t("upload.versionHint") }}</span>
          </label>

          <label class="field-item full">
            <span class="field-name">{{ t("fields.description") }}</span>
            <textarea v-model="form.description" class="full" :placeholder="t('fields.description')" rows="2" required />
          </label>

          <h2 class="full">{{ t("upload.treeTitle") }}</h2>
          <div class="full package-tree" v-if="packageEntries.length">
            <pre class="package-tree-pre">{{ packageTreeLines.join('\n') }}</pre>
          </div>
          <p class="hint full" v-else>{{ t("upload.treeEmpty") }}</p>
        </template>

        <button class="full" :disabled="submitting || parsingManifest || !parsedReady">
          {{ submitting ? t("upload.submitting") : t("upload.submit") }}
        </button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

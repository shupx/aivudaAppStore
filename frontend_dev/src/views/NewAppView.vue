<script setup>
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { useAppUpload } from "../composables/useAppUpload";

const router = useRouter();
const { t } = useI18n();
const { output, parsingManifest, form, sampleUrl, bindPackageZip, submitPackage } = useAppUpload(t);

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
      <h2>{{ t("upload.basic") }}</h2>
      <form class="grid3" @submit.prevent="submit">
        <input v-model="form.appId" :placeholder="t('fields.appId')" required />
        <input v-model="form.name" :placeholder="t('fields.name')" />
        <input v-model="form.version" :placeholder="t('fields.version')" required />

        <input v-model="form.entrypoint" class="full" :placeholder="t('fields.entrypoint')" required />
        <textarea v-model="form.description" class="full" :placeholder="t('fields.description')" rows="2" />

        <h2 class="full">{{ t("upload.requiredMaterials") }}</h2>
        <div class="file-row full">
          <span class="file-label">{{ t("upload.packageZip") }}</span>
          <input type="file" accept=".zip" @change="bindPackageZip" />
        </div>
        <p class="hint full" v-if="parsingManifest">{{ t("upload.parsing") }}</p>
        <p class="hint full">{{ t("upload.hintManifest") }}</p>
        <p class="hint full">{{ t("upload.hintEntrypoint") }}</p>
        <p class="hint full">{{ t("upload.hintConfig") }}</p>

        <h2 class="full">{{ t("upload.runHooks") }}</h2>
        <textarea v-model="form.argsText" class="full" :placeholder="t('fields.runArgs') + ' (' + t('common.jsonHint') + ') '" rows="2" />
        <input v-model="form.icon" :placeholder="t('fields.icon')" />
        <input v-model="form.preInstall" :placeholder="t('fields.preInstall')" />
        <input v-model="form.preUninstall" :placeholder="t('fields.preUninstall')" />
        <input v-model="form.updateThisVersion" class="full" :placeholder="t('fields.updateThisVersion')" />

        <h2 class="full">{{ t("upload.configExtra") }}</h2>
        <textarea v-model="form.defaultConfigText" class="full" :placeholder="t('fields.defaultConfig') + ' (' + t('common.jsonHint') + ') '" rows="4" />
        <textarea v-model="form.configSchemaText" class="full" :placeholder="t('fields.configSchema') + ' (' + t('common.jsonHint') + ') '" rows="4" />
        <textarea v-model="form.extraManifestText" class="full" :placeholder="t('fields.extraManifest') + ' (' + t('common.jsonHint') + ') '" rows="4" />

        <p class="hint full">
          <a class="link" :href="sampleUrl" target="_blank" rel="noreferrer">{{ t("upload.downloadSample") }}</a>
        </p>

        <button class="full">{{ t("upload.submit") }}</button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

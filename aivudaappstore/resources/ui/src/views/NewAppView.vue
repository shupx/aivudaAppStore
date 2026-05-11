<script setup>
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import ActionOutput from "../components/ActionOutput.vue";
import AppTopBar from "../components/AppTopBar.vue";
import { useAppUpload } from "../composables/useAppUpload";
import { Loader2, UploadCloud, FileText, Code } from "lucide-vue-next";

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
  <div class="bg-grid"></div>
  <section class="w-[min(1240px,96vw)] mx-auto my-6 flex flex-col gap-6">
    <AppTopBar :title="t('upload.title')" :subtitle="t('upload.subtitle')" />

    <section class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 mb-6 flex items-center gap-2">
        <UploadCloud class="w-6 h-6 text-emerald-600 dark:text-emerald-500" /> {{ t("upload.stepPackage") }}
      </h2>
      
      <form class="flex flex-col gap-8" @submit.prevent="submit">
        <div class="flex flex-col gap-2">
          <div class="relative border-2 border-dashed border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950/50 rounded-2xl p-8 hover:border-emerald-500/50 transition-colors flex flex-col items-center justify-center text-center group">
            <input type="file" accept=".zip,.tar,.tar.gz,.tgz,.gz" @change="bindPackageZip" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" />
            <div class="w-12 h-12 bg-white dark:bg-zinc-800 rounded-full flex items-center justify-center mb-3 group-hover:bg-emerald-50 dark:group-hover:bg-emerald-500/20 text-zinc-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 shadow-sm transition-colors">
              <UploadCloud class="w-6 h-6" />
            </div>
            <span class="text-zinc-800 dark:text-zinc-200 font-semibold text-lg">{{ t("upload.packageZip") }}</span>
            <span class="text-zinc-500 text-sm mt-1 max-w-sm">{{ t("upload.hintManifest") }}</span>
          </div>

          <div v-if="parsingManifest" class="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-sm mt-2 font-medium">
            <Loader2 class="w-4 h-4 animate-spin" /> {{ t("upload.parsing") }}
          </div>

          <p class="text-sm text-zinc-500 dark:text-zinc-400 mt-2">
            <a class="text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 font-medium transition-colors" :href="sampleUrl" target="_blank" rel="noreferrer">{{ t("upload.downloadSample") }}</a>
          </p>
        </div>

        <template v-if="parsedReady">
          <div class="border-t border-zinc-200 dark:border-zinc-800 pt-8 flex flex-col gap-6">
            <div>
              <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 flex items-center gap-2">
                <FileText class="w-6 h-6 text-emerald-600 dark:text-emerald-500" /> {{ t("upload.stepManifest") }}
              </h2>
              <p class="text-zinc-500 dark:text-zinc-400 text-sm mt-2 flex items-center gap-2">
                <Code class="w-4 h-4" /> {{ t("upload.manifestPath", { path: manifestFoundPath || 'manifest.yaml' }) }}
              </p>
              <p class="text-zinc-500 text-sm mt-1">{{ t("upload.requiredFieldsOnly") }}</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {{ t("fields.name") }}
                <input 
                  v-model="form.name" 
                  :placeholder="t('fields.name')" 
                  required 
                  class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm"
                />
              </label>

              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {{ t("fields.appId") }}
                <div class="flex gap-2">
                  <input 
                    v-model="form.appId" 
                    :placeholder="t('fields.appId')" 
                    required 
                    class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all flex-1 min-w-0 shadow-sm"
                  />
                  <button
                    type="button"
                    class="bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 px-4 py-3 rounded-xl transition-colors shrink-0 shadow-sm"
                    :title="t('upload.generateAppIdTooltip')"
                    @click="generateAppId"
                  >
                    {{ t("upload.generateAppId") }}
                  </button>
                </div>
                <span class="text-xs text-zinc-500">{{ t("upload.appIdHint") }}</span>
              </label>

              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {{ t("fields.version") }}
                <input 
                  v-model="form.version" 
                  :placeholder="t('upload.versionPlaceholder')" 
                  required 
                  class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm"
                />
                <span class="text-xs text-zinc-500">{{ t("upload.versionHint") }}</span>
              </label>

              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 md:col-span-2 lg:col-span-3">
                {{ t("fields.description") }}
                <textarea 
                  v-model="form.description" 
                  :placeholder="t('fields.description')" 
                  rows="2" 
                  required 
                  class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all resize-y shadow-sm"
                />
              </label>
            </div>

            <div class="mt-4">
              <h2 class="text-lg font-bold text-zinc-800 dark:text-zinc-200 m-0 mb-3">{{ t("upload.treeTitle") }}</h2>
              <div class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 max-h-[240px] overflow-auto shadow-inner" v-if="packageEntries.length">
                <pre class="m-0 font-mono text-sm text-zinc-700 dark:text-zinc-300">{{ packageTreeLines.join('\n') }}</pre>
              </div>
              <p class="text-zinc-500 text-sm" v-else>{{ t("upload.treeEmpty") }}</p>
            </div>
          </div>
        </template>

        <button 
          class="w-full mt-4 flex justify-center items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold py-4 px-6 rounded-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20" 
          :disabled="submitting || parsingManifest || !parsedReady"
        >
          <Loader2 v-if="submitting" class="w-5 h-5 animate-spin" />
          {{ submitting ? t("upload.submitting") : t("upload.submit") }}
        </button>
      </form>
    </section>

    <ActionOutput :output="output" />
  </section>
</template>

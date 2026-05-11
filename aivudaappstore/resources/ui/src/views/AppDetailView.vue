<script setup>
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppTopBar from "../components/AppTopBar.vue";
import { useAppDetailPage } from "../composables/useAppDetailPage";
import { formatSize, formatDate } from "../utils/format";
import { Loader2, UploadCloud, Edit3, Trash2, Download, EyeOff, RefreshCw, FileText, Code, ArrowUp, ArrowDown, Calendar, Clock } from "lucide-vue-next";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const appId = route.params.appId;

const {
  loading,
  operating,
  parsingManifest,
  uploadParsedReady,
  uploadPackageEntries,
  uploadPackageTreeLines,
  uploadManifestFoundPath,
  downloading,
  downloadProgress,
  showUploadDialog,
  uploadForm,
  uploadSubmitting,
  uploadManifestNameMismatch,
  showEditDialog,
  editForm,
  editSubmitting,
  editManifestNameMismatch,
  editHasPackageSelected,
  editParsedReady,
  editPackageEntries,
  editPackageTreeLines,
  editManifestFoundPath,
  confirmDialog,
  appInfo,
  versions,
  isOwnerOrAdmin,
  sortBy,
  sortAsc,
  sortedVersions,
  isVersionBusy,
  downloadVersion,
  openUploadDialog,
  submitUploadVersion,
  openEditDialog,
  submitEditVersion,
  runConfirm,
  confirmUnpublish,
  confirmDelete,
  handlePublish,
  onFileChange,
} = useAppDetailPage({
  appId,
  t,
  onAuthFail: () => router.push("/login"),
});
</script>

<template>
  <div class="bg-grid"></div>
  <section class="w-[min(1240px,96vw)] mx-auto my-6 flex flex-col gap-6">
    <AppTopBar :title="t('detail.title')" :subtitle="appId" />

    <section class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div>
        <h2 class="text-2xl font-extrabold text-zinc-900 dark:text-zinc-100 m-0 flex items-center gap-3">
          {{ appInfo?.name || t("detail.unknownApp") }}
        </h2>
        <p class="text-emerald-600 dark:text-emerald-500 font-mono text-sm mt-1 mb-2 bg-emerald-50 dark:bg-emerald-500/10 inline-block px-2 py-0.5 rounded">{{ appId }}</p>
        <p class="text-zinc-500 dark:text-zinc-400 text-sm max-w-2xl m-0" v-if="appInfo?.description">{{ appInfo.description }}</p>
      </div>
      <button 
        v-if="isOwnerOrAdmin" 
        @click="openUploadDialog" 
        :disabled="!!operating"
        class="shrink-0 flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold py-2.5 px-5 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-emerald-500/20"
      >
        <UploadCloud class="w-4 h-4" /> {{ t("detail.uploadVersion") }}
      </button>
    </section>

    <section class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-zinc-200 dark:border-zinc-700/60 shadow-xl shadow-zinc-200 dark:shadow-2xl dark:shadow-black/50 rounded-3xl p-6 md:p-8">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-zinc-200 dark:border-zinc-800/50 pb-4">
        <h3 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 m-0 flex items-center gap-2">
          {{ t("detail.versionList", { count: versions.length }) }}
          <span class="bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 text-xs py-1 px-2.5 rounded-full font-medium" v-if="!loading">{{ versions.length }}</span>
        </h3>
        
        <div class="flex items-center bg-zinc-50 dark:bg-zinc-950/50 rounded-xl p-1 border border-zinc-200 dark:border-zinc-800">
          <span class="text-xs text-zinc-500 px-2 font-medium hidden sm:inline">{{ t("detail.sort") }}</span>
          <button :class="sortBy === 'version' ? 'bg-white dark:bg-zinc-800 text-emerald-600 dark:text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'" class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors" @click="sortBy = 'version'">{{ t("detail.sortVersion") }}</button>
          <button :class="sortBy === 'published' ? 'bg-white dark:bg-zinc-800 text-emerald-600 dark:text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'" class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors" @click="sortBy = 'published'">{{ t("detail.sortPublished") }}</button>
          <button :class="sortBy === 'updated' ? 'bg-white dark:bg-zinc-800 text-emerald-600 dark:text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'" class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors" @click="sortBy = 'updated'">{{ t("detail.sortUpdated") }}</button>
          <button class="w-8 h-7 flex items-center justify-center text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors ml-1" @click="sortAsc = !sortAsc" :title="sortAsc ? t('detail.asc') : t('detail.desc')">
            <ArrowUp v-if="sortAsc" class="w-4 h-4" />
            <ArrowDown v-else class="w-4 h-4" />
          </button>
        </div>
      </div>

      <div v-if="loading" class="flex items-center justify-center py-12 text-emerald-600 dark:text-emerald-500 gap-2">
        <Loader2 class="w-6 h-6 animate-spin" /> {{ t("detail.loading") }}
      </div>
      <div v-else-if="versions.length === 0" class="text-center py-12 text-zinc-500">{{ t("detail.empty") }}</div>
      
      <div v-else class="flex flex-col gap-4">
        <article
          class="border rounded-2xl p-5 transition-colors relative overflow-hidden group"
          v-for="ver in sortedVersions"
          :key="ver.version"
          :class="ver.status === 'published' ? 'border-zinc-300 dark:border-zinc-700/50 bg-white dark:bg-zinc-800/40 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 shadow-md hover:shadow-lg' : 'border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-950/10 opacity-75'"
        >
          <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-3">
            <div class="flex items-center gap-3">
              <h4 class="text-lg font-bold text-zinc-900 dark:text-zinc-100 m-0">{{ ver.version }}</h4>
              <span class="text-xs font-semibold px-2 py-0.5 rounded-full border" :class="ver.status === 'published' ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20' : 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border-red-200 dark:border-red-500/20'">
                {{ ver.status === "published" ? t("detail.published") : t("detail.unpublished") }}
              </span>
            </div>
            <span class="text-sm font-mono text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-900 px-2 py-1 rounded">{{ formatSize(ver.artifact_size) }}</span>
          </div>

          <div class="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400 mb-4">
            <span v-if="ver.published_at" class="flex items-center gap-1.5"><Calendar class="w-3.5 h-3.5" /> {{ t("detail.publishedAt", { time: formatDate(ver.published_at) }) }}</span>
            <span class="flex items-center gap-1.5"><Clock class="w-3.5 h-3.5" /> {{ t("detail.updatedAt", { time: formatDate(ver.updated_at) }) }}</span>
          </div>
          
          <div v-if="ver.description" class="text-sm text-zinc-700 dark:text-zinc-300 mb-5 max-w-3xl leading-relaxed">{{ ver.description }}</div>

          <div v-if="isOwnerOrAdmin" class="flex flex-wrap gap-2 pt-4 border-t border-zinc-200 dark:border-zinc-800/50">
            <button
              v-if="ver.status === 'published'"
              @click="downloadVersion(ver.version)"
              :disabled="downloading || isVersionBusy(ver)"
              class="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500 hover:text-white dark:hover:text-zinc-950 transition-colors disabled:opacity-50"
            >
              <Loader2 v-if="downloading" class="w-4 h-4 animate-spin" />
              <Download v-else class="w-4 h-4" />
              <span v-if="downloading">{{ t("detail.downloadBusy", { progress: downloadProgress }) }}</span>
              <span v-else>{{ t("detail.download") }}</span>
            </button>
            <button @click="openEditDialog(ver)" :disabled="!!operating" class="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors disabled:opacity-50">
              <Edit3 class="w-4 h-4" /> {{ t("detail.edit") }}
            </button>
            <button
              v-if="ver.status === 'published'"
              @click="confirmUnpublish(ver)"
              :disabled="isVersionBusy(ver)"
              class="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-500 hover:bg-amber-500 hover:text-white dark:hover:text-zinc-950 transition-colors disabled:opacity-50"
            >
              <EyeOff class="w-4 h-4" /> {{ t("detail.unpublish") }}
            </button>
            <button
              v-else
              @click="handlePublish(ver)"
              :disabled="isVersionBusy(ver)"
              class="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500 hover:text-white dark:hover:text-zinc-950 transition-colors disabled:opacity-50"
            >
              <RefreshCw class="w-4 h-4" /> {{ t("detail.republish") }}
            </button>
            <button @click="confirmDelete(ver)" :disabled="isVersionBusy(ver)" class="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-lg bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-500 hover:bg-red-500 hover:text-white transition-colors disabled:opacity-50 ml-auto sm:ml-0">
              <Trash2 class="w-4 h-4" /> {{ t("detail.delete") }}
            </button>
          </div>

          <div v-else-if="ver.status === 'published'" class="flex gap-2 pt-4 border-t border-zinc-200 dark:border-zinc-800/50">
            <button
              @click="downloadVersion(ver.version)"
              :disabled="downloading"
              class="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500 hover:text-white dark:hover:text-zinc-950 transition-colors disabled:opacity-50"
            >
              <Loader2 v-if="downloading" class="w-4 h-4 animate-spin" />
              <Download v-else class="w-4 h-4" />
              {{ t("detail.download") }}
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>

  <!-- Upload Dialog -->
  <div v-if="showUploadDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 dark:bg-black/60 backdrop-blur-sm p-4" @click.self="showUploadDialog = false">
    <div class="w-[min(640px,100%)] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl p-6 max-h-[90vh] overflow-y-auto shadow-2xl dark:shadow-black/60">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">{{ t("detail.uploadDialogTitle") }}</h2>
      <form class="flex flex-col gap-6" @submit.prevent="submitUploadVersion">
        
        <div class="flex flex-col gap-2">
          <h3 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">{{ t("upload.stepPackage") }}</h3>
          <div class="flex items-center justify-between p-3 border border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-950/50">
            <span class="text-sm text-zinc-500 dark:text-zinc-400">{{ t("detail.packageLabel") }}</span>
            <input type="file" accept=".zip,.tar,.tar.gz,.tgz,.gz" @change="onFileChange('upload', $event)" class="text-sm text-zinc-700 dark:text-zinc-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-zinc-100 dark:file:bg-zinc-800 file:text-emerald-600 dark:file:text-emerald-400 hover:file:bg-zinc-200 dark:hover:file:bg-zinc-700 cursor-pointer" />
          </div>
          <div v-if="parsingManifest" class="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-sm mt-1 font-medium"><Loader2 class="w-4 h-4 animate-spin" /> {{ t("upload.parsing") }}</div>
          <p class="text-xs text-zinc-500">{{ t("upload.hintManifest") }}</p>
        </div>

        <template v-if="uploadParsedReady">
          <div class="border-t border-zinc-200 dark:border-zinc-800 pt-6 flex flex-col gap-4">
            <div>
              <h3 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">{{ t("upload.stepManifest") }}</h3>
              <p class="text-zinc-500 dark:text-zinc-400 text-sm flex items-center gap-2"><Code class="w-4 h-4" /> {{ t("upload.manifestPath", { path: uploadManifestFoundPath || 'manifest.yaml' }) }}</p>
              <p v-if="uploadManifestNameMismatch" class="mt-2 text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl px-3 py-2">
                {{ uploadManifestNameMismatch }}
              </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-400">
                {{ t("fields.name") }}
                <input v-model="uploadForm.manifest.name" :placeholder="t('fields.name')" readonly disabled class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2 text-zinc-400 dark:text-zinc-500 cursor-not-allowed" />
                <span class="text-xs text-zinc-500 dark:text-zinc-600">{{ t("detail.appNameLockedHint") }}</span>
              </label>
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-400">
                {{ t("fields.appId") }}
                <input v-model="uploadForm.manifest.appId" :placeholder="t('fields.appId')" readonly disabled class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2 text-zinc-400 dark:text-zinc-500 cursor-not-allowed" />
                <span class="text-xs text-zinc-500 dark:text-zinc-600">{{ t("detail.appIdLockedHint") }}</span>
              </label>
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 md:col-span-2">
                {{ t("fields.version") }}
                <input v-model="uploadForm.manifest.version" :placeholder="t('upload.versionPlaceholder')" required class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 outline-none shadow-sm" />
                <span class="text-xs text-emerald-600/70 dark:text-emerald-500/70">{{ t("upload.versionHint") }}</span>
              </label>
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 md:col-span-2">
                {{ t("fields.description") }}
                <textarea v-model="uploadForm.manifest.description" rows="2" required class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 outline-none resize-y shadow-sm" />
              </label>
            </div>

            <div class="mt-2">
              <h3 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">{{ t("upload.treeTitle") }}</h3>
              <div class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 max-h-[160px] overflow-auto shadow-inner" v-if="uploadPackageEntries.length">
                <pre class="m-0 font-mono text-xs text-zinc-500 dark:text-zinc-400">{{ uploadPackageTreeLines.join('\n') }}</pre>
              </div>
              <p class="text-sm text-zinc-500" v-else>{{ t("upload.treeEmpty") }}</p>
            </div>
          </div>
        </template>

        <div class="flex justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <button type="button" @click="showUploadDialog = false" :disabled="uploadSubmitting" class="px-5 py-2 rounded-xl font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50">{{ t("common.cancel") }}</button>
          <button type="submit" :disabled="uploadSubmitting || !uploadParsedReady" class="flex items-center gap-2 px-5 py-2 rounded-xl font-bold bg-emerald-500 text-zinc-950 hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-emerald-500/20">
            <Loader2 v-if="uploadSubmitting" class="w-4 h-4 animate-spin" />
            {{ uploadSubmitting ? t("detail.uploading") : t("detail.uploadNow") }}
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- Edit Dialog -->
  <div v-if="showEditDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 dark:bg-black/60 backdrop-blur-sm p-4" @click.self="showEditDialog = false">
    <div class="w-[min(640px,100%)] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl p-6 max-h-[90vh] overflow-y-auto shadow-2xl dark:shadow-black/60">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">{{ t("detail.editDialogTitle", { version: editForm.version }) }}</h2>
      <form class="flex flex-col gap-6" @submit.prevent="submitEditVersion">
        <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {{ t("detail.descriptionLabel") }}
          <textarea v-model="editForm.description" :placeholder="t('detail.descriptionLabel')" rows="3" class="bg-white dark:bg-zinc-950/50 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 outline-none resize-y shadow-sm" />
        </label>

        <div class="flex flex-col gap-2">
          <h3 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">{{ t("upload.stepPackage") }}</h3>
          <div class="flex items-center justify-between p-3 border border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-950/50 hover:border-emerald-500/50 transition-colors">
            <span class="text-sm text-zinc-500 dark:text-zinc-400">{{ t("detail.replacePackage") }}</span>
            <input type="file" accept=".zip,.tar,.tar.gz,.tgz,.gz" @change="onFileChange('edit', $event)" class="text-sm text-zinc-700 dark:text-zinc-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-zinc-100 dark:file:bg-zinc-800 file:text-emerald-600 dark:file:text-emerald-400 hover:file:bg-zinc-200 dark:hover:file:bg-zinc-700 cursor-pointer" />
          </div>
          <div v-if="parsingManifest" class="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-sm mt-1 font-medium"><Loader2 class="w-4 h-4 animate-spin" /> {{ t("upload.parsing") }}</div>
          <p class="text-xs text-zinc-500">{{ t("upload.hintManifest") }}</p>
        </div>

        <template v-if="editParsedReady">
          <div class="border-t border-zinc-200 dark:border-zinc-800 pt-6 flex flex-col gap-4">
            <div>
              <h3 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">{{ t("upload.stepManifest") }}</h3>
              <p class="text-zinc-500 dark:text-zinc-400 text-sm flex items-center gap-2"><Code class="w-4 h-4" /> {{ t("upload.manifestPath", { path: editManifestFoundPath || 'manifest.yaml' }) }}</p>
              <p v-if="editManifestNameMismatch" class="mt-2 text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl px-3 py-2">
                {{ editManifestNameMismatch }}
              </p>
              <p class="text-zinc-500 text-xs">{{ t("detail.editRequiredFieldsOnly") }}</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-400">
                {{ t("fields.name") }}
                <input v-model="editForm.manifest.name" :placeholder="t('fields.name')" readonly disabled class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2 text-zinc-400 dark:text-zinc-500 cursor-not-allowed" />
                <span class="text-xs text-zinc-500 dark:text-zinc-600">{{ t("detail.appNameLockedHint") }}</span>
              </label>
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-400">
                {{ t("fields.appId") }}
                <input v-model="editForm.manifest.appId" :placeholder="t('fields.appId')" readonly disabled class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2 text-zinc-400 dark:text-zinc-500 cursor-not-allowed" />
                <span class="text-xs text-zinc-500 dark:text-zinc-600">{{ t("detail.appIdLockedHint") }}</span>
              </label>
              <label class="flex flex-col gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-400 md:col-span-2">
                {{ t("fields.version") }}
                <input v-model="editForm.manifest.version" :placeholder="t('upload.versionPlaceholder')" readonly disabled class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl px-4 py-2 text-zinc-400 dark:text-zinc-500 cursor-not-allowed" />
                <span class="text-xs text-zinc-500 dark:text-zinc-600">{{ t("detail.versionLockedHint") }}</span>
              </label>
            </div>

            <div class="mt-2">
              <h3 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">{{ t("upload.treeTitle") }}</h3>
              <div class="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 max-h-[160px] overflow-auto shadow-inner" v-if="editPackageEntries.length">
                <pre class="m-0 font-mono text-xs text-zinc-500 dark:text-zinc-400">{{ editPackageTreeLines.join('\n') }}</pre>
              </div>
              <p class="text-sm text-zinc-500" v-else>{{ t("upload.treeEmpty") }}</p>
            </div>
          </div>
        </template>

        <div class="flex justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <button type="button" @click="showEditDialog = false" :disabled="editSubmitting" class="px-5 py-2 rounded-xl font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50">{{ t("common.cancel") }}</button>
          <button type="submit" :disabled="editSubmitting || (editHasPackageSelected && !editParsedReady)" class="flex items-center gap-2 px-5 py-2 rounded-xl font-bold bg-emerald-500 text-zinc-950 hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-emerald-500/20">
            <Loader2 v-if="editSubmitting" class="w-4 h-4 animate-spin" />
            {{ editSubmitting ? t("detail.saving") : t("common.save") }}
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- Confirm Dialog -->
  <div v-if="confirmDialog.show" class="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-900/40 dark:bg-black/60 backdrop-blur-sm p-4" @click.self="confirmDialog.show = false">
    <div class="w-[min(400px,100%)] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl p-6 shadow-2xl dark:shadow-black/60">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 mb-3">{{ confirmDialog.title }}</h2>
      <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-6">{{ confirmDialog.message }}</p>
      <div class="flex justify-end gap-3">
        <button @click="confirmDialog.show = false" :disabled="confirmDialog.submitting" class="px-4 py-2 rounded-xl font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50">{{ t("common.cancel") }}</button>
        <button class="flex items-center gap-2 px-4 py-2 rounded-xl font-bold bg-red-500 text-white hover:bg-red-400 transition-colors disabled:opacity-50 shadow-md shadow-red-500/20" @click="runConfirm" :disabled="confirmDialog.submitting">
          <Loader2 v-if="confirmDialog.submitting" class="w-4 h-4 animate-spin" />
          {{ confirmDialog.submitting ? t("common.processing") : t("common.confirm") }}
        </button>
      </div>
    </div>
  </div>
</template>

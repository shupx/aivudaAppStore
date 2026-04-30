<script setup>
import { onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { logout, session } from "../services/api";
import { setLocale } from "../i18n";
import { useDataPortability } from "../composables/useDataPortability";
import { formatSize } from "../utils/format";
import { ArrowLeft, ShoppingBag, User, LogOut, Upload, Download, FileUp, Languages, Loader2, Moon, Sun } from "lucide-vue-next";
import { useTheme } from "../composables/useTheme";

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  showBack: { type: Boolean, default: true },
});

const router = useRouter();
const { t, locale } = useI18n();
const { isDark, toggleTheme } = useTheme();
const open = ref(false);
let closeMenuTimer = null;
const {
  exporting,
  exportDialogOpen,
  exportLoading,
  exportApps,
  exportSelections,
  selectedExportAppIds,
  selectedExportTotalSize,
  canExport,
  importDialogOpen,
  inspecting,
  importing,
  selectedFile,
  inspectResult,
  importResult,
  errorMessage,
  resolutions,
  importSelections,
  selectedImportAppIds,
  selectedConflictApps,
  conflictCount,
  canApplyImport,
  openExportDialog,
  closeExportDialog,
  selectAllExportApps,
  clearExportApps,
  openImportDialog,
  closeImportDialog,
  downloadExport,
  inspectFile,
  selectAllImportApps,
  clearImportApps,
  setResolution,
  applyImport,
} = useDataPortability({
  t,
});

function go(path) {
  open.value = false;
  router.push(path);
}

function goBack() {
  open.value = false;
  if (window.history.length > 1) {
    router.back();
    return;
  }
  router.push("/store");
}

function doLogout() {
  open.value = false;
  logout();
  router.push("/login");
}

async function changeLocale(newLocale) {
  await setLocale(newLocale);
}

function closeMenu() {
  open.value = false;
}

function startImport() {
  open.value = false;
  openImportDialog();
}

function startExport() {
  open.value = false;
  openExportDialog();
}

function onImportFileChange(event) {
  const file = event.target.files?.[0] || null;
  inspectFile(file);
}

function openAccountMenu() {
  if (closeMenuTimer) {
    clearTimeout(closeMenuTimer);
    closeMenuTimer = null;
  }
  open.value = true;
}

function closeAccountMenu() {
  if (closeMenuTimer) {
    clearTimeout(closeMenuTimer);
  }
  closeMenuTimer = setTimeout(() => {
    open.value = false;
    closeMenuTimer = null;
  }, 180);
}

onBeforeUnmount(() => {
  if (closeMenuTimer) {
    clearTimeout(closeMenuTimer);
    closeMenuTimer = null;
  }
});
</script>

<template>
  <header class="relative z-20 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-4 border border-zinc-200 dark:border-zinc-700/60 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl rounded-2xl shadow-xl shadow-zinc-200 dark:shadow-black/40">
    <div>
      <h1 class="m-0 text-xl font-bold text-zinc-900 dark:text-zinc-100">{{ title }}</h1>
      <p class="m-0 mt-1 text-sm text-zinc-500 dark:text-zinc-400">{{ subtitle }}</p>
    </div>

    <div class="flex items-center gap-2 sm:ml-auto">
      <button v-if="showBack" class="w-10 h-10 flex items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800/50 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors" @click="goBack" :title="t('common.back')">
        <ArrowLeft class="w-5 h-5" />
      </button>

      <button class="w-10 h-10 flex items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800/50 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-500 dark:text-zinc-400 transition-colors" @click="toggleTheme" title="Toggle theme">
        <Sun v-if="isDark" class="w-5 h-5" />
        <Moon v-else class="w-5 h-5" />
      </button>

      <div class="flex items-center gap-1 p-1 rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900" :aria-label="t('common.language')">
        <Languages class="w-4 h-4 text-zinc-400 dark:text-zinc-500 ml-2" />
        <button
          type="button"
          class="px-3 py-1 text-xs font-semibold rounded-full transition-colors"
          :class="locale === 'zh-CN' ? 'bg-emerald-500 text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'"
          @click="changeLocale('zh-CN')"
        >
          {{ t("topbar.zhCN") }}
        </button>
        <button
          type="button"
          class="px-3 py-1 text-xs font-semibold rounded-full transition-colors"
          :class="locale === 'en-US' ? 'bg-emerald-500 text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'"
          @click="changeLocale('en-US')"
        >
          {{ t("topbar.enUS") }}
        </button>
      </div>

      <button class="w-10 h-10 flex items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800/50 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-emerald-600 dark:text-emerald-400 transition-colors" @click="go('/store')" :title="t('common.allApps')">
        <ShoppingBag class="w-5 h-5" />
      </button>

      <div class="relative z-30" @mouseenter="openAccountMenu" @mouseleave="closeAccountMenu">
        <button class="w-10 h-10 flex items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800/50 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors" :title="t('common.account')">
          <User class="w-5 h-5" />
        </button>
        <div v-if="open" class="absolute right-0 top-12 w-56 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/60 rounded-xl p-2 flex flex-col gap-1 shadow-2xl shadow-zinc-200 dark:shadow-black/50">
          <div class="px-3 py-2 text-sm text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800 mb-1 truncate">
            {{ session.user?.username }} <span class="opacity-50">({{ session.user?.role }})</span>
          </div>
          <button class="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors" @click="go('/me/new')">
            <Upload class="w-4 h-4" /> {{ t('common.uploadNewApp') }}
          </button>
          <button class="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors disabled:opacity-50" :disabled="exporting" @click="startExport">
            <Download class="w-4 h-4" /> {{ exporting ? t("dataPortability.exporting") : t("dataPortability.exportAction") }}
          </button>
          <button class="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors" @click="startImport">
            <FileUp class="w-4 h-4" /> {{ t("dataPortability.importAction") }}
          </button>
          <button class="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-700 dark:hover:text-red-300 transition-colors mt-1" @click="doLogout">
            <LogOut class="w-4 h-4" /> {{ t('common.logout') }}
          </button>
        </div>
      </div>
    </div>
  </header>

  <!-- Export Modal -->
  <div v-if="exportDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 dark:bg-black/60 backdrop-blur-sm" @click.self="closeExportDialog">
    <div class="w-[min(720px,94vw)] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl p-6 max-h-[86vh] overflow-y-auto shadow-2xl dark:shadow-black/60">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 mb-4">{{ t("dataPortability.exportTitle") }}</h2>
      <div class="flex flex-col gap-4">
        <p class="text-zinc-500 dark:text-zinc-400 text-sm" v-if="exportLoading">{{ t("dataPortability.exportLoading") }}</p>
        <p class="text-red-600 dark:text-red-400 text-sm bg-red-50 dark:bg-red-500/10 p-3 rounded-lg border border-red-200 dark:border-red-500/20" v-if="errorMessage">{{ errorMessage }}</p>

        <template v-if="!exportLoading && exportApps.length">
          <div class="flex gap-2">
            <button class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors" type="button" @click="selectAllExportApps">{{ t("dataPortability.selectAll") }}</button>
            <button class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors" type="button" @click="clearExportApps">{{ t("dataPortability.clearAll") }}</button>
          </div>

          <section class="flex flex-col gap-2">
            <label v-for="app in exportApps" :key="app.app_id" class="flex items-start gap-3 p-3 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-zinc-50 dark:bg-zinc-950/50 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors">
              <input v-model="exportSelections[app.app_id]" type="checkbox" class="mt-1 w-4 h-4 accent-emerald-500 bg-white dark:bg-zinc-800 border-zinc-300 dark:border-zinc-700 rounded" />
              <div>
                <strong class="text-zinc-800 dark:text-zinc-200 block">{{ app.name || app.app_id }}</strong>
                <p class="text-xs text-zinc-500 mt-1">
                  {{ app.app_id }} &middot; {{ t("dataPortability.versionCount", { count: app.version_count }) }} &middot;
                  {{ t("dataPortability.appSize", { size: formatSize(app.total_artifact_size) }) }}
                </p>
              </div>
            </label>
          </section>
          <div class="flex gap-4 text-sm text-zinc-500 dark:text-zinc-400">
            <p>{{ t("dataPortability.selectedApps", { count: selectedExportAppIds.length }) }}</p>
            <p>{{ t("dataPortability.selectedExportSize", { size: formatSize(selectedExportTotalSize) }) }}</p>
          </div>
        </template>

        <div class="flex gap-3 mt-4">
          <button 
            type="button" 
            class="px-5 py-2 rounded-xl font-bold bg-emerald-500 text-zinc-950 hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!canExport" 
            @click="downloadExport"
          >
            {{ exporting ? t("dataPortability.exporting") : t("dataPortability.exportNow") }}
          </button>
          <button 
            type="button" 
            class="px-5 py-2 rounded-xl font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
            :disabled="exportLoading || exporting" 
            @click="closeExportDialog"
          >
            {{ t("common.cancel") }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Import Modal -->
  <div v-if="importDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 dark:bg-black/60 backdrop-blur-sm" @click.self="closeImportDialog">
    <div class="w-[min(720px,94vw)] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/60 rounded-2xl p-6 max-h-[86vh] overflow-y-auto shadow-2xl dark:shadow-black/60">
      <h2 class="text-xl font-bold text-zinc-900 dark:text-zinc-100 mb-4">{{ t("dataPortability.importTitle") }}</h2>
      <div class="flex flex-col gap-5">
        
        <div class="flex items-center justify-between p-3 border border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-950/50">
          <span class="text-sm text-zinc-500 dark:text-zinc-400">{{ t("dataPortability.archiveLabel") }}</span>
          <input type="file" accept=".zip" class="text-sm text-zinc-700 dark:text-zinc-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-zinc-100 dark:file:bg-zinc-800 file:text-emerald-600 dark:file:text-emerald-400 hover:file:bg-zinc-200 dark:hover:file:bg-zinc-700 cursor-pointer" :disabled="inspecting || importing" @change="onImportFileChange" />
        </div>

        <p class="text-zinc-500 dark:text-zinc-400 text-sm" v-if="selectedFile">{{ t("dataPortability.selectedFile", { name: selectedFile.name }) }}</p>
        <p class="text-emerald-600 dark:text-emerald-400 text-sm flex items-center gap-2" v-if="inspecting">
          <Loader2 class="w-4 h-4 animate-spin" /> {{ t("dataPortability.inspecting") }}
        </p>
        <p class="text-red-600 dark:text-red-400 text-sm bg-red-50 dark:bg-red-500/10 p-3 rounded-lg border border-red-200 dark:border-red-500/20" v-if="errorMessage">{{ errorMessage }}</p>

        <section v-if="inspectResult" class="flex flex-col gap-3">
          <h3 class="font-bold text-zinc-800 dark:text-zinc-200">{{ t("dataPortability.summaryTitle") }}</h3>
          <div class="flex gap-4 text-sm text-zinc-500 dark:text-zinc-400">
            <span>{{ t("dataPortability.appCount", { count: inspectResult.summary.app_count }) }}</span>
            <span>{{ t("dataPortability.versionCount", { count: inspectResult.summary.version_count }) }}</span>
            <span>{{ t("dataPortability.artifactCount", { count: inspectResult.summary.artifact_count }) }}</span>
          </div>
          
          <div class="flex gap-2">
            <button class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors" type="button" @click="selectAllImportApps">{{ t("dataPortability.selectAll") }}</button>
            <button class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors" type="button" @click="clearImportApps">{{ t("dataPortability.clearAll") }}</button>
          </div>

          <section class="flex flex-col gap-2">
            <label v-for="app in inspectResult.apps" :key="app.app_id" class="flex items-start gap-3 p-3 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-zinc-50 dark:bg-zinc-950/50 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors">
              <input v-model="importSelections[app.app_id]" type="checkbox" :disabled="importing" class="mt-1 w-4 h-4 accent-emerald-500 bg-white dark:bg-zinc-800 border-zinc-300 dark:border-zinc-700 rounded" />
              <div>
                <strong class="text-zinc-800 dark:text-zinc-200 block">{{ app.name || app.app_id }}</strong>
                <p class="text-xs text-zinc-500 mt-1">{{ app.app_id }} &middot; {{ t("dataPortability.versionCount", { count: app.version_count }) }}</p>
              </div>
            </label>
          </section>
          
          <div class="flex gap-4 text-sm text-zinc-500 dark:text-zinc-400 mt-2">
            <p>{{ t("dataPortability.selectedApps", { count: selectedImportAppIds.length }) }}</p>
            <p v-if="conflictCount === 0" class="text-emerald-600 dark:text-emerald-400">{{ t("dataPortability.noConflicts") }}</p>
            <p v-else class="text-amber-600 dark:text-amber-400">{{ t("dataPortability.conflictHint", { count: conflictCount }) }}</p>
          </div>
        </section>

        <section v-if="conflictCount" class="flex flex-col gap-2">
          <article v-for="app in selectedConflictApps" :key="app.app_id" class="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 border border-amber-500/30 bg-amber-50 dark:bg-amber-500/5 rounded-xl gap-3">
            <div>
              <strong class="text-zinc-800 dark:text-zinc-200 block">{{ app.name || app.app_id }}</strong>
              <p class="text-xs text-zinc-500 mt-1">{{ app.app_id }} &middot; {{ t("dataPortability.versionCount", { count: app.version_count }) }}</p>
            </div>
            <select :value="resolutions[app.app_id]" :disabled="importing" @change="setResolution(app.app_id, $event.target.value)" class="w-full sm:w-auto bg-white dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 focus:ring-2 focus:ring-emerald-500 outline-none shadow-sm">
              <option value="skip">{{ t("dataPortability.skip") }}</option>
              <option value="overwrite">{{ t("dataPortability.overwrite") }}</option>
            </select>
          </article>
        </section>

        <section v-if="importResult" class="flex flex-col gap-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-4 rounded-xl">
          <h3 class="font-bold text-zinc-800 dark:text-zinc-200 mb-2">{{ t("dataPortability.resultTitle") }}</h3>
          <p class="text-sm text-emerald-600 dark:text-emerald-400">{{ t("dataPortability.importedApps", { count: importResult.imported_apps.length }) }}</p>
          <p class="text-sm text-amber-600 dark:text-amber-400">{{ t("dataPortability.overwrittenApps", { count: importResult.overwritten_apps.length }) }}</p>
          <p class="text-sm text-zinc-500 dark:text-zinc-400">{{ t("dataPortability.skippedApps", { count: importResult.skipped_apps.length }) }}</p>
          <p class="text-sm text-red-600 dark:text-red-400" v-if="importResult.failed_apps.length">{{ t("dataPortability.failedApps", { count: importResult.failed_apps.length }) }}</p>
          <pre v-if="importResult.messages.length" class="mt-2 p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs text-zinc-500 dark:text-zinc-400 overflow-auto max-h-40 whitespace-pre-wrap shadow-sm">{{ importResult.messages.join('\n') }}</pre>
        </section>

        <div class="flex gap-3 mt-2">
          <button 
            type="button" 
            class="px-5 py-2 rounded-xl font-bold bg-emerald-500 text-zinc-950 hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
            :disabled="!canApplyImport" 
            @click="applyImport"
          >
            <Loader2 v-if="importing" class="w-4 h-4 animate-spin" />
            {{ importing ? t("dataPortability.importing") : t("dataPortability.applyImport") }}
          </button>
          <button 
            type="button" 
            class="px-5 py-2 rounded-xl font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
            :disabled="inspecting || importing" 
            @click="closeImportDialog"
          >
            {{ t("common.cancel") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { logout, session } from "../services/api";
import shoppingBagIcon from "../assets/icons/shopping-bag.svg";
import { setLocale } from "../i18n";
import { useDataPortability } from "../composables/useDataPortability";
import { formatSize } from "../utils/format";

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  showBack: { type: Boolean, default: true },
});

const router = useRouter();
const { t, locale } = useI18n();
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

async function changeLocale(locale) {
  await setLocale(locale);
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
  <header class="topbar card">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>

    <div class="topbar-actions">
      <button v-if="showBack" class="icon-btn" @click="goBack" :title="t('common.back')">←</button>
      <div class="lang-switch" :aria-label="t('common.language')">
        <span class="lang-label">{{ t("common.language") }}</span>
        <button
          type="button"
          class="lang-btn"
          :class="{ active: locale === 'zh-CN' }"
          @click="changeLocale('zh-CN')"
        >
          {{ t("topbar.zhCN") }}
        </button>
        <button
          type="button"
          class="lang-btn"
          :class="{ active: locale === 'en-US' }"
          @click="changeLocale('en-US')"
        >
          {{ t("topbar.enUS") }}
        </button>
      </div>
    </div>

    <button class="icon-btn store-bag-btn" @click="go('/store')" :title="t('common.allApps')">
      <img :src="shoppingBagIcon" :alt="t('common.allApps')" width="22" height="22" />
    </button>

    <div class="account-wrap" @mouseenter="openAccountMenu" @mouseleave="closeAccountMenu">
      <button class="icon-btn" :title="t('common.account')">👤</button>
      <div v-if="open" class="account-menu">
        <div class="account-user">{{ session.user?.username }} ({{ session.user?.role }})</div>
        <button @click="go('/me/new')">{{ t('common.uploadNewApp') }}</button>
        <button :disabled="exporting" @click="startExport">
          {{ exporting ? t("dataPortability.exporting") : t("dataPortability.exportAction") }}
        </button>
        <button @click="startImport">{{ t("dataPortability.importAction") }}</button>
        <button class="danger" @click="doLogout">{{ t('common.logout') }}</button>
      </div>
    </div>
  </header>

  <div v-if="exportDialogOpen" class="modal-overlay" @click.self="closeExportDialog">
    <div class="modal-card data-import-card card">
      <h2>{{ t("dataPortability.exportTitle") }}</h2>
      <div class="stack">
        <p class="hint" v-if="exportLoading">{{ t("dataPortability.exportLoading") }}</p>
        <p class="hint import-error" v-if="errorMessage">{{ errorMessage }}</p>

        <template v-if="!exportLoading && exportApps.length">
          <div class="btnrow">
            <button type="button" @click="selectAllExportApps">{{ t("dataPortability.selectAll") }}</button>
            <button type="button" @click="clearExportApps">{{ t("dataPortability.clearAll") }}</button>
          </div>

          <section class="conflict-list">
            <label v-for="app in exportApps" :key="app.app_id" class="check-item">
              <input v-model="exportSelections[app.app_id]" type="checkbox" />
              <div>
                <strong>{{ app.name || app.app_id }}</strong>
                <p class="sub">
                  {{ app.app_id }} · {{ t("dataPortability.versionCount", { count: app.version_count }) }} ·
                  {{ t("dataPortability.appSize", { size: formatSize(app.total_artifact_size) }) }}
                </p>
              </div>
            </label>
          </section>
          <p class="hint">{{ t("dataPortability.selectedApps", { count: selectedExportAppIds.length }) }}</p>
          <p class="hint">{{ t("dataPortability.selectedExportSize", { size: formatSize(selectedExportTotalSize) }) }}</p>
        </template>

        <div class="btnrow">
          <button type="button" :disabled="!canExport" @click="downloadExport">
            {{ exporting ? t("dataPortability.exporting") : t("dataPortability.exportNow") }}
          </button>
          <button type="button" :disabled="exportLoading || exporting" @click="closeExportDialog">{{ t("common.cancel") }}</button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="importDialogOpen" class="modal-overlay" @click.self="closeImportDialog">
    <div class="modal-card data-import-card card">
      <h2>{{ t("dataPortability.importTitle") }}</h2>
      <div class="stack">
        <div class="file-row">
          <span class="file-label">{{ t("dataPortability.archiveLabel") }}</span>
          <input type="file" accept=".zip" :disabled="inspecting || importing" @change="onImportFileChange" />
        </div>

        <p class="hint" v-if="selectedFile">{{ t("dataPortability.selectedFile", { name: selectedFile.name }) }}</p>
        <p class="hint" v-if="inspecting">{{ t("dataPortability.inspecting") }}</p>
        <p class="hint import-error" v-if="errorMessage">{{ errorMessage }}</p>

        <section v-if="inspectResult" class="import-summary">
          <h3>{{ t("dataPortability.summaryTitle") }}</h3>
          <div class="import-stats">
            <span>{{ t("dataPortability.appCount", { count: inspectResult.summary.app_count }) }}</span>
            <span>{{ t("dataPortability.versionCount", { count: inspectResult.summary.version_count }) }}</span>
            <span>{{ t("dataPortability.artifactCount", { count: inspectResult.summary.artifact_count }) }}</span>
          </div>
          <div class="btnrow">
            <button type="button" @click="selectAllImportApps">{{ t("dataPortability.selectAll") }}</button>
            <button type="button" @click="clearImportApps">{{ t("dataPortability.clearAll") }}</button>
          </div>
          <section class="conflict-list">
            <label v-for="app in inspectResult.apps" :key="app.app_id" class="check-item">
              <input v-model="importSelections[app.app_id]" type="checkbox" :disabled="importing" />
              <div>
                <strong>{{ app.name || app.app_id }}</strong>
                <p class="sub">{{ app.app_id }} · {{ t("dataPortability.versionCount", { count: app.version_count }) }}</p>
              </div>
            </label>
          </section>
          <p class="hint">{{ t("dataPortability.selectedApps", { count: selectedImportAppIds.length }) }}</p>
          <p class="hint" v-if="conflictCount === 0">{{ t("dataPortability.noConflicts") }}</p>
          <p class="hint" v-else>{{ t("dataPortability.conflictHint", { count: conflictCount }) }}</p>
        </section>

        <section v-if="conflictCount" class="conflict-list">
          <article v-for="app in selectedConflictApps" :key="app.app_id" class="conflict-item">
            <div>
              <strong>{{ app.name || app.app_id }}</strong>
              <p class="sub">{{ app.app_id }} · {{ t("dataPortability.versionCount", { count: app.version_count }) }}</p>
            </div>
            <select :value="resolutions[app.app_id]" :disabled="importing" @change="setResolution(app.app_id, $event.target.value)">
              <option value="skip">{{ t("dataPortability.skip") }}</option>
              <option value="overwrite">{{ t("dataPortability.overwrite") }}</option>
            </select>
          </article>
        </section>

        <section v-if="importResult" class="import-result">
          <h3>{{ t("dataPortability.resultTitle") }}</h3>
          <p>{{ t("dataPortability.importedApps", { count: importResult.imported_apps.length }) }}</p>
          <p>{{ t("dataPortability.overwrittenApps", { count: importResult.overwritten_apps.length }) }}</p>
          <p>{{ t("dataPortability.skippedApps", { count: importResult.skipped_apps.length }) }}</p>
          <p v-if="importResult.failed_apps.length">{{ t("dataPortability.failedApps", { count: importResult.failed_apps.length }) }}</p>
          <pre v-if="importResult.messages.length">{{ importResult.messages.join('\n') }}</pre>
        </section>

        <div class="btnrow">
          <button type="button" :disabled="!canApplyImport" @click="applyImport">
            {{ importing ? t("dataPortability.importing") : t("dataPortability.applyImport") }}
          </button>
          <button type="button" :disabled="inspecting || importing" @click="closeImportDialog">{{ t("common.cancel") }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

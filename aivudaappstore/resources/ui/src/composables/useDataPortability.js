import { computed, reactive, ref } from "vue";
import {
  applyDataImport,
  downloadDataArchive,
  exportDataArchive,
  inspectDataImport,
} from "../services/api";

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "aivudaAppStore-data.zip";
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function defaultResult() {
  return {
    imported_apps: [],
    overwritten_apps: [],
    skipped_apps: [],
    failed_apps: [],
    messages: [],
  };
}

export function useDataPortability({ t } = {}) {
  const exporting = ref(false);
  const exportDialogOpen = ref(false);
  const exportLoading = ref(false);
  const exportApps = ref([]);
  const exportSelections = reactive({});

  const importDialogOpen = ref(false);
  const inspecting = ref(false);
  const importing = ref(false);
  const selectedFile = ref(null);
  const inspectResult = ref(null);
  const importResult = ref(null);
  const errorMessage = ref("");
  const resolutions = reactive({});
  const importSelections = reactive({});

  const selectedExportAppIds = computed(() =>
    exportApps.value.filter((app) => exportSelections[app.app_id]).map((app) => app.app_id)
  );
  const selectedExportTotalSize = computed(() =>
    exportApps.value
      .filter((app) => exportSelections[app.app_id])
      .reduce((total, app) => total + Number(app.total_artifact_size || 0), 0)
  );
  const selectedImportAppIds = computed(() =>
    (inspectResult.value?.apps || []).filter((app) => importSelections[app.app_id]).map((app) => app.app_id)
  );
  const selectedConflictApps = computed(() =>
    (inspectResult.value?.conflicts || []).filter((app) => importSelections[app.app_id])
  );
  const conflictCount = computed(() => selectedConflictApps.value.length);
  const canExport = computed(() => selectedExportAppIds.value.length > 0 && !exporting.value && !exportLoading.value);
  const canApplyImport = computed(() => {
    if (!selectedFile.value || !inspectResult.value || importing.value) return false;
    if (selectedImportAppIds.value.length === 0) return false;
    return selectedConflictApps.value.every((app) => !!resolutions[app.app_id]);
  });

  function resetExportState() {
    exportApps.value = [];
    errorMessage.value = "";
    Object.keys(exportSelections).forEach((key) => delete exportSelections[key]);
  }

  function resetImportState() {
    selectedFile.value = null;
    inspectResult.value = null;
    importResult.value = null;
    errorMessage.value = "";
    Object.keys(resolutions).forEach((key) => delete resolutions[key]);
    Object.keys(importSelections).forEach((key) => delete importSelections[key]);
  }

  async function openExportDialog() {
    resetExportState();
    exportDialogOpen.value = true;
    exportLoading.value = true;
    try {
      const data = await exportDataArchive();
      exportApps.value = data.apps || [];
      exportApps.value.forEach((app) => {
        exportSelections[app.app_id] = true;
      });
    } catch (err) {
      errorMessage.value = err?.message || (t ? t("dataPortability.exportListFailed") : "Export list failed");
    } finally {
      exportLoading.value = false;
    }
  }

  function closeExportDialog() {
    if (exportLoading.value || exporting.value) return;
    exportDialogOpen.value = false;
    resetExportState();
  }

  function selectAllExportApps() {
    exportApps.value.forEach((app) => {
      exportSelections[app.app_id] = true;
    });
  }

  function clearExportApps() {
    exportApps.value.forEach((app) => {
      exportSelections[app.app_id] = false;
    });
  }

  async function downloadExport() {
    if (!canExport.value) return;
    exporting.value = true;
    errorMessage.value = "";
    try {
      const { blob, filename } = await downloadDataArchive(selectedExportAppIds.value);
      triggerBlobDownload(blob, filename);
    } catch (err) {
      errorMessage.value = err?.message || (t ? t("dataPortability.exportFailed") : "Export failed");
    } finally {
      exporting.value = false;
    }
  }

  function openImportDialog() {
    resetImportState();
    importDialogOpen.value = true;
  }

  function closeImportDialog() {
    if (inspecting.value || importing.value) return;
    importDialogOpen.value = false;
    resetImportState();
  }

  async function inspectFile(file) {
    resetImportState();
    selectedFile.value = file || null;
    if (!selectedFile.value) return;

    inspecting.value = true;
    try {
      const data = await inspectDataImport(selectedFile.value);
      inspectResult.value = data;
      (data.apps || []).forEach((app) => {
        importSelections[app.app_id] = true;
      });
      (data.conflicts || []).forEach((app) => {
        resolutions[app.app_id] = "skip";
      });
    } catch (err) {
      errorMessage.value = err?.message || (t ? t("dataPortability.inspectFailed") : "Inspect failed");
    } finally {
      inspecting.value = false;
    }
  }

  function selectAllImportApps() {
    (inspectResult.value?.apps || []).forEach((app) => {
      importSelections[app.app_id] = true;
    });
  }

  function clearImportApps() {
    (inspectResult.value?.apps || []).forEach((app) => {
      importSelections[app.app_id] = false;
    });
  }

  function setResolution(appId, decision) {
    resolutions[appId] = decision;
  }

  async function applyImport() {
    if (!canApplyImport.value) return;
    importing.value = true;
    importResult.value = null;
    errorMessage.value = "";
    try {
      importResult.value = await applyDataImport(
        selectedFile.value,
        { ...resolutions },
        selectedImportAppIds.value
      );
    } catch (err) {
      importResult.value = defaultResult();
      errorMessage.value = err?.message || (t ? t("dataPortability.importFailed") : "Import failed");
    } finally {
      importing.value = false;
    }
  }

  return {
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
    downloadExport,
    openImportDialog,
    closeImportDialog,
    inspectFile,
    selectAllImportApps,
    clearImportApps,
    setResolution,
    applyImport,
  };
}

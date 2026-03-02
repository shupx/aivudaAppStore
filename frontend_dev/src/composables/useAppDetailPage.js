import { computed, onMounted, ref } from "vue";
import { useVersionManagement } from "./useVersionManagement";
import { useAppDownload } from "./useAppDownload";
import { useVersionSort } from "./useVersionSort";
import { applyNormalizedManifest, buildRequiredManifestFromForm, createManifestForm } from "../utils/manifest";
import { session } from "../services/api";

function sortPackageEntriesByDirectory(entries) {
  const list = Array.isArray(entries) ? entries : [];
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

  return [...list].sort((left, right) => {
    const leftPath = String(left?.path || "").replace(/\/+$/g, "");
    const rightPath = String(right?.path || "").replace(/\/+$/g, "");

    const leftParts = leftPath ? leftPath.split("/") : [];
    const rightParts = rightPath ? rightPath.split("/") : [];
    const minLen = Math.min(leftParts.length, rightParts.length);

    for (let index = 0; index < minLen; index += 1) {
      const segmentCmp = collator.compare(leftParts[index], rightParts[index]);
      if (segmentCmp !== 0) return segmentCmp;
    }

    const leftType = left?.type === "dir" ? 0 : 1;
    const rightType = right?.type === "dir" ? 0 : 1;
    if (leftType !== rightType) return leftType - rightType;

    return leftParts.length - rightParts.length;
  });
}

function buildUbuntuTreeLines(entries, truncatedLabel) {
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
  const root = { type: "dir", name: ".", children: new Map(), truncated: false };

  const list = Array.isArray(entries) ? entries : [];
  for (const entry of list) {
    const rawPath = String(entry?.path || "").replace(/\/+$/g, "");
    if (!rawPath) continue;

    const parts = rawPath.split("/").filter(Boolean);
    if (!parts.length) continue;

    const entryType = entry?.type === "dir" ? "dir" : "file";
    let current = root;

    for (let index = 0; index < parts.length; index += 1) {
      const name = parts[index];
      const isLeaf = index === parts.length - 1;
      const nodeType = isLeaf ? entryType : "dir";

      if (!current.children.has(name)) {
        current.children.set(name, { type: nodeType, name, children: new Map(), truncated: false });
      }

      const next = current.children.get(name);
      if (nodeType === "dir") {
        next.type = "dir";
      }
      if (isLeaf && entry?.truncated) {
        next.truncated = true;
      }
      current = next;
    }
  }

  const lines = ["."];

  function walk(node, prefix) {
    const children = Array.from(node.children.values()).sort((left, right) => {
      const leftType = left.type === "dir" ? 0 : 1;
      const rightType = right.type === "dir" ? 0 : 1;
      if (leftType !== rightType) return leftType - rightType;
      return collator.compare(left.name, right.name);
    });

    children.forEach((child, index) => {
      const isLast = index === children.length - 1;
      const branch = isLast ? "└── " : "├── ";
      const suffix = child.type === "dir" ? "/" : "";
      const truncated = child.truncated ? ` ${truncatedLabel}` : "";
      lines.push(`${prefix}${branch}${child.name}${suffix}${truncated}`);

      if (child.type === "dir" && child.children.size > 0) {
        const nextPrefix = `${prefix}${isLast ? "    " : "│   "}`;
        walk(child, nextPrefix);
      }
    });
  }

  walk(root, "");
  return lines;
}

export function useAppDetailPage({ appId, t, onAuthFail }) {
  const {
    loading,
    detail,
    operating,
    parsingManifest,
    uploadParsedReady,
    uploadPackageEntries,
    uploadPackageTreeLines,
    uploadManifestFoundPath,
    uploadParsedManifestBase,
    load,
    resetUploadParseState,
    parseManifestFromPackage,
    parseUploadPackage,
    doUploadVersion,
    doModifyVersion,
    doUnpublish,
    doPublish,
    doDelete,
  } = useVersionManagement(appId);

  const { downloading, progress: downloadProgress, downloadAppPackage } = useAppDownload();

  const showUploadDialog = ref(false);
  const uploadForm = ref({
    manifest: createManifestForm({ appId }),
  });
  const uploadFile = ref(null);
  const uploadSubmitting = ref(false);

  const showEditDialog = ref(false);
  const editForm = ref({
    version: "",
    description: "",
    manifest: createManifestForm({ appId }),
  });
  const editFile = ref(null);
  const editSubmitting = ref(false);
  const editParsedReady = ref(false);
  const editPackageEntries = ref([]);
  const editPackageTreeLines = ref([]);
  const editManifestFoundPath = ref("");
  const editParsedManifestBase = ref({});

  const confirmDialog = ref({ show: false, title: "", message: "", submitting: false, action: null });
  const editHasPackageSelected = computed(() => Boolean(editFile.value));

  const appInfo = computed(() => detail.value?.app || null);
  const versions = computed(() => detail.value?.versions || []);
  const isOwnerOrAdmin = computed(() => {
    if (!appInfo.value || !session.user) return false;
    return session.user.role === "admin" || session.user.id === appInfo.value.owner_user_id;
  });

  const { sortBy, sortAsc, sortedVersions } = useVersionSort(versions);

  function isVersionBusy(ver) {
    return operating.value.endsWith(`:${ver.version}`);
  }

  async function downloadVersion(version) {
    try {
      await downloadAppPackage(appId, version);
    } catch (err) {
      window.alert(String(err));
    }
  }

  function openUploadDialog() {
    const fixedName = appInfo.value?.name || "";
    uploadForm.value = {
      manifest: createManifestForm({ appId, name: fixedName }),
    };
    uploadFile.value = null;
    resetUploadParseState();
    showUploadDialog.value = true;
  }

  function resetEditParseState() {
    editParsedReady.value = false;
    editPackageEntries.value = [];
    editPackageTreeLines.value = [];
    editManifestFoundPath.value = "";
    editParsedManifestBase.value = {};
  }

  async function parseEditPackage(file) {
    const data = await parseManifestFromPackage(file);
    editPackageEntries.value = sortPackageEntriesByDirectory(data?.package_entries);
    editPackageTreeLines.value = buildUbuntuTreeLines(editPackageEntries.value, t("upload.treeTruncated"));
    editManifestFoundPath.value = data?.found_path || "";
    editParsedManifestBase.value =
      data?.manifest && typeof data.manifest === "object"
        ? data.manifest
        : data?.normalized_manifest && typeof data.normalized_manifest === "object"
          ? data.normalized_manifest
          : {};
    editParsedReady.value = true;
    return data;
  }

  async function submitUploadVersion() {
    if (!uploadFile.value) {
      window.alert(t("errors.mustChoosePackage"));
      return;
    }
    if (!uploadParsedReady.value) {
      window.alert(t("upload.parseFirst"));
      return;
    }
    uploadSubmitting.value = true;
    try {
      const manifest = buildRequiredManifestFromForm(uploadForm.value.manifest, uploadParsedManifestBase.value, t);
      manifest.app_id = appId;
      manifest.name = appInfo.value?.name || manifest.name;
      await doUploadVersion(manifest, uploadFile.value);
      showUploadDialog.value = false;
    } catch (err) {
      window.alert(String(err));
    } finally {
      uploadSubmitting.value = false;
    }
  }

  function openEditDialog(ver) {
    const fixedName = appInfo.value?.name || "";
    editForm.value = {
      version: ver.version,
      description: ver.description || "",
      manifest: createManifestForm({
        appId,
        name: fixedName,
        version: ver.version,
        description: ver.description || "",
      }),
    };
    editFile.value = null;
    resetEditParseState();
    showEditDialog.value = true;
  }

  async function submitEditVersion() {
    if (editFile.value && !editParsedReady.value) {
      window.alert(t("upload.parseFirst"));
      return;
    }
    editSubmitting.value = true;
    try {
      let manifest = null;
      if (editFile.value) {
        manifest = buildRequiredManifestFromForm(editForm.value.manifest, editParsedManifestBase.value, t);
        manifest.app_id = appId;
        manifest.name = appInfo.value?.name || manifest.name;
        manifest.version = editForm.value.version;
        manifest.description = editForm.value.description.trim() || manifest.description;
      }
      await doModifyVersion(editForm.value.version, editForm.value.description, editFile.value, manifest);
      showEditDialog.value = false;
    } catch (err) {
      window.alert(String(err));
    } finally {
      editSubmitting.value = false;
    }
  }

  function openConfirm(title, message, action) {
    confirmDialog.value = { show: true, title, message, submitting: false, action };
  }

  async function runConfirm() {
    confirmDialog.value.submitting = true;
    try {
      await confirmDialog.value.action();
      confirmDialog.value.show = false;
    } catch (err) {
      window.alert(String(err));
    } finally {
      confirmDialog.value.submitting = false;
    }
  }

  function confirmUnpublish(ver) {
    openConfirm(
      t("detail.confirmUnpublishTitle"),
      t("detail.confirmUnpublishMessage", { version: ver.version }),
      () => doUnpublish(ver.version)
    );
  }

  function confirmDelete(ver) {
    openConfirm(
      t("detail.confirmDeleteTitle"),
      t("detail.confirmDeleteMessage", { version: ver.version }),
      () => doDelete(ver.version)
    );
  }

  async function handlePublish(ver) {
    try {
      await doPublish(ver.version);
    } catch (err) {
      window.alert(String(err));
    }
  }

  async function onFileChange(target, event) {
    const file = event.target.files?.[0] || null;
    if (target === "upload") {
      uploadFile.value = file;
      if (!file) {
        resetUploadParseState();
        return;
      }
      const data = await parseUploadPackage(file, { truncatedLabel: t("upload.treeTruncated") });
      if (data?.normalized_manifest) {
        applyNormalizedManifest(uploadForm.value.manifest, data.normalized_manifest);
      }
      uploadForm.value.manifest.appId = appId;
      uploadForm.value.manifest.name = appInfo.value?.name || uploadForm.value.manifest.name;
      return;
    }

    if (target === "edit") {
      editFile.value = file;
      if (!file) {
        resetEditParseState();
        return;
      }
      const data = await parseEditPackage(file);
      if (data?.normalized_manifest) {
        applyNormalizedManifest(editForm.value.manifest, data.normalized_manifest);
      }
      editForm.value.manifest.appId = appId;
      editForm.value.manifest.name = appInfo.value?.name || editForm.value.manifest.name;
      editForm.value.manifest.version = editForm.value.version;
      editForm.value.manifest.description = editForm.value.description;
    }
  }

  onMounted(async () => {
    const result = await load();
    if (result === null && !detail.value) {
      if (onAuthFail) onAuthFail();
    }
  });

  return {
    loading,
    detail,
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
    showEditDialog,
    editForm,
    editSubmitting,
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
  };
}

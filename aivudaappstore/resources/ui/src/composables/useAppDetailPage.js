import { computed, onMounted, ref } from "vue";
import { useVersionManagement } from "./useVersionManagement";
import { useAppDownload } from "./useAppDownload";
import { useVersionSort } from "./useVersionSort";
import { applyNormalizedManifest, buildRequiredManifestFromForm, createManifestForm } from "../utils/manifest";
import { buildUbuntuTreeLines, sortPackageEntriesByDirectory } from "../utils/packageTree";
import { addAppMember, fetchUsers, removeAppMember, session, transferAppAdmin } from "../services/api";

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
  const uploadManifestNameMismatch = ref("");

  const showEditDialog = ref(false);
  const editForm = ref({
    version: "",
    description: "",
    manifest: createManifestForm({ appId }),
  });
  const editFile = ref(null);
  const editSubmitting = ref(false);
  const editManifestNameMismatch = ref("");
  const editParsedReady = ref(false);
  const editPackageEntries = ref([]);
  const editPackageTreeLines = ref([]);
  const editManifestFoundPath = ref("");
  const editParsedManifestBase = ref({});

  const confirmDialog = ref({ show: false, title: "", message: "", submitting: false, action: null });
  const editHasPackageSelected = computed(() => Boolean(editFile.value));

  const appInfo = computed(() => detail.value?.app || null);
  const appPermissions = computed(() => detail.value?.permissions || {});
  const members = computed(() => detail.value?.members || []);
  const versions = computed(() => detail.value?.versions || []);
  const isOwnerOrAdmin = computed(() => !!appPermissions.value?.can_edit_versions);
  const canManageMembers = computed(() => !!appPermissions.value?.can_manage_members);
  const memberUsername = ref("");
  const memberBusy = ref(false);
  const memberMenuUserId = ref(null);
  const showUserDropdown = ref(false);
  const availableUsers = ref([]);
  const loadingUsers = ref(false);
  const selectableUsers = computed(() => {
    const currentMembers = new Set(members.value.map((member) => member.username));
    const keyword = memberUsername.value.trim().toLowerCase();
    return availableUsers.value.filter((user) => {
      if (currentMembers.has(user.username)) return false;
      if (!keyword) return true;
      return user.username.toLowerCase().includes(keyword);
    });
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
    uploadManifestNameMismatch.value = "";
    resetUploadParseState();
    showUploadDialog.value = true;
  }

  function resetEditParseState() {
    editParsedReady.value = false;
    editPackageEntries.value = [];
    editPackageTreeLines.value = [];
    editManifestFoundPath.value = "";
    editParsedManifestBase.value = {};
    editManifestNameMismatch.value = "";
  }

  function buildManifestNameMismatchMessage(parsedManifest) {
    const expectedName = (appInfo.value?.name || "").trim();
    const packageName = String(parsedManifest?.name || "").trim();
    if (!expectedName || !packageName || packageName === expectedName) {
      return "";
    }
    return t("detail.manifestNameMismatch", {
      packageName,
      expectedName,
    });
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

  async function addDeveloper() {
    if (!memberUsername.value.trim()) return;
    memberBusy.value = true;
    try {
      await addAppMember(appId, memberUsername.value.trim());
      memberUsername.value = "";
      await load();
    } catch (err) {
      window.alert(String(err));
    } finally {
      memberBusy.value = false;
    }
  }

  async function removeDeveloper(member) {
    const confirmed = window.confirm(t("detail.confirmRemoveDeveloper", { username: member.username }));
    if (!confirmed) return;
    memberBusy.value = true;
    try {
      await removeAppMember(appId, member.user_id);
      await load();
    } catch (err) {
      window.alert(String(err));
    } finally {
      memberBusy.value = false;
    }
  }

  async function makeAdmin(member) {
    const confirmed = window.confirm(t("detail.confirmTransferAdmin", { username: member.username }));
    if (!confirmed) return;
    memberBusy.value = true;
    try {
      await transferAppAdmin(appId, member.user_id);
      await load();
    } catch (err) {
      window.alert(String(err));
    } finally {
      memberBusy.value = false;
    }
  }

  function toggleMemberMenu(userId) {
    memberMenuUserId.value = memberMenuUserId.value === userId ? null : userId;
  }

  function closeMemberMenu() {
    memberMenuUserId.value = null;
  }

  function openUserDropdown() {
    showUserDropdown.value = true;
  }

  function closeUserDropdown() {
    window.setTimeout(() => {
      showUserDropdown.value = false;
    }, 120);
  }

  function chooseUser(username) {
    memberUsername.value = username;
    showUserDropdown.value = false;
  }

  async function loadUsers() {
    loadingUsers.value = true;
    try {
      const data = await fetchUsers();
      availableUsers.value = data.users || [];
    } catch (err) {
      console.warn(err);
    } finally {
      loadingUsers.value = false;
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
      uploadManifestNameMismatch.value = buildManifestNameMismatchMessage(data?.manifest);
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
      editManifestNameMismatch.value = buildManifestNameMismatchMessage(data?.manifest);
      editForm.value.manifest.appId = appId;
      editForm.value.manifest.name = appInfo.value?.name || editForm.value.manifest.name;
      editForm.value.manifest.version = editForm.value.version;
      editForm.value.manifest.description = editForm.value.description;
    }
  }

  onMounted(async () => {
    const result = await load();
    await loadUsers();
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
    appPermissions,
    members,
    versions,
    isOwnerOrAdmin,
    canManageMembers,
    memberUsername,
    memberBusy,
    memberMenuUserId,
    showUserDropdown,
    selectableUsers,
    loadingUsers,
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
    addDeveloper,
    openUserDropdown,
    closeUserDropdown,
    chooseUser,
    toggleMemberMenu,
    closeMemberMenu,
    removeDeveloper,
    makeAdmin,
    onFileChange,
  };
}

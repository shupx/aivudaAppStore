import { ref } from "vue";
import {
  fetchMe,
  fetchStoreAppDetail,
  parsePackageManifest,
  modifyVersion,
  uploadVersion,
  unpublishVersion,
  publishVersion,
  deleteVersion,
  logout,
} from "../services/api";
import { buildUbuntuTreeLines, sortPackageEntriesByDirectory } from "../utils/packageTree";

export function useVersionManagement(appId) {
  const loading = ref(false);
  const detail = ref(null);
  const operating = ref("");
  const error = ref("");
  const parsingManifest = ref(false);
  const uploadParsedReady = ref(false);
  const uploadPackageEntries = ref([]);
  const uploadPackageTreeLines = ref([]);
  const uploadManifestFoundPath = ref("");
  const uploadParsedManifestBase = ref({});

  function resetUploadParseState() {
    uploadParsedReady.value = false;
    uploadPackageEntries.value = [];
    uploadPackageTreeLines.value = [];
    uploadManifestFoundPath.value = "";
    uploadParsedManifestBase.value = {};
  }

  async function load() {
    loading.value = true;
    error.value = "";
    try {
      await fetchMe();
      detail.value = await fetchStoreAppDetail(appId);
      return detail.value;
    } catch (err) {
      if (String(err).includes("401")) {
        logout();
        throw err;
      }
      error.value = String(err);
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function parseManifestFromPackage(file) {
    parsingManifest.value = true;
    try {
      const fd = new FormData();
      fd.append("package_zip", file);
      return await parsePackageManifest(fd);
    } finally {
      parsingManifest.value = false;
    }
  }

  async function parseUploadPackage(file, { truncatedLabel = "" } = {}) {
    const data = await parseManifestFromPackage(file);
    uploadPackageEntries.value = sortPackageEntriesByDirectory(data?.package_entries);
    uploadPackageTreeLines.value = buildUbuntuTreeLines(uploadPackageEntries.value, truncatedLabel);
    uploadManifestFoundPath.value = data?.found_path || "";
    uploadParsedManifestBase.value =
      data?.manifest && typeof data.manifest === "object"
        ? data.manifest
        : data?.normalized_manifest && typeof data.normalized_manifest === "object"
          ? data.normalized_manifest
          : {};
    uploadParsedReady.value = true;
    return data;
  }

  async function doUploadVersion(manifest, packageZipFile) {
    operating.value = `upload:${manifest.version}`;
    try {
      const fd = new FormData();
      fd.append("version", manifest.version);
      fd.append("description", manifest.description || "");
      fd.append("manifest_json", JSON.stringify(manifest));
      fd.append("package_zip", packageZipFile);
      await uploadVersion(appId, fd);
      await load();
    } finally {
      operating.value = "";
    }
  }

  async function doModifyVersion(version, description, packageZipFile, manifest = null) {
    operating.value = `modify:${version}`;
    try {
      const fd = new FormData();
      if (description !== null && description !== undefined) {
        fd.append("description", description);
      }
      if (packageZipFile) {
        if (manifest) {
          fd.append("manifest_json", JSON.stringify(manifest));
        }
        fd.append("package_zip", packageZipFile);
      }
      await modifyVersion(appId, version, fd);
      await load();
    } finally {
      operating.value = "";
    }
  }

  async function doUnpublish(version) {
    operating.value = `unpublish:${version}`;
    try {
      await unpublishVersion(appId, version);
      await load();
    } finally {
      operating.value = "";
    }
  }

  async function doPublish(version) {
    operating.value = `publish:${version}`;
    try {
      await publishVersion(appId, version);
      await load();
    } finally {
      operating.value = "";
    }
  }

  async function doDelete(version) {
    operating.value = `delete:${version}`;
    try {
      await deleteVersion(appId, version);
      await load();
    } finally {
      operating.value = "";
    }
  }

  return {
    loading,
    detail,
    operating,
    parsingManifest,
    uploadParsedReady,
    uploadPackageEntries,
    uploadPackageTreeLines,
    uploadManifestFoundPath,
    uploadParsedManifestBase,
    error,
    load,
    resetUploadParseState,
    parseManifestFromPackage,
    parseUploadPackage,
    doUploadVersion,
    doModifyVersion,
    doUnpublish,
    doPublish,
    doDelete,
  };
}

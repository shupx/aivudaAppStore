import { ref } from "vue";
import {
  fetchMe,
  fetchStoreAppDetail,
  uploadVersion,
  modifyVersion,
  unpublishVersion,
  publishVersion,
  deleteVersion,
  logout,
} from "../services/api";

export function useVersionManagement(appId) {
  const loading = ref(false);
  const detail = ref(null);
  const operating = ref("");
  const error = ref("");

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

  async function doUploadVersion(version, description, packageZipFile) {
    operating.value = `upload:${version}`;
    try {
      const fd = new FormData();
      fd.append("version", version);
      fd.append("description", description || "");
      fd.append("package_zip", packageZipFile);
      await uploadVersion(appId, fd);
      await load();
    } finally {
      operating.value = "";
    }
  }

  async function doModifyVersion(version, description, packageZipFile) {
    operating.value = `modify:${version}`;
    try {
      const fd = new FormData();
      if (description !== null && description !== undefined) {
        fd.append("description", description);
      }
      if (packageZipFile) {
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
    error,
    load,
    doUploadVersion,
    doModifyVersion,
    doUnpublish,
    doPublish,
    doDelete,
  };
}

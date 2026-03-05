import { computed, reactive, ref } from "vue";
import { APPSTORE_API_PREFIX, fetchMe, logout, parsePackageManifest, session, uploadPackage } from "../services/api";
import { applyNormalizedManifest, buildRequiredManifestFromForm, createManifestForm } from "../utils/manifest";
import { buildUbuntuTreeLines, sortPackageEntriesByDirectory } from "../utils/packageTree";

function toAppIdSlug(text) {
  const raw = String(text || "").trim().toLowerCase();
  if (!raw) return "app";
  return raw
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 32) || "app";
}

function twoDigits(value) {
  return String(value).padStart(2, "0");
}

export function useAppUpload(t) {
  const output = ref({ text: "", isError: false });
  const parsingManifest = ref(false);
  const submitting = ref(false);
  const parsedReady = ref(false);
  const packageEntries = ref([]);
  const packageTreeLines = ref([]);
  const manifestFoundPath = ref("");
  const parsedManifestBase = ref({});

  const form = reactive(createManifestForm());

  const files = {
    packageZip: ref(null),
  };

  const sampleUrl = computed(() => {
    return `${APPSTORE_API_PREFIX}/store/sample-package`;
  });

  function setOutput(data, isError = false) {
    const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    output.value = { text, isError };
  }

  function bindFile(refKey, event) {
    files[refKey].value = event.target.files && event.target.files.length ? event.target.files[0] : null;
  }

  async function parseAndPrefillManifest(file) {
    if (!file) return;
    parsingManifest.value = true;
    parsedReady.value = false;
    packageEntries.value = [];
    packageTreeLines.value = [];
    manifestFoundPath.value = "";
    parsedManifestBase.value = {};
    try {
      const fd = new FormData();
      fd.append("package_zip", file);
      const data = await parsePackageManifest(fd);
      if (data?.normalized_manifest) {
        applyNormalizedManifest(form, data.normalized_manifest);
      }
      parsedManifestBase.value =
        data?.manifest && typeof data.manifest === "object"
          ? data.manifest
          : data?.normalized_manifest && typeof data.normalized_manifest === "object"
            ? data.normalized_manifest
            : {};
      packageEntries.value = sortPackageEntriesByDirectory(data?.package_entries);
      packageTreeLines.value = buildUbuntuTreeLines(packageEntries.value, t("upload.treeTruncated"));
      manifestFoundPath.value = data?.found_path || "";
      parsedReady.value = true;
      setOutput(t("upload.parseSuccess"));
    } catch (err) {
      setOutput(String(err), true);
    } finally {
      parsingManifest.value = false;
    }
  }

  async function bindPackageZip(event) {
    bindFile("packageZip", event);
    await parseAndPrefillManifest(files.packageZip.value);
  }

  async function submitPackage({ onSuccess, onAuthFail } = {}) {
    try {
      await fetchMe();
      if (!files.packageZip.value) {
        setOutput(t("upload.requiredPackage"), true);
        return null;
      }
      if (!parsedReady.value) {
        setOutput(t("upload.parseFirst"), true);
        return null;
      }

      const manifest = buildRequiredManifestFromForm(form, parsedManifestBase.value, t);

      const fd = new FormData();
      fd.append("name", manifest.name);
      fd.append("version", manifest.version);
      fd.append("description", manifest.description);
      fd.append("manifest_json", JSON.stringify(manifest));
      fd.append("package_zip", files.packageZip.value);

      submitting.value = true;
      const data = await uploadPackage(fd);
      setOutput(data);
      if (onSuccess) onSuccess(data);
      return data;
    } catch (err) {
      if (String(err).includes("401")) {
        logout();
        if (onAuthFail) onAuthFail(err);
        return null;
      }
      setOutput(String(err), true);
      return null;
    } finally {
      submitting.value = false;
    }
  }

  function generateAppId() {
    const appName = toAppIdSlug(form.name || form.appId || "app");
    const now = new Date();
    const ymms = `${now.getFullYear()}${twoDigits(now.getMonth() + 1)}${twoDigits(now.getMinutes())}${twoDigits(now.getSeconds())}`;
    const randomNum = Math.floor(Math.random() * 9000) + 1000;
    form.appId = `app_${appName}_${ymms}_${randomNum}`;
  }

  return {
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
  };
}

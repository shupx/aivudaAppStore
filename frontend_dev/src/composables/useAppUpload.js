import { computed, reactive, ref } from "vue";
import { fetchMe, logout, parsePackageManifest, session, uploadPackage } from "../services/api";
import { applyNormalizedManifest, buildManifestFromForm, createManifestForm } from "../utils/manifest";

export function useAppUpload(t) {
  const output = ref({ text: "", isError: false });
  const parsingManifest = ref(false);

  const form = reactive(createManifestForm());

  const files = {
    packageZip: ref(null),
  };

  const sampleUrl = computed(() => {
    const base = (session.baseUrl || "").replace(/\/$/, "");
    return base ? `${base}/store/sample-package` : "/store/sample-package";
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
    try {
      const fd = new FormData();
      fd.append("package_zip", file);
      const data = await parsePackageManifest(fd);
      if (data?.normalized_manifest) {
        applyNormalizedManifest(form, data.normalized_manifest);
      }
      if (Array.isArray(data?.warnings) && data.warnings.length) {
        setOutput(data.warnings.join("\n"), false);
      }
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

      const manifest = buildManifestFromForm(form, t);

      const fd = new FormData();
      fd.append("name", manifest.name || manifest.app_id);
      fd.append("version", manifest.version);
      fd.append("description", manifest.description || "");
      fd.append("manifest_json", JSON.stringify(manifest));
      fd.append("package_zip", files.packageZip.value);

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
    }
  }

  return {
    output,
    parsingManifest,
    form,
    sampleUrl,
    bindPackageZip,
    submitPackage,
  };
}

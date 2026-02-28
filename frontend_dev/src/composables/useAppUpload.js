import { computed, ref } from "vue";
import { fetchMe, logout, session, uploadPackage } from "../services/api";

export function useAppUpload() {
  const output = ref({ text: "", isError: false });

  const form = {
    name: ref(""),
    version: ref("0.1.0"),
    description: ref(""),
  };

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

  async function submitPackage({ onSuccess, onAuthFail } = {}) {
    try {
      await fetchMe();
      if (!form.name.value.trim() || !form.version.value.trim()) {
        setOutput("必须填写 name 与 version", true);
        return null;
      }
      if (!files.packageZip.value) {
        setOutput("必须上传 package.zip", true);
        return null;
      }

      const fd = new FormData();
      fd.append("name", form.name.value.trim());
      fd.append("version", form.version.value.trim());
      fd.append("description", form.description.value.trim());
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
    form,
    sampleUrl,
    bindFile,
    submitPackage,
  };
}

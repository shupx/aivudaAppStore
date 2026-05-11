import { ref } from "vue";
import { buildApiUrl, fetchStoreDownloadUrl } from "../services/api";

function triggerBrowserDownload(fileUrl, filename) {
  const link = document.createElement("a");
  link.href = fileUrl;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function inferFilename(appId, version, info) {
  const explicit = String(info?.filename || "").trim();
  if (explicit) return explicit;
  const url = String(info?.url || "");
  const cleaned = url.split("?")[0];
  const basename = cleaned.split("/").filter(Boolean).pop() || "";
  const suffixes = basename.match(/(\.tar\.gz|\.tgz|\.tar\.xz|\.txz|\.tar|\.zip)$/i);
  const suffix = suffixes?.[1] || ".zip";
  return `${appId}-${version}${suffix}`;
}

export function useAppDownload() {
  const downloading = ref(false);
  const progress = ref(0);

  async function downloadAppPackage(appId, version) {
    downloading.value = true;
    progress.value = 5;
    try {
      progress.value = 35;
      const info = await fetchStoreDownloadUrl(appId, version);
      const fileUrl = buildApiUrl(info.url);
      const filename = inferFilename(appId, version, info);

      progress.value = 80;
      triggerBrowserDownload(fileUrl, filename);
      progress.value = 100;
    } finally {
      setTimeout(() => {
        progress.value = 0;
      }, 500);
      downloading.value = false;
    }
  }

  return {
    downloading,
    progress,
    downloadAppPackage,
  };
}

import { ref } from "vue";
import { fetchAppStoreVersion } from "../services/api";

const version = ref("unknown");
const loaded = ref(false);
let pendingRequest = null;

export function useAppStoreVersion() {
  async function loadVersion() {
    if (loaded.value) return version.value;
    if (pendingRequest) return pendingRequest;

    pendingRequest = fetchAppStoreVersion()
      .then((data) => {
        version.value = String(data?.version || "unknown");
        loaded.value = true;
        return version.value;
      })
      .catch(() => {
        version.value = "unknown";
        loaded.value = true;
        return version.value;
      })
      .finally(() => {
        pendingRequest = null;
      });

    return pendingRequest;
  }

  return {
    version,
    loaded,
    loadVersion,
  };
}

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

const NON_EXPANDABLE_PACKAGE_DIRECTORIES = Object.freeze([".git", ".svn", ".hg", "node_modules"]);
const nonExpandableDirectorySet = new Set(NON_EXPANDABLE_PACKAGE_DIRECTORIES);

export function sortPackageEntriesByDirectory(entries) {
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

export function buildUbuntuTreeLines(entries, truncatedLabel = "") {
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

      if (child.type === "dir" && !nonExpandableDirectorySet.has(child.name) && child.children.size > 0) {
        const nextPrefix = `${prefix}${isLast ? "    " : "│   "}`;
        walk(child, nextPrefix);
      }
    });
  }

  walk(root, "");
  return lines;
}

export { NON_EXPANDABLE_PACKAGE_DIRECTORIES };

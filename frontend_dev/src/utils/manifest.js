function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function parseJsonObject(text, fieldName, t) {
  const raw = (text || "").trim();
  if (!raw) return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(t("errors.invalidJson", { field: fieldName }));
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(t("errors.jsonObjectRequired", { field: fieldName }));
  }
  return parsed;
}

function parseJsonArray(text, fieldName, t) {
  const raw = (text || "").trim();
  if (!raw) return [];
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(t("errors.invalidJson", { field: fieldName }));
  }
  if (!Array.isArray(parsed)) {
    throw new Error(t("errors.jsonArrayRequired", { field: fieldName }));
  }
  return parsed.map((item) => String(item));
}

export function createManifestForm(initial = {}) {
  return {
    appId: initial.appId || "",
    name: initial.name || "",
    description: initial.description || "",
    version: initial.version || "0.1.0",
    entrypoint: initial.entrypoint || "",
    argsText: initial.argsText || "[]",
    icon: initial.icon || "",
    preInstall: initial.preInstall || "",
    preUninstall: initial.preUninstall || "",
    updateThisVersion: initial.updateThisVersion || "",
    defaultConfigText: initial.defaultConfigText || "{}",
    configSchemaText: initial.configSchemaText || "",
    extraManifestText: initial.extraManifestText || "{}",
  };
}

export function applyNormalizedManifest(form, normalizedManifest = {}) {
  const run = normalizedManifest.run && typeof normalizedManifest.run === "object" ? normalizedManifest.run : {};
  form.appId = normalizedManifest.app_id || "";
  form.name = normalizedManifest.name || "";
  form.description = normalizedManifest.description || "";
  form.version = normalizedManifest.version || form.version || "0.1.0";
  form.entrypoint = run.entrypoint || "";
  form.argsText = pretty(Array.isArray(run.args) ? run.args : []);
  form.icon = normalizedManifest.icon || "";
  form.preInstall = normalizedManifest.pre_install || "";
  form.preUninstall = normalizedManifest.pre_uninstall || "";
  form.updateThisVersion = normalizedManifest.update_this_version || "";
  form.defaultConfigText = pretty(normalizedManifest.default_config || {});
  form.configSchemaText =
    normalizedManifest.config_schema === null || normalizedManifest.config_schema === undefined
      ? ""
      : pretty(normalizedManifest.config_schema);
  form.extraManifestText = pretty(normalizedManifest.extra_manifest || {});
}

export function buildManifestFromForm(form, t) {
  const appId = (form.appId || "").trim();
  const name = (form.name || "").trim();
  const version = (form.version || "").trim();
  const description = (form.description || "").trim();
  const entrypoint = (form.entrypoint || "").trim();

  if (!appId) throw new Error(t("errors.requiredField", { field: t("fields.appId") }));
  if (!version) throw new Error(t("errors.requiredField", { field: t("fields.version") }));
  if (!entrypoint) throw new Error(t("errors.requiredField", { field: t("fields.entrypoint") }));

  const runArgs = parseJsonArray(form.argsText, t("fields.runArgs"), t);
  const defaultConfig = parseJsonObject(form.defaultConfigText, t("fields.defaultConfig"), t);

  const configSchemaRaw = (form.configSchemaText || "").trim();
  let configSchema = null;
  if (configSchemaRaw) {
    configSchema = parseJsonObject(configSchemaRaw, t("fields.configSchema"), t);
  }

  const extraManifest = parseJsonObject(form.extraManifestText, t("fields.extraManifest"), t);

  const manifest = {
    ...extraManifest,
    app_id: appId,
    name: name || appId,
    description,
    version,
    run: {
      entrypoint,
      args: runArgs,
    },
    default_config: defaultConfig,
  };

  const icon = (form.icon || "").trim();
  if (icon) manifest.icon = icon;

  const preInstall = (form.preInstall || "").trim();
  if (preInstall) manifest.pre_install = preInstall;

  const preUninstall = (form.preUninstall || "").trim();
  if (preUninstall) manifest.pre_uninstall = preUninstall;

  const updateThisVersion = (form.updateThisVersion || "").trim();
  if (updateThisVersion) manifest.update_this_version = updateThisVersion;

  if (configSchema) manifest.config_schema = configSchema;

  return manifest;
}

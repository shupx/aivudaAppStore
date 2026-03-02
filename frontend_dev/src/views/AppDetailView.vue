<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppTopBar from "../components/AppTopBar.vue";
import { useVersionManagement } from "../composables/useVersionManagement";
import { useAppDownload } from "../composables/useAppDownload";
import { useVersionSort } from "../composables/useVersionSort";
import { applyNormalizedManifest, buildManifestFromForm, createManifestForm } from "../utils/manifest";
import { formatSize, formatDate } from "../utils/format";
import { session } from "../services/api";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const appId = route.params.appId;

const {
  loading,
  detail,
  operating,
  parsingManifest,
  load,
  parseManifestFromPackage,
  doUploadVersion,
  doModifyVersion,
  doUnpublish,
  doPublish,
  doDelete,
} = useVersionManagement(appId);

const { downloading, progress: downloadProgress, downloadAppPackage } = useAppDownload();

const showUploadDialog = ref(false);
const uploadForm = ref({
  description: "",
  manifest: createManifestForm({ appId }),
});
const uploadFile = ref(null);
const uploadSubmitting = ref(false);

const showEditDialog = ref(false);
const editForm = ref({
  version: "",
  description: "",
  manifest: createManifestForm({ appId }),
});
const editFile = ref(null);
const editSubmitting = ref(false);

const confirmDialog = ref({ show: false, title: "", message: "", submitting: false, action: null });

const appInfo = computed(() => detail.value?.app || null);
const versions = computed(() => detail.value?.versions || []);
const isOwnerOrAdmin = computed(() => {
  if (!appInfo.value || !session.user) return false;
  return session.user.role === "admin" || session.user.id === appInfo.value.owner_user_id;
});

const { sortBy, sortAsc, sortedVersions } = useVersionSort(versions);

function isVersionBusy(ver) {
  return operating.value.endsWith(`:${ver.version}`);
}

async function downloadVersion(version) {
  try {
    await downloadAppPackage(appId, version);
  } catch (err) {
    window.alert(String(err));
  }
}

function openUploadDialog() {
  uploadForm.value = {
    description: "",
    manifest: createManifestForm({ appId }),
  };
  uploadFile.value = null;
  showUploadDialog.value = true;
}

async function submitUploadVersion() {
  if (!uploadFile.value) {
    window.alert(t("errors.mustChoosePackage"));
    return;
  }
  uploadSubmitting.value = true;
  try {
    const manifest = buildManifestFromForm(uploadForm.value.manifest, t);
    if (!manifest.description && uploadForm.value.description.trim()) {
      manifest.description = uploadForm.value.description.trim();
    }
    await doUploadVersion(manifest, uploadFile.value);
    showUploadDialog.value = false;
  } catch (err) {
    window.alert(String(err));
  } finally {
    uploadSubmitting.value = false;
  }
}

function openEditDialog(ver) {
  editForm.value = {
    version: ver.version,
    description: ver.description || "",
    manifest: createManifestForm({
      appId,
      version: ver.version,
      description: ver.description || "",
    }),
  };
  editFile.value = null;
  showEditDialog.value = true;
}

async function submitEditVersion() {
  editSubmitting.value = true;
  try {
    let manifest = null;
    if (editFile.value) {
      manifest = buildManifestFromForm(editForm.value.manifest, t);
      manifest.version = editForm.value.version;
      manifest.app_id = appId;
      if (!manifest.description && editForm.value.description.trim()) {
        manifest.description = editForm.value.description.trim();
      }
    }
    await doModifyVersion(editForm.value.version, editForm.value.description, editFile.value, manifest);
    showEditDialog.value = false;
  } catch (err) {
    window.alert(String(err));
  } finally {
    editSubmitting.value = false;
  }
}

function openConfirm(title, message, action) {
  confirmDialog.value = { show: true, title, message, submitting: false, action };
}

async function runConfirm() {
  confirmDialog.value.submitting = true;
  try {
    await confirmDialog.value.action();
    confirmDialog.value.show = false;
  } catch (err) {
    window.alert(String(err));
  } finally {
    confirmDialog.value.submitting = false;
  }
}

function confirmUnpublish(ver) {
  openConfirm(
    t("detail.confirmUnpublishTitle"),
    t("detail.confirmUnpublishMessage", { version: ver.version }),
    () => doUnpublish(ver.version)
  );
}

function confirmDelete(ver) {
  openConfirm(
    t("detail.confirmDeleteTitle"),
    t("detail.confirmDeleteMessage", { version: ver.version }),
    () => doDelete(ver.version)
  );
}

async function handlePublish(ver) {
  try {
    await doPublish(ver.version);
  } catch (err) {
    window.alert(String(err));
  }
}

async function onFileChange(target, event) {
  const file = event.target.files?.[0] || null;
  if (target === "upload") {
    uploadFile.value = file;
    if (!file) return;
    const data = await parseManifestFromPackage(file);
    if (data?.normalized_manifest) {
      applyNormalizedManifest(uploadForm.value.manifest, data.normalized_manifest);
      if (!uploadForm.value.manifest.appId) uploadForm.value.manifest.appId = appId;
    }
    return;
  }

  if (target === "edit") {
    editFile.value = file;
    if (!file) return;
    const data = await parseManifestFromPackage(file);
    if (data?.normalized_manifest) {
      applyNormalizedManifest(editForm.value.manifest, data.normalized_manifest);
      editForm.value.manifest.appId = appId;
      editForm.value.manifest.version = editForm.value.version;
    }
  }
}

onMounted(async () => {
  const result = await load();
  if (result === null && !detail.value) {
    router.push("/login");
  }
});
</script>

<template>
  <div class="bg"></div>
  <section class="page-wrap">
    <AppTopBar :title="t('detail.title')" :subtitle="appId" />

    <section class="card list-wrap detail-header">
      <div class="detail-header-content">
        <div>
          <p class="app-name">{{ appInfo?.name || t("detail.unknownApp") }}</p>
          <p class="sub">{{ appId }}</p>
          <p class="sub" v-if="appInfo?.description">{{ appInfo.description }}</p>
        </div>
        <button v-if="isOwnerOrAdmin" @click="openUploadDialog" :disabled="!!operating">
          {{ t("detail.uploadVersion") }}
        </button>
      </div>
    </section>

    <section class="card list-wrap">
      <div class="version-list-header">
        <h2>{{ t("detail.versionList", { count: versions.length }) }}</h2>
        <div class="sort-controls">
          <span class="sort-label">{{ t("detail.sort") }}</span>
          <button :class="{ active: sortBy === 'version' }" @click="sortBy = 'version'">{{ t("detail.sortVersion") }}</button>
          <button :class="{ active: sortBy === 'published' }" @click="sortBy = 'published'">{{ t("detail.sortPublished") }}</button>
          <button :class="{ active: sortBy === 'updated' }" @click="sortBy = 'updated'">{{ t("detail.sortUpdated") }}</button>
          <button class="sort-dir" @click="sortAsc = !sortAsc" :title="sortAsc ? t('detail.asc') : t('detail.desc')">
            {{ sortAsc ? "↑" : "↓" }}
          </button>
        </div>
      </div>
      <div v-if="loading" class="hint">{{ t("detail.loading") }}</div>
      <div v-else-if="versions.length === 0" class="hint">{{ t("detail.empty") }}</div>
      <div v-else class="version-list">
        <article
          class="version-item"
          v-for="ver in sortedVersions"
          :key="ver.version"
          :class="{ 'version-item--unpublished': ver.status !== 'published' }"
        >
          <div class="version-header">
            <h3>
              <span>{{ ver.version }}</span>
              <span class="chip" :class="ver.status === 'published' ? '' : 'chip-unpublished'">
                {{ ver.status === "published" ? t("detail.published") : t("detail.unpublished") }}
              </span>
            </h3>
            <span class="version-size">{{ formatSize(ver.artifact_size) }}</span>
          </div>

          <div class="version-meta">
            <span v-if="ver.published_at">{{ t("detail.publishedAt", { time: formatDate(ver.published_at) }) }}</span>
            <span>{{ t("detail.updatedAt", { time: formatDate(ver.updated_at) }) }}</span>
          </div>
          <div v-if="ver.description" class="version-desc">{{ ver.description }}</div>

          <div v-if="isOwnerOrAdmin" class="version-actions">
            <button
              v-if="ver.status === 'published'"
              @click="downloadVersion(ver.version)"
              :disabled="downloading || isVersionBusy(ver)"
            >
              <span v-if="downloading">{{ t("detail.downloadBusy", { progress: downloadProgress }) }}</span>
              <span v-else>{{ t("detail.download") }}</span>
            </button>
            <button @click="openEditDialog(ver)" :disabled="!!operating">
              {{ t("detail.edit") }}
            </button>
            <button
              v-if="ver.status === 'published'"
              @click="confirmUnpublish(ver)"
              :disabled="isVersionBusy(ver)"
            >
              {{ t("detail.unpublish") }}
            </button>
            <button
              v-else
              @click="handlePublish(ver)"
              :disabled="isVersionBusy(ver)"
            >
              {{ t("detail.republish") }}
            </button>
            <button class="danger" @click="confirmDelete(ver)" :disabled="isVersionBusy(ver)">
              {{ t("detail.delete") }}
            </button>
          </div>

          <div v-else-if="ver.status === 'published'" class="version-actions">
            <button
              @click="downloadVersion(ver.version)"
              :disabled="downloading"
            >
              {{ t("detail.download") }}
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>

  <div v-if="showUploadDialog" class="modal-overlay" @click.self="showUploadDialog = false">
    <div class="modal-card card">
      <h2>{{ t("detail.uploadDialogTitle") }}</h2>
      <form class="stack" @submit.prevent="submitUploadVersion">
        <label>
          {{ t("fields.appId") }}
          <input v-model="uploadForm.manifest.appId" required />
        </label>
        <label>
          {{ t("fields.name") }}
          <input v-model="uploadForm.manifest.name" />
        </label>
        <label>
          {{ t("fields.version") }}
          <input v-model="uploadForm.manifest.version" required />
        </label>
        <label>
          {{ t("fields.description") }}
          <textarea v-model="uploadForm.manifest.description" rows="2" />
        </label>
        <label>
          {{ t("fields.entrypoint") }}
          <input v-model="uploadForm.manifest.entrypoint" required />
        </label>
        <label>
          {{ t("fields.runArgs") }}
          <textarea v-model="uploadForm.manifest.argsText" rows="2" />
        </label>

        <div class="file-row">
          <span class="file-label">{{ t("detail.packageLabel") }}</span>
          <input type="file" accept=".zip" @change="onFileChange('upload', $event)" />
        </div>
        <p class="hint" v-if="parsingManifest">{{ t("upload.parsing") }}</p>
        <p class="hint">{{ t("detail.manifestHint") }}</p>

        <h3>{{ t("detail.uploadManifest") }}</h3>
        <label>
          {{ t("fields.icon") }}
          <input v-model="uploadForm.manifest.icon" />
        </label>
        <label>
          {{ t("fields.preInstall") }}
          <input v-model="uploadForm.manifest.preInstall" />
        </label>
        <label>
          {{ t("fields.preUninstall") }}
          <input v-model="uploadForm.manifest.preUninstall" />
        </label>
        <label>
          {{ t("fields.updateThisVersion") }}
          <input v-model="uploadForm.manifest.updateThisVersion" />
        </label>
        <label>
          {{ t("fields.defaultConfig") }}
          <textarea v-model="uploadForm.manifest.defaultConfigText" rows="3" />
        </label>
        <label>
          {{ t("fields.configSchema") }}
          <textarea v-model="uploadForm.manifest.configSchemaText" rows="3" />
        </label>
        <label>
          {{ t("fields.extraManifest") }}
          <textarea v-model="uploadForm.manifest.extraManifestText" rows="3" />
        </label>

        <div class="btnrow">
          <button type="submit" :disabled="uploadSubmitting">
            {{ uploadSubmitting ? t("detail.uploading") : t("detail.uploadNow") }}
          </button>
          <button type="button" @click="showUploadDialog = false" :disabled="uploadSubmitting">{{ t("common.cancel") }}</button>
        </div>
      </form>
    </div>
  </div>

  <div v-if="showEditDialog" class="modal-overlay" @click.self="showEditDialog = false">
    <div class="modal-card card">
      <h2>{{ t("detail.editDialogTitle", { version: editForm.version }) }}</h2>
      <form class="stack" @submit.prevent="submitEditVersion">
        <label>
          {{ t("detail.descriptionLabel") }}
          <textarea v-model="editForm.description" :placeholder="t('detail.descriptionLabel')" rows="3" />
        </label>
        <div class="file-row">
          <span class="file-label">{{ t("detail.replacePackage") }}</span>
          <input type="file" accept=".zip" @change="onFileChange('edit', $event)" />
        </div>
        <p class="hint" v-if="parsingManifest">{{ t("upload.parsing") }}</p>
        <p class="hint">{{ t("detail.manifestHint") }}</p>

        <h3>{{ t("detail.editManifest") }}</h3>
        <label>
          {{ t("fields.entrypoint") }}
          <input v-model="editForm.manifest.entrypoint" />
        </label>
        <label>
          {{ t("fields.runArgs") }}
          <textarea v-model="editForm.manifest.argsText" rows="2" />
        </label>
        <label>
          {{ t("fields.description") }}
          <textarea v-model="editForm.manifest.description" rows="2" />
        </label>
        <label>
          {{ t("fields.icon") }}
          <input v-model="editForm.manifest.icon" />
        </label>
        <label>
          {{ t("fields.preInstall") }}
          <input v-model="editForm.manifest.preInstall" />
        </label>
        <label>
          {{ t("fields.preUninstall") }}
          <input v-model="editForm.manifest.preUninstall" />
        </label>
        <label>
          {{ t("fields.updateThisVersion") }}
          <input v-model="editForm.manifest.updateThisVersion" />
        </label>
        <label>
          {{ t("fields.defaultConfig") }}
          <textarea v-model="editForm.manifest.defaultConfigText" rows="3" />
        </label>
        <label>
          {{ t("fields.configSchema") }}
          <textarea v-model="editForm.manifest.configSchemaText" rows="3" />
        </label>
        <label>
          {{ t("fields.extraManifest") }}
          <textarea v-model="editForm.manifest.extraManifestText" rows="3" />
        </label>

        <div class="btnrow">
          <button type="submit" :disabled="editSubmitting">
            {{ editSubmitting ? t("detail.saving") : t("common.save") }}
          </button>
          <button type="button" @click="showEditDialog = false" :disabled="editSubmitting">{{ t("common.cancel") }}</button>
        </div>
      </form>
    </div>
  </div>

  <div v-if="confirmDialog.show" class="modal-overlay" @click.self="confirmDialog.show = false">
    <div class="modal-card card">
      <h2>{{ confirmDialog.title }}</h2>
      <p>{{ confirmDialog.message }}</p>
      <div class="btnrow">
        <button class="danger" @click="runConfirm" :disabled="confirmDialog.submitting">
          {{ confirmDialog.submitting ? t("common.processing") : t("common.confirm") }}
        </button>
        <button @click="confirmDialog.show = false" :disabled="confirmDialog.submitting">{{ t("common.cancel") }}</button>
      </div>
    </div>
  </div>
</template>

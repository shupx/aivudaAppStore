<script setup>
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppTopBar from "../components/AppTopBar.vue";
import { useAppDetailPage } from "../composables/useAppDetailPage";
import { formatSize, formatDate } from "../utils/format";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const appId = route.params.appId;

const {
  loading,
  operating,
  parsingManifest,
  uploadParsedReady,
  uploadPackageEntries,
  uploadPackageTreeLines,
  uploadManifestFoundPath,
  downloading,
  downloadProgress,
  showUploadDialog,
  uploadForm,
  uploadSubmitting,
  showEditDialog,
  editForm,
  editSubmitting,
  editHasPackageSelected,
  editParsedReady,
  editPackageEntries,
  editPackageTreeLines,
  editManifestFoundPath,
  confirmDialog,
  appInfo,
  versions,
  isOwnerOrAdmin,
  sortBy,
  sortAsc,
  sortedVersions,
  isVersionBusy,
  downloadVersion,
  openUploadDialog,
  submitUploadVersion,
  openEditDialog,
  submitEditVersion,
  runConfirm,
  confirmUnpublish,
  confirmDelete,
  handlePublish,
  onFileChange,
} = useAppDetailPage({
  appId,
  t,
  onAuthFail: () => router.push("/login"),
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
        <h3>{{ t("upload.stepPackage") }}</h3>

        <div class="file-row">
          <span class="file-label">{{ t("detail.packageLabel") }}</span>
          <input type="file" accept=".zip" @change="onFileChange('upload', $event)" />
        </div>
        <p class="hint" v-if="parsingManifest">{{ t("upload.parsing") }}</p>
        <p class="hint">{{ t("upload.hintManifest") }}</p>

        <template v-if="uploadParsedReady">
          <h3>{{ t("upload.stepManifest") }}</h3>
          <p class="hint">{{ t("upload.manifestPath", { path: uploadManifestFoundPath || 'manifest.yaml' }) }}</p>
          <p class="hint">{{ t("upload.requiredFieldsOnly") }}</p>

          <label class="field-item">
            <span class="field-name">{{ t("fields.name") }}</span>
            <input v-model="uploadForm.manifest.name" :placeholder="t('fields.name')" readonly disabled />
            <span class="input-hint">{{ t("detail.appNameLockedHint") }}</span>
          </label>
          <label class="field-item">
            <span class="field-name">{{ t("fields.appId") }}</span>
            <input v-model="uploadForm.manifest.appId" :placeholder="t('fields.appId')" readonly disabled />
            <span class="input-hint">{{ t("detail.appIdLockedHint") }}</span>
          </label>
          <label class="field-item">
            <span class="field-name">{{ t("fields.version") }}</span>
            <input v-model="uploadForm.manifest.version" :placeholder="t('upload.versionPlaceholder')" required />
            <span class="input-hint">{{ t("upload.versionHint") }}</span>
          </label>
          <label class="field-item">
            <span class="field-name">{{ t("fields.description") }}</span>
            <textarea v-model="uploadForm.manifest.description" rows="2" required />
          </label>

          <h3>{{ t("upload.treeTitle") }}</h3>
          <div class="package-tree" v-if="uploadPackageEntries.length">
            <pre class="package-tree-pre">{{ uploadPackageTreeLines.join('\n') }}</pre>
          </div>
          <p class="hint" v-else>{{ t("upload.treeEmpty") }}</p>
        </template>

        <div class="btnrow">
          <button type="submit" :disabled="uploadSubmitting || !uploadParsedReady">
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

        <h3>{{ t("upload.stepPackage") }}</h3>
        <div class="file-row">
          <span class="file-label">{{ t("detail.replacePackage") }}</span>
          <input type="file" accept=".zip" @change="onFileChange('edit', $event)" />
        </div>
        <p class="hint" v-if="parsingManifest">{{ t("upload.parsing") }}</p>
        <p class="hint">{{ t("upload.hintManifest") }}</p>

        <template v-if="editParsedReady">
          <h3>{{ t("upload.stepManifest") }}</h3>
          <p class="hint">{{ t("upload.manifestPath", { path: editManifestFoundPath || 'manifest.yaml' }) }}</p>
          <p class="hint">{{ t("detail.editRequiredFieldsOnly") }}</p>

          <label class="field-item">
            <span class="field-name">{{ t("fields.name") }}</span>
            <input v-model="editForm.manifest.name" :placeholder="t('fields.name')" readonly disabled />
            <span class="input-hint">{{ t("detail.appNameLockedHint") }}</span>
          </label>
          <label class="field-item">
            <span class="field-name">{{ t("fields.appId") }}</span>
            <input v-model="editForm.manifest.appId" :placeholder="t('fields.appId')" readonly disabled />
            <span class="input-hint">{{ t("detail.appIdLockedHint") }}</span>
          </label>
          <label class="field-item">
            <span class="field-name">{{ t("fields.version") }}</span>
            <input v-model="editForm.manifest.version" :placeholder="t('upload.versionPlaceholder')" readonly disabled />
            <span class="input-hint">{{ t("detail.versionLockedHint") }}</span>
          </label>

          <h3>{{ t("upload.treeTitle") }}</h3>
          <div class="package-tree" v-if="editPackageEntries.length">
            <pre class="package-tree-pre">{{ editPackageTreeLines.join('\n') }}</pre>
          </div>
          <p class="hint" v-else>{{ t("upload.treeEmpty") }}</p>
        </template>

        <div class="btnrow">
          <button type="submit" :disabled="editSubmitting || (editHasPackageSelected && !editParsedReady)">
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

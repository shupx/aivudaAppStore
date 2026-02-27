<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import { useVersionManagement } from "../composables/useVersionManagement";
import { useAppDownload } from "../composables/useAppDownload";
import { useVersionSort } from "../composables/useVersionSort";
import { formatSize, formatDate } from "../utils/format";
import { session } from "../services/api";

const route = useRoute();
const router = useRouter();
const appId = route.params.appId;

const {
  loading,
  detail,
  operating,
  load,
  doUploadVersion,
  doModifyVersion,
  doUnpublish,
  doPublish,
  doDelete,
} = useVersionManagement(appId);

const { downloading, progress: downloadProgress, downloadAppPackage } = useAppDownload();

// --- Upload new version dialog ---
const showUploadDialog = ref(false);
const uploadForm = ref({ version: "", description: "" });
const uploadFile = ref(null);
const uploadSubmitting = ref(false);

// --- Edit version dialog ---
const showEditDialog = ref(false);
const editForm = ref({ version: "", description: "" });
const editFile = ref(null);
const editSubmitting = ref(false);

// --- Confirm dialog ---
const confirmDialog = ref({ show: false, title: "", message: "", submitting: false, action: null });

// --- Computed ---
const appInfo = computed(() => detail.value?.app || null);
const versions = computed(() => detail.value?.versions || []);
const isOwnerOrAdmin = computed(() => {
  if (!appInfo.value || !session.user) return false;
  return session.user.role === "admin" || session.user.id === appInfo.value.owner_user_id;
});

// --- Sorting ---
const { sortBy, sortAsc, sortedVersions } = useVersionSort(versions);

// --- Helpers ---
function isVersionBusy(ver) {
  return operating.value.endsWith(`:${ver.version}`);
}

// --- Actions ---
async function downloadVersion(version) {
  try {
    await downloadAppPackage(appId, version);
  } catch (err) {
    window.alert(String(err));
  }
}

function openUploadDialog() {
  uploadForm.value = { version: "", description: "" };
  uploadFile.value = null;
  showUploadDialog.value = true;
}

async function submitUploadVersion() {
  if (!uploadForm.value.version.trim()) {
    window.alert("必须填写版本号");
    return;
  }
  if (!uploadFile.value) {
    window.alert("必须选择安装包（zip）");
    return;
  }
  uploadSubmitting.value = true;
  try {
    await doUploadVersion(
      uploadForm.value.version.trim(),
      uploadForm.value.description.trim(),
      uploadFile.value
    );
    showUploadDialog.value = false;
  } catch (err) {
    window.alert(String(err));
  } finally {
    uploadSubmitting.value = false;
  }
}

function openEditDialog(ver) {
  editForm.value = { version: ver.version, description: ver.description || "" };
  editFile.value = null;
  showEditDialog.value = true;
}

async function submitEditVersion() {
  editSubmitting.value = true;
  try {
    await doModifyVersion(editForm.value.version, editForm.value.description, editFile.value);
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
    "下架版本",
    `确定要下架版本 ${ver.version} 吗？下架后用户将无法从商店下载此版本，可随时重新发布。`,
    () => doUnpublish(ver.version)
  );
}

function confirmDelete(ver) {
  openConfirm(
    "永久删除版本",
    `确定要永久删除版本 ${ver.version} 吗？此操作不可恢复，将同时删除安装包文件。`,
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

function onFileChange(target, event) {
  const file = event.target.files?.[0] || null;
  if (target === "upload") uploadFile.value = file;
  else if (target === "edit") editFile.value = file;
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
    <AppTopBar title="应用详情" :subtitle="appId" />

    <!-- App header card -->
    <section class="card list-wrap detail-header">
      <div class="detail-header-content">
        <div>
          <p class="app-name">{{ appInfo?.name || "未知应用" }}</p>
          <p class="sub">{{ appId }}</p>
          <p class="sub" v-if="appInfo?.description">{{ appInfo.description }}</p>
        </div>
        <button v-if="isOwnerOrAdmin" @click="openUploadDialog" :disabled="!!operating">
          + 上传新版本
        </button>
      </div>
    </section>

    <!-- Version list -->
    <section class="card list-wrap">
      <div class="version-list-header">
        <h2>版本列表（{{ versions.length }}）</h2>
        <div class="sort-controls">
          <span class="sort-label">排序：</span>
          <button :class="{ active: sortBy === 'version' }" @click="sortBy = 'version'">版本号</button>
          <button :class="{ active: sortBy === 'published' }" @click="sortBy = 'published'">发布时间</button>
          <button :class="{ active: sortBy === 'updated' }" @click="sortBy = 'updated'">更新时间</button>
          <button class="sort-dir" @click="sortAsc = !sortAsc" :title="sortAsc ? '升序' : '降序'">
            {{ sortAsc ? '↑' : '↓' }}
          </button>
        </div>
      </div>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="versions.length === 0" class="hint">暂无版本，请上传第一个版本。</div>
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
                {{ ver.status === "published" ? "已发布" : "已下架" }}
              </span>
            </h3>
            <span class="version-size">{{ formatSize(ver.artifact_size) }}</span>
          </div>

          <div class="version-meta">
            <span v-if="ver.published_at">发布于 {{ formatDate(ver.published_at) }}</span>
            <span>更新于 {{ formatDate(ver.updated_at) }}</span>
          </div>
          <div v-if="ver.description" class="version-desc">{{ ver.description }}</div>

          <!-- Owner / admin actions -->
          <div v-if="isOwnerOrAdmin" class="version-actions">
            <button
              v-if="ver.status === 'published'"
              @click="downloadVersion(ver.version)"
              :disabled="downloading || isVersionBusy(ver)"
            >
              <span v-if="downloading">⏳ {{ downloadProgress }}%</span>
              <span v-else>⬇ 下载</span>
            </button>
            <button @click="openEditDialog(ver)" :disabled="!!operating">
              编辑
            </button>
            <button
              v-if="ver.status === 'published'"
              @click="confirmUnpublish(ver)"
              :disabled="isVersionBusy(ver)"
            >
              下架
            </button>
            <button
              v-else
              @click="handlePublish(ver)"
              :disabled="isVersionBusy(ver)"
            >
              重新发布
            </button>
            <button class="danger" @click="confirmDelete(ver)" :disabled="isVersionBusy(ver)">
              删除
            </button>
          </div>

          <!-- Public: download published only -->
          <div v-else-if="ver.status === 'published'" class="version-actions">
            <button
              @click="downloadVersion(ver.version)"
              :disabled="downloading"
            >
              ⬇ 下载
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>

  <!-- Upload new version dialog -->
  <div v-if="showUploadDialog" class="modal-overlay" @click.self="showUploadDialog = false">
    <div class="modal-card card">
      <h2>上传新版本</h2>
      <form class="stack" @submit.prevent="submitUploadVersion">
        <label>
          版本号
          <input v-model="uploadForm.version" placeholder="如 0.1.1, 0.1.1-alpha, rolling, 不推荐其他方式" required />
        </label>
        <label>
          描述（可选，留空则沿用应用当前描述）
          <textarea v-model="uploadForm.description" placeholder="版本描述" rows="3" />
        </label>
        <div class="file-row">
          <span class="file-label">应用安装包（zip）</span>
          <input type="file" accept=".zip" @change="onFileChange('upload', $event)" />
        </div>
        <div class="btnrow">
          <button type="submit" :disabled="uploadSubmitting">
            {{ uploadSubmitting ? "上传中..." : "上传" }}
          </button>
          <button type="button" @click="showUploadDialog = false" :disabled="uploadSubmitting">取消</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Edit version dialog -->
  <div v-if="showEditDialog" class="modal-overlay" @click.self="showEditDialog = false">
    <div class="modal-card card">
      <h2>编辑版本 {{ editForm.version }}</h2>
      <form class="stack" @submit.prevent="submitEditVersion">
        <label>
          版本描述
          <textarea v-model="editForm.description" placeholder="版本描述" rows="3" />
        </label>
        <div class="file-row">
          <span class="file-label">替换安装包（可选，不选则保留原包）</span>
          <input type="file" accept=".zip" @change="onFileChange('edit', $event)" />
        </div>
        <div class="btnrow">
          <button type="submit" :disabled="editSubmitting">
            {{ editSubmitting ? "保存中..." : "保存" }}
          </button>
          <button type="button" @click="showEditDialog = false" :disabled="editSubmitting">取消</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Confirm dialog -->
  <div v-if="confirmDialog.show" class="modal-overlay" @click.self="confirmDialog.show = false">
    <div class="modal-card card">
      <h2>{{ confirmDialog.title }}</h2>
      <p>{{ confirmDialog.message }}</p>
      <div class="btnrow">
        <button class="danger" @click="runConfirm" :disabled="confirmDialog.submitting">
          {{ confirmDialog.submitting ? "处理中..." : "确认" }}
        </button>
        <button @click="confirmDialog.show = false" :disabled="confirmDialog.submitting">取消</button>
      </div>
    </div>
  </div>
</template>

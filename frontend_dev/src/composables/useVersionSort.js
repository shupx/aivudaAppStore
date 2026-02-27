import { computed, ref } from "vue";
import { compareVersions } from "../utils/semver";

/**
 * Composable providing sort state and sorted list for version arrays.
 *
 * @param {import('vue').Ref<Array>} versions - reactive array of version objects
 * @returns sort controls and sorted computed list
 */
export function useVersionSort(versions) {
  const sortBy = ref("version"); // 'version' | 'published' | 'updated'
  const sortAsc = ref(false);    // false = descending (default)

  const sortedVersions = computed(() => {
    const list = [...versions.value];
    const dir = sortAsc.value ? 1 : -1;
    if (sortBy.value === "version") {
      list.sort((a, b) => dir * compareVersions(a.version, b.version));
    } else if (sortBy.value === "published") {
      list.sort((a, b) => dir * ((a.published_at || 0) - (b.published_at || 0)));
    } else {
      list.sort((a, b) => dir * ((a.updated_at || 0) - (b.updated_at || 0)));
    }
    return list;
  });

  return { sortBy, sortAsc, sortedVersions };
}

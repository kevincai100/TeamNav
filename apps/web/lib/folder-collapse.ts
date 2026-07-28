const COMPACT_FOLDER_THRESHOLD = 8;

export function isFolderCollapsed(
  overrides: ReadonlyMap<string, boolean>,
  folderId: string,
  folderCount: number,
): boolean {
  return overrides.get(folderId) ?? folderCount > COMPACT_FOLDER_THRESHOLD;
}

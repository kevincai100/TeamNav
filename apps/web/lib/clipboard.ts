export async function copyText(value: string): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return;
    } catch {
      // HTTP deployments and restricted browsers can reject the modern API.
    }
  }

  if (typeof document === "undefined" || !document.execCommand) {
    throw new Error("CLIPBOARD_UNAVAILABLE");
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.readOnly = true;
  textarea.dataset.teamnavCopyFallback = "true";
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.focus();
  textarea.select();

  try {
    if (!document.execCommand("copy")) throw new Error("CLIPBOARD_COPY_FAILED");
  } finally {
    textarea.remove();
  }
}

// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";

import { copyText } from "./clipboard";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("copyText", () => {
  it("uses the Clipboard API when it is available", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    await copyText("https://teamnav.example.com/s/public");

    expect(writeText).toHaveBeenCalledWith("https://teamnav.example.com/s/public");
    expect(execCommand).not.toHaveBeenCalled();
  });

  it("falls back when the Clipboard API rejects the write", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("NotAllowedError"));
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    await copyText("http://192.0.2.10/manage/private");

    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("[data-teamnav-copy-fallback]")).toBeNull();
  });

  it("falls back when the Clipboard API is unavailable on HTTP", async () => {
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    await copyText("http://192.0.2.10/s/public");

    expect(execCommand).toHaveBeenCalledWith("copy");
  });
});

import { describe, expect, it } from "vitest";

import { resolveLocale } from "./i18n";

describe("resolveLocale", () => {
  it("uses a saved preference before browser languages", () => {
    expect(resolveLocale("en", ["zh-CN"])).toBe("en");
    expect(resolveLocale("zh-CN", ["en-US"])).toBe("zh-CN");
  });

  it("uses Chinese for Chinese browsers and English otherwise", () => {
    expect(resolveLocale(null, ["zh-TW", "en-US"])).toBe("zh-CN");
    expect(resolveLocale(null, ["en-US", "zh-CN"])).toBe("en");
    expect(resolveLocale(null, ["fr-FR"])).toBe("en");
  });
});

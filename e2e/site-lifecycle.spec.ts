import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("create, manage, search, and rotate the edit key", async ({ page, browser }) => {
  await page.goto("/create");
  await page.getByLabel("站点名称 *").fill("E2E Team Workspace");
  const captcha = page.locator("#captcha-answer");
  await expect(captcha).toBeVisible();
  const label = await page.locator('label[for="captcha-answer"]').textContent();
  const numbers = label?.match(/(\d+)\s*\+\s*(\d+)/);
  expect(numbers).not.toBeNull();
  await captcha.fill(String(Number(numbers?.[1]) + Number(numbers?.[2])));
  await page.getByRole("button", { name: "创建导航站" }).click();
  await expect(page.getByText("创建完成")).toBeVisible();
  await page.locator('.save-confirm input[type="checkbox"]').check();
  const oldManageUrl = await page.getByTestId("manage-link").getAttribute("href");
  expect(oldManageUrl).toContain("?key=");
  await page.getByTestId("manage-link").click();
  await expect(page.getByText("管理模式")).toBeVisible();

  await page.getByRole("button", { name: "外观" }).click();
  await page.getByLabel("选择品牌色 #2563EB").click();
  await page.getByRole("button", { name: "描边" }).click();
  await page.getByRole("button", { name: "紧凑" }).click();
  await page.getByRole("button", { name: "保存并发布外观" }).click();
  await page.getByRole("button", { name: "内容" }).click();

  await page.getByLabel("分类名称").fill("Engineering");
  await page.getByTitle("添加分类").click();
  await expect(page.locator('.category-name-input[value="Engineering"]')).toBeVisible();
  const sourceHandle = page.getByRole("button", { name: "拖拽 Engineering 分类" });
  const handles = page.getByRole("button", { name: /拖拽 .* 分类/ });
  const categoryCount = await handles.count();
  const targetHandle = handles.nth(categoryCount - 2);
  await sourceHandle.scrollIntoViewIfNeeded();
  const sourceBox = await sourceHandle.boundingBox();
  const targetBox = await targetHandle.boundingBox();
  expect(sourceBox).not.toBeNull();
  expect(targetBox).not.toBeNull();
  await page.mouse.move(sourceBox!.x + sourceBox!.width / 2, sourceBox!.y + sourceBox!.height / 2);
  await page.mouse.down();
  await page.mouse.move(sourceBox!.x + sourceBox!.width / 2 + 10, sourceBox!.y + sourceBox!.height / 2, { steps: 4 });
  await page.mouse.move(targetBox!.x + targetBox!.width / 2, targetBox!.y + targetBox!.height / 2, { steps: 12 });
  await page.mouse.up();
  await expect(page.locator(".category-name-input").nth(categoryCount - 2)).toHaveValue("Engineering");
  const addLink = page.getByTestId("add-link-form");
  await addLink.locator("select").selectOption({ label: "Engineering" });
  await page.getByLabel("链接名称").fill("Team Portal");
  await page.getByLabel("链接 URL").fill("https://example.com/portal");
  await page.getByLabel("链接标签").fill("team, docs");
  await addLink.getByRole("button", { name: "添加链接" }).click();
  const linkRow = page.locator(".manage-link").filter({ hasText: "Team Portal" });
  await expect(linkRow).toBeVisible();
  await linkRow.getByTitle("编辑").click();
  const modal = page.locator(".modal").filter({ hasText: "编辑书签" });
  await modal.locator("input").nth(0).fill("Engineering Portal");
  await modal.getByRole("button", { name: "保存链接" }).click();
  await expect(page.locator(".manage-link").filter({ hasText: "Engineering Portal" })).toBeVisible();

  const batchSection = page.locator("details.editor-section").filter({ hasText: "批量与数据" });
  await batchSection.locator("summary").click();
  await expect(batchSection.locator(".data-tool-row")).toHaveCount(2);
  await expect(batchSection.getByText("站点数据", { exact: true })).toBeVisible();
  await expect(batchSection.getByText("浏览器书签", { exact: true })).toBeVisible();
  await batchSection.locator('input[accept="text/html,.html"]').setInputFiles({
    name: "bookmarks.html",
    mimeType: "text/html",
    buffer: Buffer.from("<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p><DT><H3>Imported Folder</H3><DL><p><DT><A HREF=\"https://example.com/imported\">Imported Link</A></DL><p></DL><p>"),
  });
  await expect(page.getByText("已导入 1 个书签")).toBeVisible();
  const importedFolder = page.locator(".manage-category").filter({
    has: page.locator('.category-name-input[value="Imported Folder"]'),
  });
  await expect(importedFolder.locator(".category-icon-input")).toHaveValue("📁");
  const batchLines = Array.from(
    { length: 12 },
    (_, index) => `Resource ${index + 1} | https://example.com/resource-${index + 1}`,
  ).join("\n");
  await batchSection.locator("textarea").fill(batchLines);
  await batchSection.getByRole("button", { name: "批量添加到所选分类" }).click();
  await expect(page.getByText("批量链接已添加")).toBeVisible();

  const slug = new URL(oldManageUrl!).pathname.split("/").at(-1);
  const publicPage = await page.context().newPage();
  await publicPage.goto(`/s/${slug}`);
  await expect(publicPage.locator(".nav-view")).toHaveClass(/cards-outline/);
  await expect(publicPage.locator(".nav-view")).toHaveClass(/density-compact/);
  await expect(publicPage.locator(".nav-view")).toHaveCSS("--site-accent", "#2563EB");
  await expect(publicPage.locator(".nav-quick-panel")).toHaveCount(0);
  await expect(publicPage.getByText("Resource 12", { exact: true })).toHaveCount(0);
  await publicPage.getByRole("button", { name: "展开其余 1 个" }).click();
  await expect(publicPage.getByText("Resource 12", { exact: true })).toBeVisible();
  await publicPage.getByRole("button", { name: "收起" }).click();
  await expect(publicPage.getByText("Resource 12", { exact: true })).toHaveCount(0);

  const publicSearch = publicPage.getByLabel("搜索导航链接");
  await publicSearch.fill("Resource 12");
  await expect(publicPage.getByText("Resource 12", { exact: true })).toBeVisible();
  await expect(publicPage.locator(".category-toggle")).toHaveCount(0);
  await publicSearch.fill("");
  await publicPage.getByRole("tab", { name: "Engineering", exact: true }).click();
  await expect(publicPage.getByText("Resource 12", { exact: true })).toBeVisible();
  await expect(publicPage.locator(".category-toggle")).toHaveCount(0);
  await publicPage.close();

  await page.getByRole("button", { name: "设置" }).click();
  await page.locator("details.danger-zone summary").click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "轮换私密编辑链接" }).click();
  const newManageUrl = await page.locator(".rotated-url").textContent();
  expect(newManageUrl).toContain("?key=");
  const freshContext = await browser.newContext({ locale: "zh-CN" });
  const verificationPage = await freshContext.newPage();
  await verificationPage.goto(oldManageUrl!);
  await expect(verificationPage.getByText("无法进入管理模式")).toBeVisible();
  await verificationPage.goto(newManageUrl!);
  await expect(verificationPage.getByText("管理模式")).toBeVisible();
  await freshContext.close();
});

test("owner can let anonymous visitors export public bookmarks", async ({ page, browser }) => {
  await page.goto("/create");
  await page.getByLabel("站点名称 *").fill("Public Bookmark Workspace");
  const captcha = page.locator("#captcha-answer");
  const label = await page.locator('label[for="captcha-answer"]').textContent();
  const numbers = label?.match(/(\d+)\s*\+\s*(\d+)/);
  expect(numbers).not.toBeNull();
  await captcha.fill(String(Number(numbers?.[1]) + Number(numbers?.[2])));
  await page.getByRole("button", { name: "创建导航站" }).click();
  await expect(page.getByText("创建完成")).toBeVisible();
  await page.locator('.save-confirm input[type="checkbox"]').check();
  const manageUrl = await page.getByTestId("manage-link").getAttribute("href");
  expect(manageUrl).not.toBeNull();
  const slug = new URL(manageUrl!, page.url()).pathname.split("/").at(-1);
  await page.getByTestId("manage-link").click();
  await expect(page.getByText("管理模式")).toBeVisible();
  await page.getByRole("button", { name: "设置" }).click();
  await page.getByRole("checkbox", { name: "允许访客导出书签" }).check();
  await page.getByRole("button", { name: "保存访问设置" }).click();
  await expect(page.getByText("站点设置已保存")).toBeVisible();

  const visitorContext = await browser.newContext({ acceptDownloads: true, locale: "zh-CN" });
  const visitorPage = await visitorContext.newPage();
  await visitorPage.setViewportSize({ width: 390, height: 844 });
  await visitorPage.goto(`/s/${slug}`);
  await expect(visitorPage.getByRole("button", { name: "导出书签" })).toBeVisible();
  expect(
    await visitorPage.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    ),
  ).toBe(false);
  const downloadPromise = visitorPage.waitForEvent("download");
  await visitorPage.getByRole("button", { name: "导出书签" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(`teamnav-${slug}-bookmarks.html`);
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const content = await readFile(downloadPath!, "utf8");
  expect(content).toContain("<!DOCTYPE NETSCAPE-Bookmark-file-1>");
  expect(content).toContain("Public Bookmark Workspace");
  await visitorContext.close();
});

test("account session restores editing credentials in a new tab", async ({ page, context }) => {
  await page.goto("/account");
  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("邮箱").fill("persistent-owner@example.com");
  await page.getByLabel("密码").fill("correct-horse-battery");
  await page.getByRole("button", { name: "注册并登录" }).click();
  await expect(page.getByRole("heading", { name: "我的工作台" })).toBeVisible();

  await page.goto("/create");
  await page.getByLabel("站点名称 *").fill("Persistent Account Workspace");
  const captcha = page.locator("#captcha-answer");
  const label = await page.locator('label[for="captcha-answer"]').textContent();
  const numbers = label?.match(/(\d+)\s*\+\s*(\d+)/);
  expect(numbers).not.toBeNull();
  await captcha.fill(String(Number(numbers?.[1]) + Number(numbers?.[2])));
  await page.getByRole("button", { name: "创建导航站" }).click();
  await expect(page.getByText("创建完成")).toBeVisible();

  const returningPage = await context.newPage();
  await returningPage.goto("/account");
  await expect(returningPage.getByText("Persistent Account Workspace")).toBeVisible();
  expect(
    await returningPage.evaluate(() => sessionStorage.getItem("teamnav_account_csrf")),
  ).toBeTruthy();
  await returningPage.getByTitle("管理").click();
  await expect(returningPage.getByText("管理模式")).toBeVisible();
  await returningPage.getByRole("button", { name: "设置" }).click();
  await returningPage.getByRole("checkbox", { name: "允许访客导出书签" }).check();
  await returningPage.getByRole("button", { name: "保存访问设置" }).click();
  await expect(returningPage.getByText("站点设置已保存")).toBeVisible();
  await returningPage.close();
});

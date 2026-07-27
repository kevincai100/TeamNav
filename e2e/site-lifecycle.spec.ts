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
  const modal = page.locator(".modal").filter({ hasText: "编辑链接" });
  await modal.locator("input").nth(0).fill("Engineering Portal");
  await modal.getByRole("button", { name: "保存链接" }).click();
  await expect(page.locator(".manage-link").filter({ hasText: "Engineering Portal" })).toBeVisible();

  const slug = new URL(oldManageUrl!).pathname.split("/").at(-1);
  const publicPage = await page.context().newPage();
  await publicPage.goto(`/s/${slug}`);
  await expect(publicPage.locator(".nav-view")).toHaveClass(/cards-outline/);
  await expect(publicPage.locator(".nav-view")).toHaveClass(/density-compact/);
  await expect(publicPage.locator(".nav-view")).toHaveCSS("--site-accent", "#2563EB");
  await publicPage.getByLabel("搜索导航链接").fill("engineering");
  await expect(publicPage.getByText("Engineering Portal")).toBeVisible();
  await publicPage.close();

  await page.getByRole("button", { name: "设置" }).click();
  await page.locator("details.danger-zone summary").click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "轮换私密编辑链接" }).click();
  const newManageUrl = await page.locator(".rotated-url").textContent();
  expect(newManageUrl).toContain("?key=");
  const freshContext = await browser.newContext();
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

  const visitorContext = await browser.newContext({ acceptDownloads: true });
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

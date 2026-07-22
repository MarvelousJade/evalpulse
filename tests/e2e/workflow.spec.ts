import { expect, test } from "@playwright/test";

test("reviewer detects a prompt regression", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Release confidence" })).toBeVisible();

  await page.getByLabel("Project name").fill(`Browser workflow ${Date.now()}`);
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByRole("button", { name: "Project created" })).toBeVisible();

  await page.getByRole("button", { name: "Save immutable versions" }).click();
  await expect(page.getByRole("button", { name: "Versions locked" })).toBeVisible();

  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByText("3", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Run evaluations" }).click();
  await expect(page.getByText("completed", { exact: true })).toHaveCount(2, { timeout: 45_000 });

  await page.getByRole("button", { name: "Compare runs" }).click();
  await expect(page.getByRole("heading", { name: "Regression detected" })).toBeVisible();
  await expect(page.getByText("FAIL", { exact: true })).toBeVisible();
  await expect(page.getByText("pass rate", { exact: true })).toBeVisible();
});


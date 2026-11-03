import { test, expect } from "@playwright/test";
test("workflow graph renders nodes and edges, retains simulation and allows edge removal", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "03 · Operator preview" }).click();
  await page.getByLabel("Simulated scan").fill("PART-001");
  await page.getByRole("button", { name: "Run workflow" }).click();
  await expect(page.locator("output")).toHaveText("PASS · Part accepted");
  await page.getByRole("button", { name: "02 · Workflow" }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(4);
  await expect(page.locator(".react-flow__node").first()).toBeVisible();
  await expect(page.locator(".react-flow__edge")).toHaveCount(3);
  await expect(page.locator(".react-flow__node.visited")).toHaveCount(3);
  await page.locator(".react-flow__edge").first().click();
  await page.keyboard.press("Delete");
  await expect(page.locator(".react-flow__edge")).toHaveCount(2);
  await page.getByRole("button", { name: "03 · Operator preview" }).click();
  await page.getByRole("button", { name: "Run workflow" }).click();
  await expect(page.locator(".message")).toContainText("needs one next edge");
});
test("operator exact scan produces fail result and disabled action cannot execute", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "03 · Operator preview" }).click();
  await page
    .getByRole("textbox", { name: "Part barcode", exact: true })
    .fill("WRONG");
  await page.getByRole("button", { name: "Verify part", exact: true }).click();
  await expect(page.locator("output")).toHaveText("FAIL · Incorrect part");
  await page.getByRole("button", { name: "01 · Station layout" }).click();
  await page.getByRole("button", { name: "Select Action button" }).click();
  await page.getByLabel("Disabled", { exact: true }).check();
  await page.getByRole("button", { name: "03 · Operator preview" }).click();
  await expect(
    page.getByRole("button", { name: "Verify part", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("textbox", { name: "Part barcode", exact: true })
    .press("Enter");
  await expect(page.locator("output")).toBeEmpty();
});

test("editing a scan clears prior result and trace", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "03 · Operator preview" }).click();
  await page.getByLabel("Simulated scan").fill("PART-001");
  await page.getByRole("button", { name: "Run workflow" }).click();
  await expect(page.locator("output")).toContainText("PASS");
  await page.getByLabel("Simulated scan").fill("WRONG");
  await expect(page.locator("output")).toBeEmpty();
  await expect(page.getByText("Run to see each visited step.")).toBeVisible();
});

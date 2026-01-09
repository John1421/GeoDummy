import { test, expect } from '@playwright/test';

test('Botão de ordenação das layers funciona corretamente', async ({ page }) => {
    await page.goto('http://localhost:5173');

    const layers = page.locator('[data-testid^="layer-card-"]');
    await expect(layers).toHaveCount(3);

    const before = await layers.allTextContents();

    await page.getByTestId('layers-reorder-button').click();

    const after = await layers.allTextContents();
    expect(after).not.toEqual(before);

});

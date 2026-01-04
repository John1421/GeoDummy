import { test, expect } from '@playwright/test';

test('Alterar basemap funciona corretamente', async ({ page }) => {
  
  await page.goto('http://localhost:5173');
 
  await page.getByTestId('edit-menu-button').click();
 
  await page.getByTestId('edit-basemap-button').click();
 
  await page.getByTestId('basemap-dropdown').click();
 
  await page.getByTestId('basemap-option-osm').click();

  await page.getByTestId('basemap-save').click();
  
  const tiles = page.locator('img.leaflet-tile');
  await expect(tiles.first()).toBeVisible();
});

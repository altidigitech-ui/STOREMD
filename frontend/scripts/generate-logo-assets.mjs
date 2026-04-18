import sharp from "sharp";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

// Paths resolved from npm script cwd (frontend/).
const SRC = "../storemd_icon_1200x1200.png";
const OUT_ICONS = "public/icons";
const OUT_ROOT = "public";

const PWA_SIZES = [72, 96, 128, 144, 152, 192, 384, 512];
const FAVICON_SIZES = [16, 32, 48];

async function main() {
  await mkdir(OUT_ICONS, { recursive: true });

  // PWA icons (overwrite existing)
  for (const size of PWA_SIZES) {
    await sharp(SRC)
      .resize(size, size, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png()
      .toFile(join(OUT_ICONS, `icon-${size}x${size}.png`));
    console.log(`✓ icon-${size}x${size}.png`);
  }

  // Apple touch icon (180×180 is Apple's preferred)
  await sharp(SRC).resize(180, 180).png().toFile(join(OUT_ROOT, "apple-touch-icon.png"));
  console.log("✓ apple-touch-icon.png");

  // Favicon PNGs
  for (const size of FAVICON_SIZES) {
    await sharp(SRC).resize(size, size).png().toFile(join(OUT_ROOT, `favicon-${size}x${size}.png`));
  }
  console.log("✓ favicon-16, 32, 48");

  // favicon.ico (multi-size ICO — sharp doesn't do ICO natively, so we output 32×32 PNG renamed)
  // For a proper .ico, we'd need `png-to-ico`, but most modern browsers accept PNG as .ico.
  await sharp(SRC).resize(32, 32).png().toFile(join(OUT_ROOT, "favicon.ico"));
  console.log("✓ favicon.ico (32×32 PNG)");

  // Shopify App Store icon (1200×1200 — just copy the source at the correct size)
  await sharp(SRC).resize(1200, 1200).png().toFile(join(OUT_ROOT, "shopify-app-icon.png"));
  console.log("✓ shopify-app-icon.png (1200×1200)");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

import sharp from "sharp";
import { join } from "node:path";

// Paths resolved from npm script cwd (frontend/).
const SRC_LOGO = "../storemd_icon_1200x1200.png";
const OUT = "public/og-image.png";
const W = 1200;
const H = 630;

async function main() {
  // Dark background with subtle gradient feel (solid is fine for OG)
  const bg = Buffer.from(
    `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="g" cx="30%" cy="50%" r="80%">
          <stop offset="0%" stop-color="#0a0a0f"/>
          <stop offset="100%" stop-color="#020205"/>
        </radialGradient>
      </defs>
      <rect width="${W}" height="${H}" fill="url(#g)"/>
      <text x="360" y="270" font-family="system-ui, -apple-system, sans-serif" font-size="72" font-weight="800" fill="#ffffff" letter-spacing="-2">
        One app.
      </text>
      <text x="360" y="360" font-family="system-ui, -apple-system, sans-serif" font-size="72" font-weight="800" fill="#ffffff" letter-spacing="-2">
        Five killed.
      </text>
      <text x="360" y="450" font-family="system-ui, -apple-system, sans-serif" font-size="72" font-weight="800" fill="#06b6d4" letter-spacing="-2">
        Zero regrets.
      </text>
      <text x="360" y="520" font-family="system-ui, -apple-system, sans-serif" font-size="28" font-weight="400" fill="#94a3b8">
        The Shopify app that uninstalls the others.
      </text>
    </svg>`
  );

  // Logo scaled to 240×240 on the left
  const logoBuffer = await sharp(SRC_LOGO).resize(240, 240).png().toBuffer();

  await sharp(bg)
    .composite([
      { input: logoBuffer, left: 80, top: 195 },
    ])
    .png()
    .toFile(OUT);

  console.log(`✓ og-image.png (${W}×${H})`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

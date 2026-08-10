import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import sharp from "sharp";
import { readFileSync } from "node:fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const svgPath = resolve(__dirname, "..", "public", "shred-mark.svg");
const publicDir = resolve(__dirname, "..", "public");
const svgBuffer = readFileSync(svgPath);

async function generate() {
  await sharp(svgBuffer)
    .resize(192, 192)
    .png()
    .toFile(resolve(publicDir, "pwa-192x192.png"));

  await sharp(svgBuffer)
    .resize(512, 512)
    .png()
    .toFile(resolve(publicDir, "pwa-512x512.png"));

  const padding = 64;
  const iconSize = 512 - padding * 2;
  const iconBuffer = await sharp(svgBuffer)
    .resize(iconSize, iconSize)
    .png()
    .toBuffer();

  await sharp({
    create: {
      width: 512,
      height: 512,
      channels: 4,
      background: { r: 26, g: 26, b: 46, alpha: 1 },
    },
  })
    .composite([{ input: iconBuffer, top: padding, left: padding }])
    .png()
    .toFile(resolve(publicDir, "maskable-512x512.png"));

  console.log("Icons generated successfully.");
}

generate().catch((err) => {
  console.error("Icon generation failed:", err);
  process.exit(1);
});

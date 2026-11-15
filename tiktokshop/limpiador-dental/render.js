// Render anim.html to video frames with Playwright and pipe them to ffmpeg.
// Usage: node render.js <fonts_dir> <timing.json> <out.mp4> [still times...]
//   with still times it writes <out.mp4>.<t>.jpg test frames instead of the video
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const [fonts, timingPath, out, ...stills] = process.argv.slice(2);
const FPS = 30;

(async () => {
  const timing = JSON.parse(fs.readFileSync(timingPath, "utf8"));
  const html = fs.readFileSync(path.join(__dirname, "anim.html"), "utf8")
    .replaceAll("FONTS/", "file://" + path.resolve(fonts) + "/");
  const tmp = path.join(path.dirname(path.resolve(out)), ".anim_tmp.html");
  fs.writeFileSync(tmp, html);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on("pageerror", e => { console.error("PAGE ERROR", e.message); process.exitCode = 1; });
  await page.addInitScript(t => { window.TIMING = t; }, timing);
  await page.goto("file://" + tmp);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(async () => { for (const f of ["138px Hook", "800 76px Cap", "italic 94px Emph"]) await document.fonts.load(f); });

  if (stills.length) {
    for (const s of stills) {
      await page.evaluate(t => window.renderFrame(t), parseFloat(s));
      await page.screenshot({ path: `${out}.${s}.jpg`, type: "jpeg", quality: 88 });
    }
  } else {
    const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
      "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", String(FPS), out], { stdio: ["pipe", "inherit", "inherit"] });
    const n = Math.round(timing.duration * FPS);
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => window.renderFrame(t), i / FPS);
      const buf = await page.screenshot({ type: "jpeg", quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
      if (i % 90 === 0) console.log(`frame ${i}/${n}`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on("close", r));
  }
  await browser.close();
  fs.unlinkSync(tmp);
})();

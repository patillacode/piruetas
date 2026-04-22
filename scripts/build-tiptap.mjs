import esbuild from "esbuild";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { mkdirSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outfile = resolve(__dirname, "../app/static/js/vendor/tiptap.bundle.js");
mkdirSync(resolve(__dirname, "../app/static/js/vendor"), { recursive: true });

await esbuild.build({
  entryPoints: [resolve(__dirname, "tiptap-entry.js")],
  bundle: true,
  format: "esm",
  outfile,
  minify: true,
  treeShaking: true,
});

console.log(`Built ${outfile}`);

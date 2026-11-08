# Third-party notices

The MIT license in the repository root applies to the Audio-to-Cinema Lab source code and project documentation authored for this repository. It does not relicense the recording, lyrics, model weights, generated media, or third-party tools used during production.

## HyperFrames sample project

`projects/2026-11-08/one-last-kiss/edit/hyperframes/` contains the following third-party resources:

- **GSAP 3.15.0** — the bundled `assets/gsap.min.js` distribution retains GreenSock's copyright and is subject to the [GreenSock Standard License](https://gsap.com/standard-license/). It is not relicensed under this repository's MIT license.
- **Noto Sans CJK SC / JP** — the bundled CJK font files are from the Noto CJK project. The applicable upstream notice and license text is preserved beside the font files as [`NotoCJK-LICENSE.txt`](projects/2026-11-08/one-last-kiss/edit/hyperframes/assets/fonts/NotoCJK-LICENSE.txt).
- **DejaVu Sans** — the bundled `OpeningSans.woff2` file identifies as DejaVu Sans. The upstream notice and license text is preserved as [`DejaVuSans-LICENSE.txt`](projects/2026-11-08/one-last-kiss/edit/hyperframes/assets/fonts/DejaVuSans-LICENSE.txt).
- **HyperFrames CLI** — `package.json` records `hyperframes@0.9.7` as the rendering tool used by the source project. The CLI is a runtime dependency and is not bundled or relicensed here.

The ComfyUI graphs, custom nodes, model checkpoints, LoRAs, source recordings and complete lyric text have their own licenses or rights conditions. The public migration records their provenance and selected parameters while omitting private or large source media.

## NCM input adapter

The NCM input adapter follows the classic NCM container decoding flow implemented by [NCM Breaker](https://github.com/KaffuAlcaid/ncmBreaker), release `0.4.1`, commit `8e86dc6a0ff71fd60785ae38eed23efb2f3e9253`. NCM Breaker is Copyright (c) 2026 KaffuAlcaid and is distributed under the MIT License. This repository does not include its Java application or a copy of its binary distribution; the Python adapter keeps the upstream attribution and uses the algorithm to decode locally supplied files.

# Third-party notices

The MIT license in the repository root applies to the Audio-to-Cinema Lab source code and project documentation authored for this repository. It does not relicense the recording, lyrics, model weights, generated media, or third-party tools used during production.

## Historical production resources

The concrete HyperFrames sample was removed from current Git tracking during the local-project separation. Its files and adjacent notices remain in the original local production directory and the historical commits. No GSAP or font binaries are included in the current reusable recipe package.

The historical sample used GSAP 3.15.0, Noto Sans CJK SC / JP, DejaVu Sans and HyperFrames CLI 0.9.7. Their existing upstream notices and licenses remain with those local files; removing Git tracking does not alter their attribution or license terms.

ComfyUI nodes, model checkpoints, LoRAs, recordings and lyrics retain their own provenance and terms. Concrete references, parameters and media are recorded within local productions. The root repository license does not relicense them.

## NCM input adapter

The NCM input adapter follows the classic NCM container decoding flow implemented by [NCM Breaker](https://github.com/KaffuAlcaid/ncmBreaker), release `0.4.1`, commit `8e86dc6a0ff71fd60785ae38eed23efb2f3e9253`. NCM Breaker is Copyright (c) 2026 KaffuAlcaid and is distributed under the MIT License. This repository does not include its Java application or a copy of its binary distribution; the Python adapter keeps the upstream attribution and uses the algorithm to decode locally supplied files.

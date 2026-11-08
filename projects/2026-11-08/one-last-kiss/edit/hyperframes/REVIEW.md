# Subtitle review

The original MV is the visual source. The added graphic is a fixed two-line subtitle: original above Chinese, white regular-weight Noto Sans with a thin black outline. No animation or per-word styling.

Inspected full-size HyperFrames snapshots on bright water, a bright morning street, and a dark dusk street; both lines are readable, inside the frame, and below the faces. English, Japanese and Chinese glyphs render with bundled font subsets. Runtime checks report no overflow, occlusion or contrast errors. The synchronized subtitle audit covers 142 seek positions including cue starts, ends, midpoints and instrumental gaps; both lines share one visible interval.

Caption times are authored one microsecond before their target frame boundary to avoid a decimal serialization error shifting a cue by one frame. This is below one frame and does not change the intended timing. Render and external subtitle timecodes remain on the 24 fps grid.


## Opening credits revision

The clean picture master was rebuilt from the original shots to remove the old burned title. The HyperFrames opening graphics layer shows only the song title `ONE LAST KISS`, plus performer, lyricist and composer credits for 宇多田ヒカル. The title is 104 px, performer 30 px, writing credits 28 px; all fonts are bundled. All text is fully visible from frame 0, holds through 5.25 s, fades with a seekable sine.inOut opacity tween, and is fully transparent by 7 s before the first cut at 7.2083 s.

Inspected 0, 2, 4, 5.25, 6.125, 7, 8 and 28 s: title appears over the initial black frame; the picture fades in under it; all text sits in the sky above the train; no title survives into the second shot or the lyric section.

Final validation: the full-film check and explicit opening-time check pass with zero errors or warnings. Non-monotonic opening seeks pass at 17 samples, including repeated returns to 0 s. The delivered render matches the browser snapshots at 0, 3, 6.125, 7 and 28 s; frame 0 contains both the title and the credits, and the title is absent at 7 s. The 142-sample bilingual seek audit and rendered-pixel checks for all 45 cue groups plus seven instrumental gaps pass.

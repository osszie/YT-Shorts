import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption, styleSchema} from './schema';
import {z} from 'zod';

type Props = {
  captions: Caption[];
  style: z.infer<typeof styleSchema>;
};

// Modern YouTube-Shorts / CapCut caption style: a few words at a time, big bold
// ALL-CAPS, centered, with the currently-spoken word highlighted in a rounded
// colour box that pops as it lands ("karaoke"). Falls back to whole-chunk
// emphasis if a track has no per-word timings.
export const Captions: React.FC<Props> = ({captions, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const active = captions.find((c) => t >= c.start && t < c.end);
  if (!active) {
    return null;
  }

  const words =
    active.words && active.words.length > 0
      ? active.words
      : active.text
          .split(/\s+/)
          .map((w) => ({word: w, start: active.start, end: active.end}));

  // Whole-group entrance pop.
  const enter = spring({
    frame: frame - Math.round(active.start * fps),
    fps,
    config: {damping: 14, stiffness: 200, mass: 0.5},
  });
  const groupScale = 0.92 + 0.08 * enter;

  const outline =
    '0 0 7px rgba(0,0,0,0.95), 5px 5px 0 #000, -5px -5px 0 #000, 5px -5px 0 #000, -5px 5px 0 #000';

  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div
        style={{
          transform: `scale(${groupScale})`,
          maxWidth: 960,
          padding: '0 48px',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '0.16em 0.28em',
          textAlign: 'center',
          fontFamily: style.fontFamily,
          fontSize: Math.round(style.fontSize * 1.18),
          fontWeight: 900,
          lineHeight: 1.12,
          letterSpacing: 1,
          textTransform: 'uppercase',
        }}
      >
        {words.map((w, i) => {
          const isActive = t >= w.start && t < w.end;
          const wordPop = spring({
            frame: frame - Math.round(w.start * fps),
            fps,
            config: {damping: 11, stiffness: 260, mass: 0.5},
          });
          const scale = isActive ? 0.86 + 0.2 * Math.min(1, wordPop) : 1;
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                transform: `scale(${scale})`,
                color: isActive ? '#000' : style.primary,
                backgroundColor: isActive ? style.highlight : 'transparent',
                borderRadius: 14,
                padding: isActive ? '2px 16px' : '2px 0',
                textShadow: isActive ? 'none' : outline,
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

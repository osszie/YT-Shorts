import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption, styleSchema} from './schema';
import {z} from 'zod';

type Props = {
  captions: Caption[];
  style: z.infer<typeof styleSchema>;
};

// CapCut-style centered caption track: show the active phrase chunk, pop it in
// with a spring, emphasize ALL-CAPS words with the highlight colour.
export const Captions: React.FC<Props> = ({captions, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const active = captions.find((c) => t >= c.start && t < c.end);
  if (!active) {
    return null;
  }

  const enter = spring({
    frame: frame - Math.round(active.start * fps),
    fps,
    config: {damping: 12, stiffness: 220, mass: 0.6},
  });
  const scale = 0.8 + 0.2 * enter; // 0.8 -> 1.0 with a little overshoot

  const words = active.text.split(/\s+/);

  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', top: '12%'}}>
      <div
        style={{
          transform: `scale(${scale})`,
          maxWidth: 980,
          textAlign: 'center',
          fontFamily: style.fontFamily,
          fontSize: style.fontSize,
          fontWeight: 800,
          lineHeight: 1.1,
          color: style.primary,
          textShadow:
            '0 0 6px rgba(0,0,0,0.9), 4px 4px 0 #000, -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000',
        }}
      >
        {words.map((w, i) => {
          const isEmphasis = w.length >= 3 && w === w.toUpperCase() && /[A-Z]/.test(w);
          return (
            <span key={i} style={{color: isEmphasis ? style.highlight : style.primary}}>
              {w}
              {i < words.length - 1 ? ' ' : ''}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

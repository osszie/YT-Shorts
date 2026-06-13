import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Loop,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {ShortProps} from './schema';
import {Captions} from './Captions';

export const Short: React.FC<ShortProps> = ({
  audioSrc,
  backgroundSrc,
  captions,
  title,
  introSfx,
  bgDurationInFrames,
  style,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // Subtle zoom + upward drift (the same "alive background" feel as the FFmpeg path).
  const zoom = interpolate(frame, [0, durationInFrames], [1.06, 1.12], {
    extrapolateRight: 'clamp',
  });
  const drift = interpolate(frame, [0, durationInFrames], [0, -40], {
    extrapolateRight: 'clamp',
  });
  // Optional intro "punch": a quick extra scale on the first ~8 frames.
  const introPunch = introSfx
    ? interpolate(frame, [0, 4, 8], [1.05, 1.0, 1.0], {extrapolateRight: 'clamp'})
    : 1;

  const progress = interpolate(frame, [0, durationInFrames], [0, 100], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {/* Background (cover-fit, looped if shorter than the audio). */}
      <AbsoluteFill
        style={{
          transform: `scale(${zoom * introPunch}) translateY(${drift}px)`,
        }}
      >
        <Loop durationInFrames={Math.max(1, bgDurationInFrames)}>
          <OffthreadVideo
            src={staticFile(backgroundSrc)}
            muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </Loop>
      </AbsoluteFill>

      <Audio src={staticFile(audioSrc)} />

      {/* Top progress bar that fills over the video. */}
      <AbsoluteFill style={{justifyContent: 'flex-start'}}>
        <div style={{height: 10, width: `${progress}%`, backgroundColor: '#37FF37'}} />
      </AbsoluteFill>

      {/* Small, low-key subject header (brand signature, not clickbait). */}
      <AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center', paddingTop: 120}}>
        <div
          style={{
            fontFamily: style.fontFamily,
            fontSize: 34,
            color: 'rgba(255,255,255,0.85)',
            textTransform: 'uppercase',
            letterSpacing: 2,
            textShadow: '0 2px 8px rgba(0,0,0,0.8)',
            maxWidth: 900,
            textAlign: 'center',
          }}
        >
          {title}
        </div>
      </AbsoluteFill>

      <Captions captions={captions} style={style} />
    </AbsoluteFill>
  );
};

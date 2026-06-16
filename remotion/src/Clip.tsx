import React from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {ClipProps} from './schema';
import {Captions} from './Captions';

// A repurposed clip: the (already 9:16-reframed) source video full-frame, its own
// audio, plus the same karaoke captions as generated Shorts. No zoom/drift/header
// and no hook — clips are existing moments, not written content.
export const Clip: React.FC<ClipProps> = ({videoSrc, captions, style}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const progress = interpolate(frame, [0, durationInFrames], [0, 100], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <OffthreadVideo
        src={staticFile(videoSrc)}
        style={{width: '100%', height: '100%', objectFit: 'cover'}}
      />
      {/* Subtle top progress bar (same brand cue as Shorts). */}
      <AbsoluteFill style={{justifyContent: 'flex-start'}}>
        <div style={{height: 8, width: `${progress}%`, backgroundColor: '#37FF37'}} />
      </AbsoluteFill>
      <Captions captions={captions} style={style} />
    </AbsoluteFill>
  );
};

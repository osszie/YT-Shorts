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

const FRAME_W = 1080;
const FRAME_H = 1920;

// A repurposed clip: the landscape source segment, scaled to fill the 9:16 frame
// height and PANNED horizontally to follow the speaker (faceTrack), smoothly
// interpolated per frame. Its own audio + karaoke captions. No zoom/header/hook.
export const Clip: React.FC<ClipProps> = ({videoSrc, sourceW, sourceH, faceTrack, captions, style}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const t = frame / fps;

  const scale = FRAME_H / sourceH;
  const scaledW = sourceW * scale;

  // Normalized face x at time t (smooth follow); default centered.
  let cxNorm = 0.5;
  if (faceTrack && faceTrack.length >= 2) {
    cxNorm = interpolate(t, faceTrack.map((p) => p.t), faceTrack.map((p) => p.cx), {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  } else if (faceTrack && faceTrack.length === 1) {
    cxNorm = faceTrack[0].cx;
  }

  // Translate so the face sits at frame center, clamped to keep the frame covered.
  let tx = FRAME_W / 2 - cxNorm * scaledW;
  tx = Math.min(0, Math.max(FRAME_W - scaledW, tx));

  const progress = interpolate(frame, [0, durationInFrames], [0, 100], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: 'black', overflow: 'hidden'}}>
      <div style={{position: 'absolute', width: scaledW, height: FRAME_H, transform: `translateX(${tx}px)`}}>
        <OffthreadVideo src={staticFile(videoSrc)} style={{width: '100%', height: '100%'}} />
      </div>
      <AbsoluteFill style={{justifyContent: 'flex-start'}}>
        <div style={{height: 8, width: `${progress}%`, backgroundColor: '#37FF37'}} />
      </AbsoluteFill>
      <Captions captions={captions} style={style} />
    </AbsoluteFill>
  );
};

import React from 'react';
import {Composition} from 'remotion';
import {Short} from './Short';
import {shortSchema, ShortProps} from './schema';

// Defaults let `remotion studio` open without external props. The Python
// renderer overrides everything via --props and sizes the timeline from
// durationInFrames / fps in the props.
const defaultProps: ShortProps = {
  audioSrc: 'voice.mp3',
  backgroundSrc: 'background.mp4',
  captions: [
    {text: 'This is a preview caption', start: 0, end: 1.5},
    {text: 'rendered with Remotion', start: 1.5, end: 3},
  ],
  title: 'the hidden detail of everyday things',
  introSfx: true,
  fps: 30,
  durationInFrames: 90,
  bgDurationInFrames: 300,
  style: {
    primary: '#FFFF00',
    highlight: '#FFA500',
    fontFamily: 'Arial',
    fontSize: 72,
  },
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Short"
      component={Short}
      schema={shortSchema}
      defaultProps={defaultProps}
      width={1080}
      height={1920}
      fps={defaultProps.fps}
      durationInFrames={defaultProps.durationInFrames}
      calculateMetadata={({props}) => ({
        durationInFrames: props.durationInFrames,
        fps: props.fps,
      })}
    />
  );
};

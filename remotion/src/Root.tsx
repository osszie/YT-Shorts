import React from 'react';
import {Composition} from 'remotion';
import {Short} from './Short';
import {Clip} from './Clip';
import {shortSchema, ShortProps, clipSchema, ClipProps} from './schema';

// Defaults let `remotion studio` open without external props. The Python
// renderer overrides everything via --props and sizes the timeline from
// durationInFrames / fps in the props.
const defaultProps: ShortProps = {
  audioSrc: 'voice.mp3',
  backgroundSrc: 'background.mp4',
  captions: [
    {
      text: 'THIS IS A',
      start: 0,
      end: 1.5,
      words: [
        {word: 'THIS', start: 0, end: 0.5},
        {word: 'IS', start: 0.5, end: 0.9},
        {word: 'A', start: 0.9, end: 1.5},
      ],
    },
    {
      text: 'PREVIEW CAPTION',
      start: 1.5,
      end: 3,
      words: [
        {word: 'PREVIEW', start: 1.5, end: 2.3},
        {word: 'CAPTION', start: 2.3, end: 3},
      ],
    },
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

const clipDefaultProps: ClipProps = {
  videoSrc: 'clip.mp4',
  captions: defaultProps.captions,
  fps: 30,
  durationInFrames: 90,
  style: defaultProps.style,
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
      <Composition
        id="Clip"
        component={Clip}
        schema={clipSchema}
        defaultProps={clipDefaultProps}
        width={1080}
        height={1920}
        fps={clipDefaultProps.fps}
        durationInFrames={clipDefaultProps.durationInFrames}
        calculateMetadata={({props}) => ({
          durationInFrames: props.durationInFrames,
          fps: props.fps,
        })}
      />
    </>
  );
};

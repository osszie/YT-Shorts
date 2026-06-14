import {z} from 'zod';

// Mirrors the props built in pipeline/media/remotion.py. Times are in seconds.
export const wordSchema = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number(),
});

export const captionSchema = z.object({
  text: z.string(),
  start: z.number(),
  end: z.number(),
  // Per-word timings for word-by-word (karaoke) highlighting. Optional so older
  // tracks (or the FFmpeg path) still validate.
  words: z.array(wordSchema).optional().default([]),
});

export const styleSchema = z.object({
  primary: z.string(),
  highlight: z.string(),
  fontFamily: z.string(),
  fontSize: z.number(),
});

export const shortSchema = z.object({
  audioSrc: z.string(),
  backgroundSrc: z.string(),
  captions: z.array(captionSchema),
  title: z.string(),
  introSfx: z.boolean(),
  fps: z.number(),
  durationInFrames: z.number(),
  bgDurationInFrames: z.number(),
  style: styleSchema,
});

export type ShortProps = z.infer<typeof shortSchema>;
export type Caption = z.infer<typeof captionSchema>;

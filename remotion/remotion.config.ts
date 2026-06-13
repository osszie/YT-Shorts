import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// H.264 / yuv420p so the output is YouTube-ready straight out of the renderer.
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');

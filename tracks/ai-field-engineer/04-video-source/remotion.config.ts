import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// Software GL is the safe default on a headless Linux box (incl. DGX Spark arm64).
Config.setChromiumOpenGlRenderer('swangle');

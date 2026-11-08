export {
  DETECT_THUMB_W,
  DETECT_THUMB_H,
  DETECT_FRAME_TARGET_W,
  startUserMedia,
  describeCameraFailure,
  ensureCanvas,
  prepareDetectFrame,
  sampleDetectThumb,
  captureFaceCrop,
  scaleDetectionBoxes,
  dataURLtoFile,
} from './kiosk-camera';
export type { UserMediaResult, FaceCropOpts, CameraFailureKind, CameraRecoveryInfo } from './kiosk-camera';

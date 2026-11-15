import { Injectable } from '@angular/core';
import type * as OrtTypes from 'onnxruntime-web';

/**
 * Client-side Voice Activity Detection using Silero VAD ONNX (/models/silero_vad.onnx)
 * with an automatic RMS energy fallback.
 */
@Injectable({ providedIn: 'root' })
export class SileroVadService {
  private session: OrtTypes.InferenceSession | null = null;
  private ort: typeof OrtTypes | null = null;
  private stateTensor: OrtTypes.Tensor | null = null;
  private srTensor: OrtTypes.Tensor | null = null;
  private loadFailed = false;

  async init(): Promise<boolean> {
    if (this.session) return true;
    if (this.loadFailed) return false;
    try {
      const ort = await import('onnxruntime-web');
      ort.env.wasm.wasmPaths = '/ort/';
      ort.env.wasm.numThreads = 1;
      this.ort = ort;
      this.session = await ort.InferenceSession.create('/models/silero_vad.onnx', {
        executionProviders: ['wasm'],
      });
      this.resetState();
      return true;
    } catch {
      this.loadFailed = true;
      return false;
    }
  }

  resetState(): void {
    if (!this.ort) return;
    this.stateTensor = new this.ort.Tensor('float32', new Float32Array(2 * 1 * 128), [2, 1, 128]);
    this.srTensor = new this.ort.Tensor('int64', BigInt64Array.from([16000n]), [1]);
  }

  /** Returns speech probability [0..1] for a 512-sample 16kHz Float32Array frame. */
  async isSpeech(frame512: Float32Array): Promise<number> {
    if (this.session && this.ort && this.stateTensor && this.srTensor) {
      try {
        const input = new this.ort.Tensor('float32', frame512, [1, frame512.length]);
        const out = await this.session.run({
          input,
          state: this.stateTensor,
          sr: this.srTensor,
        });
        if (out['stateN']) {
          this.stateTensor = out['stateN'];
        }
        const prob = Number(out['output']?.data?.[0] ?? 0);
        return Number.isFinite(prob) ? prob : 0;
      } catch {
        // fall through to RMS
      }
    }
    let sum = 0;
    for (let i = 0; i < frame512.length; i++) {
      sum += frame512[i]! * frame512[i]!;
    }
    const rms = Math.sqrt(sum / Math.max(1, frame512.length));
    return Math.min(1, rms * 12);
  }
}

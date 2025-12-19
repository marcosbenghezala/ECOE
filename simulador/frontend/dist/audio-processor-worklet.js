/**
 * AudioWorklet Processor para captura de audio
 * Reemplazo moderno de ScriptProcessorNode (deprecado)
 */

class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs) {
    const input = inputs[0];

    if (input.length > 0) {
      const channel = input[0];

      for (let i = 0; i < channel.length; i++) {
        this.buffer[this.bufferIndex++] = channel[i];

        // Cuando el buffer está lleno, enviarlo
        if (this.bufferIndex >= this.bufferSize) {
          this.port.postMessage({
            type: 'audioData',
            samples: this.buffer.slice(0)
          });
          this.bufferIndex = 0;
        }
      }
    }

    // Mantener el procesador activo
    return true;
  }
}

registerProcessor('audio-capture-processor', AudioCaptureProcessor);

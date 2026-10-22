// Aviso sonoro de pedido nuevo, generado con Web Audio (sin archivos de audio).
// Los navegadores solo dejan sonar tras una interacción del usuario; si todavía
// no la hubo, el aviso simplemente no suena (y el toast sigue apareciendo).
let contexto: AudioContext | null = null;

function obtenerContexto(): AudioContext | null {
  try {
    contexto ??= new AudioContext();
    if (contexto.state === "suspended") void contexto.resume();
    return contexto;
  } catch {
    return null;
  }
}

/** Dos notas cortas y agradables, tipo campanilla de cocina. */
export function sonarNuevoPedido() {
  const audio = obtenerContexto();
  if (!audio) return;
  const inicio = audio.currentTime + 0.02;
  [880, 1174.66].forEach((frecuencia, i) => {
    const oscilador = audio.createOscillator();
    const volumen = audio.createGain();
    const t = inicio + i * 0.16;
    oscilador.type = "sine";
    oscilador.frequency.value = frecuencia;
    volumen.gain.setValueAtTime(0.0001, t);
    volumen.gain.exponentialRampToValueAtTime(0.22, t + 0.02);
    volumen.gain.exponentialRampToValueAtTime(0.0001, t + 0.38);
    oscilador.connect(volumen).connect(audio.destination);
    oscilador.start(t);
    oscilador.stop(t + 0.4);
  });
}

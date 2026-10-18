export const cameraPreferenceKey = "modemon-go:playable:camera-preference:v1";
export type CameraPreference = "enabled" | "disabled" | "unset";
type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;

export class CameraPreferences {
  private forcedOff = false;
  private storage: () => Storage;
  constructor(storage: () => Storage) { this.storage = storage; }

  read(): CameraPreference {
    if (this.forcedOff) return "disabled";
    try {
      const storage = this.storage();
      const value = storage.getItem(cameraPreferenceKey);
      // Do not automatically open a camera if this browser cannot save a later
      // reversal. No unrelated storage or progress keys are read or changed.
      if (value === "enabled") storage.setItem(cameraPreferenceKey, value);
      return value === "enabled" || value === "disabled" ? value : "unset";
    } catch {
      return "unset";
    }
  }

  write(value: Exclude<CameraPreference, "unset">): boolean {
    this.forcedOff = value === "disabled";
    try {
      this.storage().setItem(cameraPreferenceKey, value);
      return true;
    } catch {
      return false;
    }
  }
}

export const cameraPreferences = new CameraPreferences(() => localStorage);
// A permission prompt may outlive its encounter. Never overlap it with a new
// request, even when React unmounts and replaces the original scene.
const requestGate = { busy: false };
export type CameraState = { status: string; pending: boolean; active: boolean };
export const cameraOff: CameraState = {
  status: "Camera off. The non-camera encounter is available.", pending: false, active: false,
};
type Dependencies = {
  preferences: CameraPreferences;
  video: () => Pick<HTMLVideoElement, "srcObject" | "play"> | null;
  getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  available: () => boolean;
  hidden: () => boolean;
  changed: (state: CameraState) => void;
  gate?: { busy: boolean };
};

export class EncounterCamera {
  private stream: MediaStream | null = null;
  private generation = 0;
  private mounted = true;
  private pending = false;
  private state = { ...cameraOff };
  private gate: { busy: boolean };
  private deps: Dependencies;
  constructor(deps: Dependencies) { this.deps = deps; this.gate = deps.gate ?? requestGate; }

  private emit(status: string, active = false) {
    this.state = { status, active, pending: this.pending };
    if (this.mounted) this.deps.changed(this.state);
  }

  private stop() {
    this.generation++;
    const stream = this.stream;
    this.stream = null;
    stream?.getTracks().forEach((track) => track.stop());
    const video = this.deps.video();
    if (video && video.srcObject === stream) video.srcObject = null;
  }

  private current(token: number) {
    return this.mounted && token === this.generation && !this.deps.hidden();
  }

  async autoStart() {
    if (this.deps.preferences.read() === "enabled") await this.start(false);
  }

  async start(explicit = true) {
    if (!this.mounted || this.pending || this.deps.hidden() || this.stream) return;
    if (this.gate.busy) {
      this.emit("A previous camera request is still closing. Try Enable camera again.");
      return;
    }
    this.stop();
    const token = this.generation;
    this.pending = this.gate.busy = true;
    this.emit("Requesting camera permission...");
    try {
      if (!this.deps.available()) throw Error("Camera requires a supported HTTPS browser.");
      const camera = await this.deps.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
      if (!this.current(token)) {
        camera.getTracks().forEach((track) => track.stop());
        return;
      }
      this.stream = camera;
      const video = this.deps.video();
      if (!video) throw Error("Encounter closed");
      video.srcObject = camera;
      await video.play();
      if (!this.current(token)) {
        if (this.stream === camera) this.stop();
        return;
      }
      const saved = !explicit || this.deps.preferences.write("enabled");
      this.emit("Camera active. No video is recorded or uploaded." +
        (saved ? "" : " Camera preference could not be saved in this browser."), true);
    } catch {
      // A late rejection must not change a newer off choice or update an exited
      // scene. Permission/playback failure disables future automatic attempts.
      if (this.current(token)) {
        this.stop();
        this.deps.preferences.write("disabled");
        this.emit("Camera unavailable or denied. Use the non-camera encounter below.");
      } else if (this.stream) this.stop();
    } finally {
      this.pending = this.gate.busy = false;
      this.emit(this.state.status, this.state.active);
    }
  }

  disable() {
    const saved = this.deps.preferences.write("disabled");
    this.stop();
    this.emit("Non-camera encounter." + (saved ? "" : " Camera preference could not be saved in this browser."));
  }

  pause() {
    this.stop();
    this.emit("Camera paused while the page is hidden.");
  }

  dispose() {
    this.mounted = false;
    this.stop();
  }
}

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Camera,
  CameraOff,
  Compass,
  MapPin,
  BookOpen,
  Settings,
  X,
  LocateFixed,
} from "lucide-react";
import L from "leaflet";
import type { FeatureCollection } from "geojson";
import "leaflet/dist/leaflet.css";
import "./style.css";
import bundle from "./data/runtime.json";
import QuizFeedback from "./QuizFeedback";
import DexEntry from "./DexEntry";
import {
  approximateDistance,
  extraLocationSafety,
  markerLabel,
  placeLabel,
  proximityCopy,
  publicLocationSafety,
  rarityLabel,
  regionLabel,
} from "./presentation";
import { safetyNotice } from "../../src/content/safety";
import {
  answerQuestion,
  startAttempt,
  changeDifficulty,
  attemptRules,
  buildWorld,
  dayKey,
  distance,
  emptyProgress,
  habitatAt,
  interaction,
  persist,
  questionsForAttempt,
  readProgress,
  type Fix,
  type Progress,
  type Runtime,
  type Spawn,
} from "./engine";
import { quizModes, type Difficulty } from "./quizzes";

const data = bundle as unknown as Runtime;
const safetyKey = "modemon-go:playable:safety:v1";
const modeKey = "modemon-go:playable:mode";
const colors = { common: "#147d65", rare: "#2462cd", signature: "#ba7600" };
const title = (s: string) =>
  Object.entries(data.habitats).find(([, v]) => v === s)?.[0] ?? s;
const read = (key: string) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};
function ErrorText({ children }: { children: React.ReactNode }) {
  return (
    <p className="error" role="alert">
      {children}
    </p>
  );
}

function Map({
  world,
  position,
  onSelect,
  city,
}: {
  world: Spawn[];
  position: Fix | null;
  onSelect: (s: Spawn) => void;
  city: string;
}) {
  const container = useRef<HTMLDivElement>(null),
    map = useRef<L.Map | null>(null);
  const [tileError, setTileError] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    const m = L.map(container.current, { zoomControl: false }).setView(
      city === "Durham" ? [35.999, -78.918] : [35.7796, -78.6382],
      14,
    );
    map.current = m;
    L.control.zoom({ position: "bottomright" }).addTo(m);
    const tiles = L.tileLayer(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    ).addTo(m);
    tiles.on("tileerror", () => setTileError(true));
    tiles.on("load", () => setTileError(false));
    L.geoJSON(
      {
        type: "FeatureCollection",
        features: data.regions,
      } as FeatureCollection,
      {
        style: { color: "#234a41", weight: 2, fillOpacity: 0.03 },
        onEachFeature: (f, l) => l.bindTooltip(f.properties.display_name),
      },
    ).addTo(m);
    return () => {
      map.current = null;
      m.remove();
    };
  }, [city]);
  useEffect(() => {
    if (!map.current) return;
    const group = L.layerGroup().addTo(map.current);
    for (const spawn of world) {
      const color = colors[spawn.rarity as keyof typeof colors];
      const icon = L.divIcon({
        className: "encounter-pin",
        html: `<span class="pin ${spawn.rarity}" style="--pin:${color}" aria-hidden="true">?</span>`,
        iconSize: [36, 42],
        iconAnchor: [18, 42],
      });
      const marker = L.marker([spawn.poi.lat, spawn.poi.lon], {
        icon,
        alt: markerLabel(data, spawn),
        title: markerLabel(data, spawn),
      }).addTo(group);
      marker.on("click", () => onSelect(spawn));
      const el = marker.getElement();
      el?.setAttribute("role", "button");
      el?.setAttribute("aria-label", markerLabel(data, spawn));
    }
    return () => {
      group.remove();
    };
  }, [world, onSelect, city]);
  useEffect(() => {
    if (!map.current || !position) return;
    const dot = L.circleMarker([position.lat, position.lon], {
      radius: 8,
      color: "white",
      weight: 3,
      fillColor: "#076bd9",
      fillOpacity: 1,
    }).addTo(map.current);
    return () => {
      dot.remove();
    };
  }, [position, city]);
  return (
    <section className="map-frame" aria-label="Street map">
      <div ref={container} className="map" />
      <button
        title="Center on player location"
        aria-label="Center on player location"
        className="recenter"
        disabled={!position}
        onClick={() =>
          position && map.current?.setView([position.lat, position.lon], 16)
        }
      >
        <LocateFixed size={22} />
      </button>
      {tileError && (
        <p className="tile-warning" role="status">
          Street tiles unavailable. Retry your connection; the encounter list
          remains available.
        </p>
      )}
    </section>
  );
}

function Creature({ name }: { name: string }) {
  return (
    <div
      className="creature-fallback"
      aria-label={`Artwork unavailable for ${name}`}
    >
      <span className="fallback-symbol">?</span>
      <strong>{name}</strong>
      <small>Artwork unavailable</small>
    </div>
  );
}
function CameraScene({
  name,
  onTap,
  onExit,
}: {
  name: string;
  onTap: () => void;
  onExit: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null),
    stream = useRef<MediaStream | null>(null),
    generation = useRef(0);
  const [status, setStatus] = useState(
    "Camera off. The non-camera encounter is available.",
  );
  const stop = useCallback(() => {
    generation.current++;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
  }, []);
  useEffect(() => {
    const visibility = () => {
      if (document.hidden) {
        stop();
        setStatus("Camera paused while the page is hidden.");
      }
    };
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("pagehide", stop);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("pagehide", stop);
    };
  }, [stop]);
  async function start() {
    stop();
    const token = generation.current;
    try {
      if (!isSecureContext || !navigator.mediaDevices?.getUserMedia)
        throw Error("Camera requires a supported HTTPS browser.");
      setStatus("Requesting camera permission...");
      const camera = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      if (token !== generation.current || document.hidden) {
        camera.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = camera;
      if (video.current) {
        video.current.srcObject = camera;
        await video.current.play();
      }
      if (token !== generation.current || document.hidden) {
        stop();
        return;
      }
      setStatus("Camera active. No video is recorded or uploaded.");
    } catch {
      stop();
      setStatus(
        "Camera unavailable or denied. Use the non-camera encounter below.",
      );
    }
  }
  return (
    <>
      <div className="camera-scene">
        <video
          ref={video}
          muted
          playsInline
          autoPlay
          aria-label="Live camera preview"
        />
        <button
          className="creature-tap"
          aria-label={`Inspect ${name}`}
          onClick={() => {
            stop();
            onTap();
          }}
        >
          <Creature name={name} />
        </button>
      </div>
      <p role="status">{status}</p>
      <div className="actions">
        <button onClick={start}>
          <Camera size={18} /> Enable camera
        </button>
        <button
          className="secondary"
          onClick={() => {
            stop();
            setStatus("Non-camera encounter.");
          }}
        >
          <CameraOff size={18} /> Use without camera
        </button>
        <button
          className="secondary"
          onClick={() => {
            stop();
            onExit();
          }}
        >
          Leave encounter
        </button>
      </div>
      <p>Tap {name} to read its Modédex entry.</p>
    </>
  );
}

export default function App() {
  const [ready, setReady] = useState(() => read(safetyKey) === "1");
  const [agreed, setAgreed] = useState(false),
    [showSafety, setShowSafety] = useState(false);
  const [publicApproach, setPublicApproach] = useState(false);
  const [mode, setMode] = useState(() =>
    read(modeKey) === "demo" ? "demo" : "real",
  );
  const [city, setCity] = useState("Raleigh"),
    [demoFix, setDemoFix] = useState<Fix | null>(null);
  const [fix, setFix] = useState<Fix | null>(null),
    [requestGPS, setRequestGPS] = useState(false);
  const [locationStatus, setLocationStatus] = useState(
    "GPS not requested. Browse the map or opt into Demo Mode.",
  );
  const [day, setDay] = useState(dayKey()),
    [tab, setTab] = useState("map");
  const [demoDay, setDemoDay] = useState("");
  const [progress, setProgress] = useState<Progress>(emptyProgress),
    [storageError, setStorageError] = useState("");
  const [selected, setSelected] = useState<Spawn | null>(null),
    [phase, setPhase] = useState<"nearby" | "scene" | "info" | "quiz">(
      "nearby",
    );
  const [feedback, setFeedback] = useState<number | null>(null),
    [dexId, setDexId] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    const refresh = (probe = false) => {
      if (!current) return;
      try {
        const p = readProgress(localStorage, mode);
        if (p.discovered.some((id) => !data.modedex.modemon[id]))
          throw Error(
            "Saved discovery references an unknown species. It was not overwritten.",
          );
        if (probe) persist(localStorage, mode, p);
        setProgress(p);
        setStorageError("");
      } catch (e) {
        setProgress(emptyProgress());
        setStorageError(
          `${(e as Error).message} Capture is disabled until persistent browser storage is available.`,
        );
      }
    };
    const changed = (event: StorageEvent) => {
      if (event.key?.endsWith(`progress:${mode}`)) refresh();
    };
    queueMicrotask(() => refresh(true));
    window.addEventListener("storage", changed);
    return () => {
      current = false;
      window.removeEventListener("storage", changed);
    };
  }, [mode]);
  const [clock, setClock] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => {
      const next = dayKey();
      setClock(Date.now());
      setDay(next);
      if (
        selected &&
        selected.date !== (mode === "demo" && demoDay ? demoDay : next)
      ) {
        setSelected(null);
        setPhase("nearby");
        setFeedback(null);
      }
    }, 1000);
    return () => clearInterval(t);
  }, [selected, mode, demoDay]);
  useEffect(() => {
    if (!ready || !requestGPS || mode === "demo") return;
    let watch: number | undefined;
    const stop = () => {
      if (watch !== undefined) navigator.geolocation?.clearWatch(watch);
      watch = undefined;
      setFix(null);
    };
    const start = () => {
      if (document.hidden) return;
      if (!navigator.geolocation) {
        setLocationStatus("This browser does not support geolocation.");
        return;
      }
      setLocationStatus("Waiting for foreground GPS...");
      watch = navigator.geolocation.watchPosition(
        (p) => {
          setFix({
            lat: p.coords.latitude,
            lon: p.coords.longitude,
            accuracy: p.coords.accuracy,
            timestamp: p.timestamp,
          });
          setLocationStatus(
            `Real GPS · accuracy ${approximateDistance(p.coords.accuracy)}`,
          );
        },
        (e) => {
          setFix(null);
          setLocationStatus(
            e.code === 1
              ? "Location permission denied. Enable it in Safari website settings, or opt into Demo Mode."
              : "Location unavailable. Check your signal and retry.",
          );
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
      );
    };
    const visibility = () => {
      stop();
      if (!document.hidden) start();
    };
    start();
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("pagehide", stop);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("pagehide", stop);
    };
  }, [ready, requestGPS, mode]);
  const worldDay = mode === "demo" && demoDay ? demoDay : day;
  const world = useMemo(
    () => buildWorld(data, worldDay, mode === "demo" ? "demo" : "real"),
    [worldDay, mode],
  );
  const active = useMemo(
    () =>
      world.filter(
        (s) =>
          !["captured", "escaped"].includes(progress.attempts[s.id]?.status),
      ),
    [world, progress],
  );
  const position =
    mode === "demo" ? (demoFix ? { ...demoFix, timestamp: clock } : null) : fix;
  const local = position ? habitatAt(data, position.lon, position.lat) : null;
  const available = active
    .filter((s) => s.poi.region.startsWith(city === "Raleigh" ? "RAL" : "DUR"))
    .sort((a, b) =>
      position
        ? distance(position, a.poi) - distance(position, b.poi)
        : a.id.localeCompare(b.id),
    );
  const open = useCallback((s: Spawn) => {
    setPublicApproach(false);
    setSelected(s);
    setPhase("nearby");
    setFeedback(null);
    setTab("map");
  }, []);
  const save = (p: Progress) => {
    try {
      persist(localStorage, mode, p);
      setProgress(p);
      setStorageError("");
      return true;
    } catch {
      setStorageError(
        "Progress could not be saved. Capture is paused; free storage or leave private browsing before continuing.",
      );
      return false;
    }
  };
  function switchMode(next: string) {
    setMode(next);
    setSelected(null);
    setPhase("nearby");
    setDemoFix(null);
    setTab("map");
    try {
      localStorage.setItem(modeKey, next);
    } catch {
      /* Progress persistence is checked separately. */
    }
  }
  function enterEncounter() {
    if (
      selected &&
      (mode === "demo" || selected.rarity !== "signature" || publicApproach) &&
      interaction(selected, position, clock).allowed &&
      !storageError &&
      save(startAttempt(progress, selected, data))
    )
      setPhase("scene");
  }
  const attempt = selected ? progress.attempts[selected.id] : null;
  const captureMode = attemptRules(attempt);
  const quiz = useMemo(
    () =>
      selected && attempt ? questionsForAttempt(selected, data, attempt) : [],
    [selected, attempt],
  );
  const gate = selected ? interaction(selected, position, clock) : null;
  const counts = Object.values(progress.attempts).filter(
    (a) => a.status === "captured",
  ).length;
  const close = () => {
    setSelected(null);
    setPhase("nearby");
    setFeedback(null);
  };

  if (!ready || showSafety)
    return (
      <>
        <header>
          <h1>Modémon GO</h1>
          <span>Explore. Learn. Collect.</span>
        </header>
        <main className="onboarding">
          <h2>{safetyNotice.title}</h2>
          {safetyNotice.sections.map((s) => (
            <section key={s.title}>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </section>
          ))}
          <p>
            Foreground GPS is optional until a real-world encounter. Camera is
            optional. Progress stays in this browser; clearing site data deletes
            it. No account or location history is stored. Street tiles are
            requested from OpenStreetMap, which can see tile requests.
          </p>
          {!ready ? (
            <>
              <label>
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                />{" "}
                {safetyNotice.acknowledgment}
              </label>
              <button
                disabled={!agreed}
                onClick={() => {
                  try {
                    localStorage.setItem(safetyKey, "1");
                  } catch {
                    /* session acknowledgment only */
                  }
                  setReady(true);
                }}
              >
                Start Playing
              </button>
            </>
          ) : (
            <button onClick={() => setShowSafety(false)}>Back to game</button>
          )}
        </main>
      </>
    );

  return (
    <>
      <header>
        <h1>Modémon GO</h1>
        <span>{counts} captured</span>
      </header>
      {mode === "demo" && (
        <aside className="demo-banner" role="status">
          <strong>DEMO LOCATION — not your GPS</strong>
          <span>Simulated movement · separate demo collection</span>
          <button className="small" onClick={() => switchMode("real")}>
            Exit Demo Mode
          </button>
        </aside>
      )}
      <button className="safety-strip" onClick={() => setShowSafety(true)}>
        {safetyNotice.reminder}
      </button>
      {storageError && <ErrorText>{storageError}</ErrorText>}
      <nav aria-label="Game navigation">
        {[
          ["map", "Map", Compass],
          ["dex", "Modédex", BookOpen],
          ["settings", "Settings", Settings],
        ].map(([key, label, Icon]) => {
          const C = Icon as typeof Compass;
          return (
            <button
              key={key as string}
              className={tab === key ? "active" : "secondary"}
              aria-current={tab === key ? "page" : undefined}
              onClick={() => {
                close();
                setTab(key as string);
              }}
            >
              <C size={18} />
              {label as string}
            </button>
          );
        })}
      </nav>
      {tab === "map" && (
        <>
          <div className="map-controls">
            <select
              aria-label="Browse city"
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                setDemoFix(null);
                close();
              }}
            >
              <option>Raleigh</option>
              <option>Durham</option>
            </select>
            {mode === "real" ? (
              <>
                <button
                  className="small"
                  onClick={() => {
                    setRequestGPS(false);
                    setTimeout(() => setRequestGPS(true), 0);
                  }}
                >
                  <MapPin size={17} /> Allow foreground location
                </button>
                <button
                  className="secondary small"
                  onClick={() => switchMode("demo")}
                >
                  Try Demo Mode
                </button>
              </>
            ) : (
              <label>
                Demo rotation (simulated date)
                <select
                  aria-label="Demo rotation (simulated date)"
                  value={demoDay}
                  onChange={(event) => {
                    setDemoDay(event.target.value);
                    setDemoFix(null);
                    close();
                  }}
                >
                  <option value="">Today</option>
                  {Array.from({ length: 16 }, (_, i) =>
                    new Date(Date.parse(day + "T12:00:00Z") + i * 86400000)
                      .toISOString().slice(0, 10),
                  ).map((date) => (
                    <option key={date} value={date}>{date} (preview)</option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <Map world={active} position={position} onSelect={open} city={city} />
          <main className="nearby">
            {mode === "demo" && (
              <p>
                Simulated day: {worldDay}. Preview another day to explore the
                rotation; saved attempts are never reset. Real encounters always
                use today.
              </p>
            )}
            <p role="status">
              {mode === "demo" ? "Demo preset: " + city : locationStatus}
            </p>
            <p className="muted">
              {local?.region
                ? `${regionLabel(data, local.region)} · ${local.zones.map((z) => z.properties.habitat_primary).join(", ") || "No habitat identified here yet"}`
                : position
                  ? "You're outside the game areas. Browse freely; real encounters still need a nearby phone location."
                  : mode === "demo"
                    ? "Choose an encounter to set a simulated location."
                    : "Allow location access when you're ready to find a nearby encounter."}
            </p>
            <h2>Nearby encounters</h2>
            <p>
              Question marks hide the Modémon until you enter. Common markers
              are green; Rare markers are blue. New encounters arrive each day (
              {day}, Eastern time).
            </p>
            <div className="encounter-list">
              {available.map((s) => (
                <button
                  className="encounter-row secondary"
                  data-poi-id={s.poi.id}
                  key={s.id}
                  onClick={() => open(s)}
                >
                  <span className={`rarity-dot ${s.rarity}`} />
                  <span>
                    Mystery Modémon · {rarityLabel(s.rarity)}
                    <small>{placeLabel(data, s.poi)}</small>
                  </span>
                  <span>
                    {position
                      ? `${approximateDistance(distance(position, s.poi))}${mode === "demo" ? " simulated" : ""}`
                      : mode === "demo"
                        ? "Try here"
                        : "Location needed"}
                  </span>
                </button>
              ))}
            </div>
            {available.length === 0 && (
              <p>
                No safe eligible encounters are available here in this rotation.
                Try the other city; never enter a sensitive facility for
                gameplay.
              </p>
            )}
          </main>
        </>
      )}
      {tab === "dex" && (
        <main>
          <h2>{mode === "demo" ? "Demo " : ""}Modédex</h2>
          <p>
            {progress.discovered.length} discovered of 51 · {counts} captures
          </p>
          {dexId ? (
            <>
              <button className="secondary" onClick={() => setDexId(null)}>
                Back to discoveries
              </button>
              <DexEntry
                species={data.modedex.modemon[dexId]}
                habitatTitle={title}
              />
            </>
          ) : (
            <>
              <p>
                Undiscovered entries remain hidden. Signature encounters appear
                occasionally at approved project-associated destinations, not every day.
              </p>
              {progress.discovered.map((id) => (
                <button
                  className="dex-row secondary"
                  key={id}
                  onClick={() => setDexId(id)}
                >
                  {data.modedex.modemon[id]?.name ?? id}
                  <small>
                    {
                      Object.values(progress.attempts).filter(
                        (a) => a.speciesId === id && a.status === "captured",
                      ).length
                    }{" "}
                    captured
                  </small>
                </button>
              ))}
              {!progress.discovered.length && (
                <p>
                  No discoveries yet. Enter an encounter to discover a Modémon.
                </p>
              )}
            </>
          )}
        </main>
      )}
      {tab === "settings" && (
        <main>
          <h2>Settings & privacy</h2>
          <p>
            Camera frames and GPS coordinates are not recorded or uploaded by
            this game. Only safety acknowledgment, mode, discoveries, quiz
            answers, captures, and escapes are saved locally. Map tiles are
            served by OpenStreetMap. No analytics or player account.
          </p>
          <button onClick={() => switchMode(mode === "demo" ? "real" : "demo")}>
            {mode === "demo" ? "Exit Demo Mode" : "Opt into Demo Mode"}
          </button>
          <button className="secondary" onClick={() => setShowSafety(true)}>
            Read player-safety notice
          </button>
          <p>
            Prototype limitations: artwork is unavailable pending approval.
            Durham Station Signatures are Demo-only while a safe approach is unverified during construction.
            Browser progress is not
            synchronized across devices. Real-world access and opening hours are
            not guaranteed; skip unsafe or inaccessible places.
          </p>
          <p>
            World rules: {bundle.data_version} / playable-v1. Real and demo
            progress are separate.
          </p>
          <p>
            Habitat labels and special destinations are educational context, not
            claims about specific AI deployments.
          </p>
          <p>
            Map data © OpenStreetMap contributors (ODbL).{" "}
            <a href="https://www.openstreetmap.org/copyright">
              Attribution and license
            </a>
            .
          </p>
        </main>
      )}
      {selected && (
        <div className="modal-backdrop">
          <section
            className="encounter-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="encounter-title"
          >
            <button
              aria-label="Close encounter"
              title="Close encounter"
              className="close secondary"
              onClick={close}
            >
              <X size={22} />
            </button>
            <h2 id="encounter-title">
              {phase === "nearby"
                ? "Mystery Modémon · " + rarityLabel(selected.rarity)
                : data.modedex.modemon[selected.speciesId].name}
            </h2>
            <p>{placeLabel(data, selected.poi)}</p>
            {mode === "demo" && (
              <p className="demo-inline">DEMO LOCATION — not your GPS</p>
            )}
            {phase === "nearby" && (
              <>
                <p>{publicLocationSafety}</p>
                {extraLocationSafety(selected.poi) && (
                  <p>{extraLocationSafety(selected.poi)}</p>
                )}
                {selected.rarity === "signature" && mode === "real" && (
                  <label className="safety-check">
                    <input
                      type="checkbox"
                      checked={publicApproach}
                      onChange={(event) => setPublicApproach(event.target.checked)}
                    />
                    I am stopped safely on an open public pedestrian approach.
                    No closed, restricted or operating area is needed.
                  </label>
                )}
                {gate && (
                  <p role="status">{proximityCopy(mode, position, gate)}</p>
                )}
                {mode === "real" &&
                  position &&
                  Number.isFinite(position.accuracy) &&
                  position.accuracy >= 20 && (
                    <p className="muted">
                      Your phone&apos;s location estimate may be off by about{" "}
                      {approximateDistance(position.accuracy)}. Wait for a
                      clearer signal if the distance seems wrong.
                    </p>
                  )}
                {mode === "demo" && (
                  <button
                    className="secondary"
                    onClick={() =>
                      setDemoFix({
                        lat: selected.poi.lat,
                        lon: selected.poi.lon,
                        accuracy: 0,
                        timestamp: Date.now(),
                      })
                    }
                  >
                    Simulate walking here (Demo)
                  </button>
                )}
                <button
                  disabled={
                    !gate?.allowed || !!storageError ||
                    (mode === "real" && selected.rarity === "signature" && !publicApproach)
                  }
                  onClick={enterEncounter}
                >
                  Enter encounter
                </button>
                <p className="muted">
                  Stop somewhere safe before using your screen. Keep paths and
                  entrances clear, and skip this encounter if you can&apos;t
                  reach it safely.
                </p>
              </>
            )}
            {phase === "scene" && (
              <CameraScene
                name={data.modedex.modemon[selected.speciesId].name}
                onTap={() => setPhase("info")}
                onExit={close}
              />
            )}
            {phase === "info" && (
              <>
                <DexEntry
                  species={data.modedex.modemon[selected.speciesId]}
                  habitatTitle={title}
                />
                <fieldset
                  className="difficulty-picker"
                  disabled={
                    !!storageError ||
                    !!attempt?.answers.length ||
                    captureMode.legacy
                  }
                >
                  <legend>Capture difficulty</legend>
                  {Object.entries(quizModes).map(([key, choice]) => (
                    <label key={key}>
                      <input
                        type="radio"
                        name="capture-difficulty"
                        value={key}
                        checked={captureMode.difficulty === key}
                        onChange={() =>
                          save(
                            changeDifficulty(
                              progress,
                              selected,
                              data,
                              key as Difficulty,
                            ),
                          )
                        }
                      />
                      <span>
                        <strong>{choice.label}</strong>
                        <small>{choice.count} questions</small>
                      </span>
                    </label>
                  ))}
                </fieldset>
                {(!!attempt?.answers.length || captureMode.legacy) && (
                  <p>
                    {captureMode.label} is locked for this encounter. Your saved
                    answers will resume.
                  </p>
                )}
                <button
                  disabled={!!storageError}
                  onClick={() => {
                    setPhase("quiz");
                    setFeedback(
                      attempt?.answers.length
                        ? attempt.answers.length - 1
                        : null,
                    );
                  }}
                >
                  Capture · {captureMode.count} questions
                </button>
              </>
            )}
            {phase === "quiz" && (
              <>
                <p className="quiz-score" role="status">
                  {captureMode.label} ·{" "}
                  {attempt?.answers.filter(
                    (answer, i) => answer === quiz[i].correct,
                  ).length ?? 0}{" "}
                  correct from {attempt?.answers.length ?? 0} answered · Need{" "}
                  {captureMode.required} of {captureMode.count}
                </p>
                {feedback !== null && attempt && (
                  <QuizFeedback
                    correct={
                      attempt.answers[feedback] === quiz[feedback].correct
                    }
                    answer={quiz[feedback].options[quiz[feedback].correct]}
                    explanation={quiz[feedback].explanation}
                    buttonLabel={
                      attempt.status === "in_progress"
                        ? "Next question"
                        : "Show result"
                    }
                    onContinue={() => setFeedback(null)}
                  />
                )}
                {feedback === null && attempt?.status === "in_progress" && (
                  <section>
                    <p>
                      Question {attempt.answers.length + 1} of{" "}
                      {captureMode.count} · at least {captureMode.required}{" "}
                      correct to capture
                    </p>
                    <h3>{quiz[attempt.answers.length].prompt}</h3>
                    {quiz[attempt.answers.length].options.map((option, i) => (
                      <button
                        className="answer secondary"
                        key={option}
                        disabled={!!storageError}
                        onClick={() => {
                          const index = attempt.answers.length;
                          const next = answerQuestion(
                            progress,
                            selected,
                            i,
                            quiz,
                          );
                          if (save(next)) setFeedback(index);
                        }}
                      >
                        {option}
                      </button>
                    ))}
                  </section>
                )}
                {feedback === null && attempt?.status === "captured" && (
                  <>
                    <h3>Captured!</h3>
                    <p>
                      {data.modedex.modemon[selected.speciesId].name} is saved
                      in your {mode === "demo" ? "separate demo " : ""}
                      collection in this browser.
                    </p>
                    <button onClick={close}>Return to map</button>
                  </>
                )}
                {feedback === null && attempt?.status === "escaped" && (
                  <>
                    <h3>It escaped.</h3>
                    <p>
                      This encounter is unavailable for today’s rotation. Other
                      encounters of the same species are unaffected. Your
                      answers are saved.
                    </p>
                    <button onClick={close}>Return to map</button>
                  </>
                )}
              </>
            )}
          </section>
        </div>
      )}
      <footer>
        Modémon GO · Educational prototype · No encounter is worth an unsafe
        approach.
      </footer>
    </>
  );
}

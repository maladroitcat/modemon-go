import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { AppState as NativeAppState } from 'react-native';
import { foregroundPermission, startForegroundWatch, UNKNOWN_PERMISSION, type Permission, type Position } from '../lib/location';
import { acknowledgeSafety, canEnterGameplay, loadAcknowledgment, stageAfterLocation, type OnboardingStage } from '../lib/onboarding';

type State = {
  stage: OnboardingStage;
  ready: boolean;
  busy: boolean;
  storageAvailable: boolean;
  permission: Permission;
  position: Position | null;
  locating: boolean;
  locationUnavailable: boolean;
  begin: () => Promise<void>;
  requestLocation: () => Promise<void>;
  continueWithoutLocation: () => void;
  acceptSafety: (checked: boolean) => Promise<void>;
  retryLocation: () => void;
};

const Context = createContext<State | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [stage, setStage] = useState<OnboardingStage>('loading');
  const [acknowledged, setAcknowledged] = useState(false);
  const [storageAvailable, setStorageAvailable] = useState(true);
  const [busy, setBusy] = useState(false);
  const [permission, setPermission] = useState<Permission>(UNKNOWN_PERMISSION);
  const [position, setPosition] = useState<Position | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationUnavailable, setLocationUnavailable] = useState(false);
  const [active, setActive] = useState(NativeAppState.currentState === 'active');
  const [refresh, setRefresh] = useState(0);
  const ready = canEnterGameplay(stage, acknowledged);

  useEffect(() => {
    let mounted = true;
    void loadAcknowledgment(AsyncStorage).then((result) => {
      if (!mounted) return;
      setAcknowledged(result.acknowledged);
      setStorageAvailable(result.persisted);
      setStage('welcome');
    });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    const listener = NativeAppState.addEventListener('change', (value) => {
      setActive(value === 'active');
      if (value === 'active') setRefresh((n) => n + 1);
      else setPosition(null);
    });
    return () => listener.remove();
  }, []);

  useEffect(() => {
    if (!ready || !active) return;
    let cancelled = false;
    let stop: (() => void) | undefined;
    void foregroundPermission(Location).then((current) => {
      if (cancelled) return;
      setPosition(null);
      setLocating(true);
      setLocationUnavailable(false);
      setPermission(current);
      if (current.status !== 'granted') {
        setLocating(false);
        return;
      }
      stop = startForegroundWatch({
        hasServicesEnabledAsync: Location.hasServicesEnabledAsync,
        watch: (onFix, onError) => Location.watchPositionAsync({
          accuracy: Location.Accuracy.Balanced, distanceInterval: 10, timeInterval: 5_000,
        }, (fix) => onFix({ latitude: fix.coords.latitude, longitude: fix.coords.longitude, accuracy: fix.coords.accuracy }), onError),
      }, (fix) => {
        setPosition(fix);
        setLocating(false);
        setLocationUnavailable(false);
      }, () => {
        setPosition(null);
        setLocating(false);
        setLocationUnavailable(true);
      });
    });
    return () => { cancelled = true; stop?.(); };
  }, [ready, active, refresh]);

  const begin = useCallback(async () => {
    setStage('location');
    setBusy(true);
    const current = await foregroundPermission(Location);
    setPermission(current);
    setBusy(false);
    if (current.status === 'granted') setStage(stageAfterLocation(acknowledged));
  }, [acknowledged]);

  const requestLocation = useCallback(async () => {
    setBusy(true);
    const current = await foregroundPermission(Location, true);
    setPermission(current);
    setBusy(false);
    if (current.status === 'granted') {
      setStage(stageAfterLocation(acknowledged));
      setRefresh((n) => n + 1);
    }
  }, [acknowledged]);

  const acceptSafety = useCallback(async (checked: boolean) => {
    setBusy(true);
    try {
      const result = await acknowledgeSafety(AsyncStorage, checked);
      setAcknowledged(result.acknowledged);
      setStorageAvailable(result.persisted);
      setStage('ready');
    } finally {
      setBusy(false);
    }
  }, []);

  return <Context.Provider value={{ stage, ready, busy, storageAvailable, permission, position, locating,
    locationUnavailable, begin, requestLocation,
    continueWithoutLocation: () => setStage(stageAfterLocation(acknowledged)),
    acceptSafety, retryLocation: () => setRefresh((n) => n + 1) }}>{children}</Context.Provider>;
}

export function useAppState() {
  const value = useContext(Context);
  if (!value) throw new Error('AppProvider is required');
  return value;
}

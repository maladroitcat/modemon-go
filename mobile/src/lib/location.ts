export type Permission = {
  status: 'undetermined' | 'granted' | 'denied' | 'unavailable';
  canAskAgain: boolean;
};

export type PermissionApi = {
  getForegroundPermissionsAsync: () => Promise<Permission>;
  requestForegroundPermissionsAsync: () => Promise<Permission>;
};

export const UNKNOWN_PERMISSION: Permission = { status: 'undetermined', canAskAgain: true };

export async function foregroundPermission(api: PermissionApi, request = false): Promise<Permission> {
  try {
    const current = await api.getForegroundPermissionsAsync();
    if (!request || current.status === 'granted' || !current.canAskAgain) return current;
    return await api.requestForegroundPermissionsAsync();
  } catch {
    return { status: 'unavailable', canAskAgain: true };
  }
}

export type Position = { latitude: number; longitude: number; accuracy: number | null };
type Subscription = { remove: () => void };
export type PositionApi = {
  hasServicesEnabledAsync: () => Promise<boolean>;
  watch: (onFix: (fix: Position) => void, onError: () => void) => Promise<Subscription>;
};

export function validPosition(fix: Position) {
  return Number.isFinite(fix.latitude) && Number.isFinite(fix.longitude)
    && Math.abs(fix.latitude) <= 90 && Math.abs(fix.longitude) <= 180;
}

// Only one current fix is delivered. The owner stops this watcher when backgrounded.
export function startForegroundWatch(
  api: PositionApi,
  onFix: (fix: Position) => void,
  onUnavailable: () => void,
  timeoutMs = 15_000,
): () => void {
  let stopped = false;
  let subscription: Subscription | undefined;
  const deadline = setTimeout(() => { if (!stopped) onUnavailable(); }, timeoutMs);
  const unavailable = () => {
    clearTimeout(deadline);
    if (!stopped) onUnavailable();
  };
  void (async () => {
    if (!await api.hasServicesEnabledAsync()) {
      unavailable();
      return;
    }
    if (stopped) return;
    subscription = await api.watch((fix) => {
      if (stopped) return;
      if (!validPosition(fix)) {
        unavailable();
        return;
      }
      clearTimeout(deadline);
      onFix(fix);
    }, unavailable);
    if (stopped) subscription.remove();
  })().catch(unavailable);
  return () => {
    stopped = true;
    clearTimeout(deadline);
    subscription?.remove();
  };
}

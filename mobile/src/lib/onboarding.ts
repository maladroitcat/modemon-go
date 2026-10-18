export const SAFETY_VERSION = 1;
export const SAFETY_STORAGE_KEY = 'modemon-go:safety-acknowledgment';

export type OnboardingStage = 'loading' | 'welcome' | 'location' | 'safety' | 'ready';
export type SafetyStorage = {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
};

export function hasCurrentAcknowledgment(value: string | null): boolean {
  if (!value) return false;
  try {
    const record: unknown = JSON.parse(value);
    return typeof record === 'object' && record !== null && !Array.isArray(record)
      && 'version' in record && record.version === SAFETY_VERSION;
  } catch {
    return false;
  }
}

export async function loadAcknowledgment(storage: SafetyStorage) {
  try {
    return { acknowledged: hasCurrentAcknowledgment(await storage.getItem(SAFETY_STORAGE_KEY)), persisted: true };
  } catch {
    return { acknowledged: false, persisted: false };
  }
}

export async function acknowledgeSafety(storage: SafetyStorage, checked: boolean) {
  if (!checked) throw new Error('Explicit safety acknowledgment is required.');
  try {
    await storage.setItem(SAFETY_STORAGE_KEY, JSON.stringify({ version: SAFETY_VERSION }));
    return { acknowledged: true, persisted: true };
  } catch {
    // Explicit agreement still applies this session; the notice returns next launch.
    return { acknowledged: true, persisted: false };
  }
}

export function stageAfterLocation(acknowledged: boolean): OnboardingStage {
  return acknowledged ? 'ready' : 'safety';
}

export function canEnterGameplay(stage: OnboardingStage, acknowledged: boolean) {
  return stage === 'ready' && acknowledged;
}

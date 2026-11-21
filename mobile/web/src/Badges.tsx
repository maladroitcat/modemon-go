import { Award, Check, Lock, Trophy, X } from "lucide-react";
import type { Difficulty } from "./quizzes";
import type { Achievement } from "./achievements";

const levels = [
  ["novice", "Beginner", "Novice"],
  ["intermediate", "Intermediate", "Intermediate"],
  ["expert", "Expert", "Expert"],
] as const;

export function MasteryBadges({ earned, compact = false }: {
  earned?: ReadonlySet<Difficulty>; compact?: boolean;
}) {
  return <span className={`mastery-badges${compact ? " compact" : ""}`} role="group" aria-label="Quiz mastery badges">
    {levels.map(([level, label, quiz]) => {
      const unlocked = earned?.has(level) ?? false;
      const explanation = `${label} Badge: ${unlocked ? "earned" : "locked"}. Successfully capture this species by passing ${level === "novice" ? "a" : "an"} ${quiz} quiz.`;
      return <span key={level} className={`mastery-badge ${level} ${unlocked ? "earned" : "locked"}`}
        role="img" aria-label={explanation} title={explanation}>
        {unlocked ? <Award size={20} aria-hidden="true" /> : <Lock size={18} aria-hidden="true" />}
        <span>{label}<span className="badge-state">{unlocked ? "Earned" : "Locked"}</span></span>
      </span>;
    })}
  </span>;
}

function AchievementCard({ achievement: a }: { achievement: Achievement }) {
  return <article className={`achievement-card ${a.unlocked ? "earned" : "locked"}`} aria-label={a.name}>
    <div className="achievement-heading">
      <span className="achievement-icon"><Trophy size={24} aria-hidden="true" /></span>
      <h3>{a.name}</h3>
    </div>
    <span className="achievement-state">{a.unlocked ? <Check size={16} aria-hidden="true" /> : <Lock size={16} aria-hidden="true" />}
      {a.unlocked ? "Earned · Complete" : a.current ? "In progress · Locked" : "Locked"}</span>
    <p>{a.description}</p>
    <p className="achievement-count">{a.current} of {a.total} {a.unit}</p>
    <progress max={a.total || 1} value={a.current} aria-label={`${a.name}: ${a.current} of ${a.total} ${a.unit}`} />
    {a.unavailable > 0 && <p className="coverage-note">World coverage: {a.unavailable} required {a.unavailable === 1 ? "species has" : "species have"} no eligible public encounter locations yet. This goal currently cannot be completed through play.</p>}
  </article>;
}

export function TrainerBadges({ achievements, demo }: { achievements: Achievement[]; demo: boolean }) {
  return <main className="trainer-badges">
    <p className="eyebrow">{demo ? "Separate Demo collection" : "Real-world collection"}</p>
    <h2>Trainer Badges</h2>
    <p>Explore, collect and learn. Only successful captures count. Earn mastery at each difficulty through distinct eligible encounters; completed encounters stay completed.</p>
    <h3>Collection milestones</h3>
    <div className="achievement-gallery">{achievements.filter((a) => a.group === "collection").map((a) => <AchievementCard key={a.id} achievement={a} />)}</div>
    <h3>Family experts</h3>
    <p>Collect every species in a family to earn its badge.</p>
    <div className="achievement-gallery">{achievements.filter((a) => a.group === "family").map((a) => <AchievementCard key={a.id} achievement={a} />)}</div>
  </main>;
}

export function AchievementNotice({ achievements, onDismiss }: { achievements: Achievement[]; onDismiss: () => void }) {
  return <aside className="achievement-notice" aria-label="New trainer achievements">
    <div role="status" aria-live="polite" aria-atomic="true">
      <strong><Trophy size={20} aria-hidden="true" /> Achievement Unlocked!</strong>
      <p>{achievements.map((a) => a.name).join(" · ")}</p>
      <small>View your progress in Badges.</small>
    </div>
    <button className="secondary" aria-label="Dismiss achievement notification" onClick={onDismiss}><X size={18} aria-hidden="true" /></button>
  </aside>;
}

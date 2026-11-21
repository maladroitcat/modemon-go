import { ExternalLink, Sparkles, Workflow, ShieldAlert, ScanEye, Leaf, BookOpen } from "lucide-react";
import type { ReactNode } from "react";
import { MasteryBadges } from "./Badges";
import type { Difficulty } from "./quizzes";
import { rarityLabel } from "./presentation";
import { everydayExamples } from "./data/everydayExamples";
import type { Species } from "./engine";
import { signatureProject } from "./signatures";
import { Creature } from "./Art";
import LearningLinks from "./LearningLinks";

function CardPanel({ title, icon, children, className = "" }: {
  title: string; icon: ReactNode; children: ReactNode; className?: string;
}) {
  return <section className={`card-panel ${className}`}>
    <h3>{icon}{title}</h3>{children}
  </section>;
}

export default function DexEntry({
  species: s,
  habitatTitle,
  modemonId,
  familyName,
  showExamples = false,
  mastery,
}: {
  species: Species;
  habitatTitle: (id: string) => string;
  modemonId?: string;
  familyName?: string;
  showExamples?: boolean;
  mastery?: ReadonlySet<Difficulty>;
}) {
  const project = signatureProject(s);
  return (
    <article className={`dex-entry trading-card rarity-${s.rarity}`}>
      <div className="card-header">
      <p className="card-meta"><span className={`rarity-tag ${s.rarity}`}>{rarityLabel(s.rarity)}</span><span>{familyName ?? s.family_id}</span></p>
      <h2>{s.name}</h2>
      {modemonId && <Creature modemonId={modemonId} name={s.name} className="dex-art" />}
      {mastery && <>
        <MasteryBadges earned={mastery} />
        <p className="muted">Earn each badge separately by capturing this species at that quiz difficulty. Beginner uses Novice; higher difficulties do not grant lower badges.</p>
      </>}
      {project?.introduction && (
        <p className="signature-inspiration">{project.introduction}</p>
      )}
      <p>{s.dex_entry}</p>
      </div>
      <CardPanel title="Ability / Job" icon={<Sparkles size={20} aria-hidden="true" />}>
        <p><strong>{s.role}</strong></p>
        <dl><dt>AI tasks</dt><dd>{s.ai_tasks.join(", ")}</dd>
          <dt>Habitats</dt><dd>{s.habitats.map(habitatTitle).join(", ")}</dd></dl>
      </CardPanel>
      <CardPanel title="How It Works" icon={<Workflow size={20} aria-hidden="true" />}>
        <dl>
          <dt>Input</dt><dd>{s.input_data}</dd>
          <dt>Output</dt><dd>{s.output_data}</dd>
          <dt>Representative techniques{project ? " (not deployment claims)" : ""}</dt>
          <dd>{s.models_algorithms.join(", ")}</dd>
        </dl>
      </CardPanel>
      <CardPanel title="Weaknesses / Limitations" className="card-limitations" icon={<ShieldAlert size={20} aria-hidden="true" />}>
        <ul>{s.biases_limitations.map((text) => <li key={text}>{text}</li>)}</ul>
      </CardPanel>
      <CardPanel title="Explainability" icon={<ScanEye size={20} aria-hidden="true" />}>
        <ul>{s.explainability.map((text) => <li key={text}>{text}</li>)}</ul>
      </CardPanel>
      {showExamples && modemonId && everydayExamples[modemonId] && (
        <CardPanel title="AI in the Wild" icon={<Leaf size={20} aria-hidden="true" />}>
          <p className="muted">Illustrative applications, not claims about systems deployed at these places. Documented Signature projects are cited separately below.</p>
          {everydayExamples[modemonId].map((example) => <div className="everyday-example" key={example.title}>
            <h4>{example.title}</h4><p>{example.description}</p>
            <small>{example.illustrative ? "Illustrative scenario" : "Documented example"}</small>
          </div>)}
        </CardPanel>
      )}
      <CardPanel title="Further Learning" icon={<BookOpen size={20} aria-hidden="true" />}>
      {project && (
        <section
          aria-label="Real project inspiration"
          className="signature-project"
        >
          {project.href && (
            <a
              href={project.href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Learn about the real project for ${s.name} (opens in a new tab)`}
            >
              Learn about the real project{" "}
              <ExternalLink aria-hidden="true" size={18} />
            </a>
          )}
          {project.review && <p role="alert">{project.review}</p>}
          {project.source && (
            <>
              <p className="muted">
                Source: {project.source.source_organization}.{" "}
                {project.source.source_title}.
              </p>
              <p>
                Documented technology:{" "}
                {project.source.documented_technology.length
                  ? project.source.documented_technology.join(", ")
                  : "No specific technology is recorded in this entry's provenance."}
              </p>
            </>
          )}
          <p>
            Real-world inspiration, not a claim that this system runs at your
            location. Encounters use approved place associations and public
            pedestrian approaches, subject to local signs, hours and closures.
          </p>
        </section>
      )}
      <LearningLinks modemonId={modemonId} species={s} />
      </CardPanel>
      <p className="muted">
        Educational context, not a claim that this place deploys a particular AI
        system.
      </p>
    </article>
  );
}

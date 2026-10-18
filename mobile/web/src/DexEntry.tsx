import { ExternalLink } from "lucide-react";
import type { Species } from "./engine";
import { signatureProject } from "./signatures";

export default function DexEntry({
  species: s,
  habitatTitle,
}: {
  species: Species;
  habitatTitle: (id: string) => string;
}) {
  const project = signatureProject(s);
  return (
    <article className="dex-entry">
      <h2>{s.name}</h2>
      <p className="eyebrow">
        {s.role} · {s.rarity}
      </p>
      {project?.introduction && (
        <p className="signature-inspiration">{project.introduction}</p>
      )}
      <p>{s.dex_entry}</p>
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
      <dl>
        <dt>Habitats</dt>
        <dd>{s.habitats.map(habitatTitle).join(", ")}</dd>
        <dt>AI tasks</dt>
        <dd>{s.ai_tasks.join(", ")}</dd>
        <dt>
          Representative techniques{project ? " (not deployment claims)" : ""}
        </dt>
        <dd>{s.models_algorithms.join(", ")}</dd>
        <dt>Input</dt>
        <dd>{s.input_data}</dd>
        <dt>Output</dt>
        <dd>{s.output_data}</dd>
        <dt>Limitations</dt>
        <dd>
          <ul>
            {s.biases_limitations.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        </dd>
        <dt>Explainability</dt>
        <dd>{s.explainability.join(", ")}</dd>
      </dl>
      <p className="muted">
        Educational context, not a claim that this place deploys a particular AI
        system.
      </p>
    </article>
  );
}

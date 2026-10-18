import { CircleCheck, CircleX } from "lucide-react";

export default function QuizFeedback({
  correct,
  answer,
  explanation,
  buttonLabel,
  onContinue,
}: {
  correct: boolean;
  answer: string;
  explanation: string;
  buttonLabel: string;
  onContinue: () => void;
}) {
  const Icon = correct ? CircleCheck : CircleX;
  return (
    <div
      className={`feedback feedback--${correct ? "correct" : "incorrect"}`}
      role="status"
      aria-live="polite"
    >
      <div className="feedback-heading">
        <Icon aria-hidden="true" size={24} />
        <strong>
          {correct ? "Correct." : "Not quite."} Correct answer: {answer}
        </strong>
      </div>
      <p>{explanation}</p>
      <button onClick={onContinue}>{buttonLabel}</button>
    </div>
  );
}

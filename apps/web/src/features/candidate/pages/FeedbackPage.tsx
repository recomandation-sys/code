import { FormEvent, useState } from "react";

import { Button } from "../../../components/Button.js";
import { Card } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { fieldClass } from "../../candidate-profile/components/OnboardingChrome.js";

export function FeedbackPage() {
  const [submitted, setSubmitted] = useState(false);
  const [rating, setRating] = useState(0);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <Card className="jl-fade-up mx-auto max-w-lg text-center">
        <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-accent-50 text-accent-600">
          <svg width="22" height="22" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3.5 8.5L6.5 11.5L12.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </div>
        <h1 className="mt-4 text-xl font-bold text-slate-900">Thank you</h1>
        <p className="mt-2 text-sm text-slate-500">
          Your feedback helps us improve matches for everyone. We never show a public “sentiment” label on your
          comment.
        </p>
        <Button className="mt-6" variant="secondary" onClick={() => setSubmitted(false)}>
          Send another
        </Button>
      </Card>
    );
  }

  return (
    <div className="jl-fade-up mx-auto max-w-lg">
      <PageHeader title="Feedback" description="Tell us how JOBLIK AI is working for you." />
      <Card>
        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Rating (optional)</p>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  aria-label={`${n} stars`}
                  onClick={() => setRating(n)}
                  className={`cursor-pointer text-2xl transition-transform hover:scale-110 ${
                    n <= rating ? "text-warn-500" : "text-slate-300"
                  }`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Your comment</span>
            <textarea
              required
              rows={5}
              className={fieldClass}
              placeholder="What worked? What should we improve?"
            />
          </label>
          <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-600">
            <input type="checkbox" className="mt-1 size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600" />
            Allow this to be featured as a testimonial (first name + role only)
          </label>
          <Button type="submit" className="w-full font-semibold shadow-sm shadow-brand-600/20">
            Submit feedback
          </Button>
        </form>
      </Card>
    </div>
  );
}

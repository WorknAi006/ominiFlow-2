import Link from "next/link";

interface FeaturePlaceholderProps {
  title: string;
  description: string;
  mark: string;
}

export function FeaturePlaceholder({ title, description, mark }: FeaturePlaceholderProps) {
  return (
    <section className="page-enter max-w-4xl">
      <p className="eyebrow">OMNIFLOW WORKSPACE</p>
      <h1 className="page-title mt-3">{title}</h1>
      <p className="page-subtitle mt-2">{description}</p>
      <div className="placeholder-card mt-9">
        <span className="placeholder-mark" aria-hidden="true">{mark}</span>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Coming into focus</h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">
            This destination is part of your workspace navigation. Its full workflow is not available yet.
          </p>
          <Link href="/dashboard" className="inline-flex mt-5 text-sm font-semibold text-[#176b59] hover:underline">
            Back to dashboard <span aria-hidden="true" className="ml-1">→</span>
          </Link>
        </div>
      </div>
    </section>
  );
}

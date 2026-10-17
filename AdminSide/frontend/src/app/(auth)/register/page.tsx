import Link from "next/link";
import Image from "next/image";
import { AuthForm } from "@/components/auth-form";

export default function RegisterPage() {
  return (
    <main className="min-h-screen bg-[#F8F9FD] flex flex-col items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-lg bg-white rounded-3xl p-8 sm:p-10 shadow-xl shadow-slate-200/50 border border-slate-100">
        <div className="text-center mb-7">
          <Link href="/" className="inline-flex items-center justify-center mb-5">
            <Image
              src="/images/omniflow-logo.png"
              alt="Omniflow"
              width={160}
              height={40}
              className="h-9 w-auto object-contain"
              priority
              unoptimized
            />
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#11172F] tracking-tight">Create your workspace</h1>
          <p className="mt-2 text-sm text-slate-500">Start with your team and the workspace you&apos;ll share.</p>
        </div>
        <AuthForm mode="register" />
      </div>
    </main>
  );
}

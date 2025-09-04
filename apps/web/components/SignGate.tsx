"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useUser } from "./Providers";

export default function SignGate({ children }: { children: React.ReactNode }) {
  const { userId } = useUser();
  const router = useRouter();

  const pathname = usePathname();

  const allowedWithoutSignIn = !!pathname && pathname.startsWith("/auth");

  useEffect(() => {
    if (!userId && !allowedWithoutSignIn) {
      router.replace("/auth");
    }
  }, [userId, router, pathname, allowedWithoutSignIn]);

  // If there's no user and the current path is allowed (e.g. /connect), render children
  if (!userId && allowedWithoutSignIn) return <>{children}</>;

  if (!userId) return null;
  return <>{children}</>;
}

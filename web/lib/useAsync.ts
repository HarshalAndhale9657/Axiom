"use client";

import { useEffect, useRef, useState } from "react";

/**
 * One place where "fetch something, show it, survive failure" is solved.
 *
 * Every panel previously did `api.x().then(setState).catch(() => {})`, which turns a
 * backend hiccup into a skeleton that shimmers forever. On a live demo that is the worst
 * possible failure mode: the screen looks busy, so nobody knows anything is wrong. This
 * hook always resolves into exactly one of three states, and gives the caller a `reload`
 * so the UI can offer a retry instead of a dead end.
 *
 * Two implementation notes, both driven by the React Compiler's lint rules:
 *
 * * **No synchronous `setState` inside the effect.** Loading is *derived* — we are loading
 *   whenever the stored result does not carry the current request token — rather than
 *   flipped by an extra render pass.
 * * **The result is tokenised.** A response only lands if its token still matches, so a
 *   slow first request can never overwrite a fast second one, and nothing is written
 *   after unmount.
 *
 * `key` identifies the request: change it (e.g. `ring:${id}`) and the hook refetches.
 */
export interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  reload: () => void;
}

interface Result<T> {
  token: string;
  data: T | null;
  error: Error | null;
}

export function useAsync<T>(fetcher: () => Promise<T>, key: string): AsyncState<T> {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<Result<T> | null>(null);
  const token = `${key}#${nonce}`;

  // The fetcher is a fresh closure on every render; keep the latest one without making it
  // an effect dependency (which would refetch on every render). Written in an effect, not
  // during render, so the value stays consistent within a render pass.
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    let cancelled = false;
    fetcherRef.current().then(
      (data) => {
        if (!cancelled) setResult({ token, data, error: null });
      },
      (err: unknown) => {
        if (!cancelled) {
          setResult({ token, data: null, error: err instanceof Error ? err : new Error(String(err)) });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [token]);

  const fresh = result?.token === token ? result : null;
  return {
    data: fresh?.data ?? null,
    error: fresh?.error ?? null,
    loading: fresh === null,
    reload: () => setNonce((n) => n + 1),
  };
}

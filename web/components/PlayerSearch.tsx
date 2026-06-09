"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

interface Result {
  id: number;
  name: string;
}

export function PlayerSearch({
  onSelect,
  placeholder = "Search players…",
}: {
  onSelect?: (p: Result) => void;
  placeholder?: string;
}) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      const res = await fetch(`/api/players/search?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = (await res.json()) as { players: Result[] };
        setResults(data.players);
        setOpen(true);
      }
    }, 200);
  }, [q]);

  const choose = (p: Result) => {
    setOpen(false);
    setQ(p.name);
    if (onSelect) onSelect(p);
    else router.push(`/players/${p.id}`);
  };

  return (
    <div className="relative w-full max-w-md">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
        placeholder={placeholder}
        className="w-full rounded-lg bg-neutral-900 border border-neutral-700 px-4 py-2.5 text-sm outline-none focus:border-neutral-500"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full rounded-lg border border-neutral-700 bg-neutral-900 shadow-xl max-h-72 overflow-auto">
          {results.map((p) => (
            <li key={p.id}>
              <button
                onClick={() => choose(p)}
                className="w-full text-left px-4 py-2 text-sm hover:bg-neutral-800"
              >
                {p.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

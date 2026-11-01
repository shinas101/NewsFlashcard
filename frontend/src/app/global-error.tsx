"use client";

import React from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0b0b0d] text-zinc-100 flex items-center justify-center p-4">
        <div className="text-center space-y-4 max-w-md">
          <h2 className="text-2xl font-bold">Something went wrong</h2>
          <p className="text-zinc-400 text-sm">
            {error?.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => reset()}
            className="px-4 py-2 bg-[#9e3547] text-white rounded-lg hover:opacity-90 transition-opacity font-medium text-sm"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}


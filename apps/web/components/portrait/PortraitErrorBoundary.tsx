"use client";

import { Component, type ReactNode } from "react";

export class PortraitErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    return this.state.hasError ? (
      <div role="alert" className="rounded-2xl border border-[var(--danger)]/40 bg-[var(--bg-surface)] p-8 text-sm text-[var(--text-secondary)]">
        Portrait artwork is temporarily unavailable. Your textual portrait index remains available below.
      </div>
    ) : this.props.children;
  }
}

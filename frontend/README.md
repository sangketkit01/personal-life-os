# Personal Life OS — Frontend

Modern executive single-page web dashboard application built with **Vue 3**, **Vite**, **TypeScript**, and **Tailwind CSS**.

## Features & Modules

- **Finance Radar**: Obligations management (Subscriptions, Installments, Debts, BNPL), Cash Flow forecasting, Net Worth tracker, and burn-rate intelligence.
- **Double-Entry Ledger**: Chart of accounts, multi-legged transaction splits, budget variance tracking, and balance sheet auditing.
- **Investment Portfolio**: Real-time asset dossier, DCA cost-basis calculation, watchlist, multi-tier automated news intelligence with Thai translation, and dividends timeline.
- **Workspace & Projects**: Kanban boards, Calendar Gantt views, Notion-like block-based rich text document pages with autosave serialization, and Google Drive vault.
- **Infrastructure & Operations**: Remote SSH server web terminal, quick runbooks with mandatory confirmation modal safety, and container telemetry.

## Technology Stack

- **Framework**: [Vue 3](https://vuejs.org/) (Composition API, `<script setup>`)
- **Build Tool**: [Vite](https://vitejs.dev/) with `vue-tsc` for strict TypeScript checking
- **State Management**: [Pinia](https://pinia.vuejs.org/)
- **Routing**: [Vue Router 4](https://router.vuejs.org/) with navigation guards and autosave flush
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) with dark/light themes
- **Icons**: [Lucide Vue Next](https://lucide.dev/)
- **Terminal**: `@xterm/xterm` with WebSocket transport

## Getting Started

### Prerequisites

- Node.js >= 18
- Backend Django server running on `http://localhost:8000`

### Development

```bash
# Install dependencies
npm install

# Start Vite dev server (with proxy to backend)
npm run dev
```

### Production Build & Type-Check

```bash
# Strict type check and Vite bundle build
npm run build

# Preview production build locally
npm run preview
```

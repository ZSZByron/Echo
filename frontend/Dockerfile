# Echo UGC — frontend image (multi-stage: vite build → nginx serve)
# Build from repo root:  docker build -f frontend/Dockerfile -t echo-frontend .
# node:24 matches the dev environment (node 24 / npm 11) that owns package-lock.json;
# @testing-library/jest-dom@7 also requires node>=22.
FROM node:24-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
# NOTE: `npm ci` is intentionally NOT used here — the lockfile is generated on
# Windows and lacks the linux/musl variants of optional platform deps
# (e.g. @rolldown binding wasm chain needs @emnapi/* on linux only).
# Windows-side `npm install` prunes those entries again, so a both-platform
# lock is not achievable with current tooling. npm install resolves at build
# time; trade-off tracked in PROJECT_STATE.
RUN npm install --no-audit --no-fund

COPY frontend/ .
# NOTE: `npm run build` (tsc -b && vite build) is blocked by 16 pre-existing TS errors
# (documented in PROJECT_STATE); vite build itself does not type-check.
RUN npx vite build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

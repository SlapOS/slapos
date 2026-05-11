# npm-project

A generic SlapOS Software Release for building and serving any npm-based frontend project.

## Overview

This SR clones a Git repository containing an npm project, builds it, and serves the resulting static files via nginx. It is framework-agnostic and works with any project that follows the standard npm build convention (React, Vue, Angular, Svelte, etc.).

## How it works

Instantiation goes through four steps:

1. **Clone** — The Git repository is cloned from the URL provided in the instance parameters.
2. **Install dependencies** — `npm ci` (clean install) is run inside the cloned repository to install all dependencies from `package-lock.json` in a reproducible way.
3. **Build** — `npm run build` is executed inside the repository. This script is defined by the project itself in its `package.json` and can contain any framework-specific build steps (Vite, webpack, Next.js, etc.).
4. **Serve** — The resulting `dist/` directory is copied to a dedicated location and served by nginx.

## Instance parameters

| Parameter   | Required | Description                              |
|-------------|----------|------------------------------------------|
| `repo-url`  | ✅ Yes   | Git repository URL of the npm project. If the repo is private, include the access token directly in the URL, e.g: `https://oauth2:YOUR_ACCESS_TOKEN@lab.nexedi.com/NAMESPACE/PROJECT_NAME.git` |
| `branch`    | ✅ Yes   | Branch to clone and build                |

## Requirements

The project repository must:

- contain a `package.json` with a `build` script defined (i.e. `"scripts": { "build": "..." }`),
- produce its build output in a `dist/` directory.

## Example `package.json` scripts

```json
{
  "scripts": {
    "build": "vite build"
  }
}
```

```json
{
  "scripts": {
    "build": "react-scripts build"
  }
}
```

Any tool that writes its output to `dist/` is compatible.
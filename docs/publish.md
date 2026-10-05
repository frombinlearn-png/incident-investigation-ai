# Publish to your personal GitHub repository

Target: `https://github.com/frombinlearn-png/incident-investigation-ai`.

These instructions do not assume the repository already exists or is empty. Confirm you are signed in to **frombinlearn-png**, not an employer account. If necessary, create a public repository named `incident-investigation-ai` on that account. For the first path below, leave GitHub's README, license, and .gitignore initialization options unchecked so the remote is empty.

## Empty remote repository

Open PowerShell or a terminal **inside the extracted project folder**, then run:

```bash
git init -b main
git config user.name
git config user.email
git status --short
git add .
git diff --cached --stat
git diff --cached --name-only
git commit -m "Add runnable incident investigation RAG portfolio demo"
git remote add origin https://github.com/frombinlearn-png/incident-investigation-ai.git
git remote -v
git push -u origin main
```

The two `git config` commands only display your current identity. If either is blank or uses the wrong identity, set your desired name and email with `git config user.name "Your Name"` and `git config user.email "your-personal-email"` before committing. Use values you choose, including a GitHub no-reply address if preferred.

Before the commit, inspect the staged filename list: `.env.example` should be present, but `.env`, API keys, `.venv`, caches, and personal files must not be. GitHub authentication may open a browser; choose your personal account. Do not put a token in the remote URL.

## If the remote already contains files or commits

Do not force-push. Clone the remote into a separate folder first:

```bash
git clone https://github.com/frombinlearn-png/incident-investigation-ai.git incident-investigation-ai-upload
cd incident-investigation-ai-upload
```

Copy the extracted project contents into that clone, including `.github`, `.gitignore`, `.dockerignore`, and `.env.example`. Do not copy any `.git` directory, local `.env`, environment, or cache. Review any conflicting files before replacing them. Then run:

```bash
git status --short
git add .
git diff --cached --stat
git diff --cached --name-only
git commit -m "Add runnable incident investigation RAG portfolio demo"
git push
```

The clone retains its existing branch and upstream. If a push is rejected because the remote changed, inspect and reconcile its history; do not use `--force` to bypass it.

## Confirm the upload

Open the repository and check that `README.md`, `app`, `tests`, `docs`, dependency files, `Dockerfile`, and `.github/workflows/tests.yml` are visible. Open **Actions → Python checks** and inspect all three Python jobs; the local verification record does not certify a remote run. The folder can also be uploaded through GitHub's file uploader, but local Git is preferable for preserving hidden configuration directories.

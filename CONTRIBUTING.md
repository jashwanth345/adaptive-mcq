# Team access and collaboration

Repository: https://github.com/jashwanth345/adaptive-mcq

The repository is public. Anyone can view, download or clone the source without an invitation. Only the owner and invited collaborators can push changes to this repository. An `@username` mention in an issue or pull request does not grant write access.

## Run it on your laptop

Install Git, then open a terminal in the folder where you want the project:

```powershell
git clone https://github.com/jashwanth345/adaptive-mcq.git
cd adaptive-mcq
```

Follow [fresh Windows setup](docs/github-setup.md) before running `Start-Project.cmd`. A clone does not include Python/Node dependencies, PostgreSQL, pgvector, Ollama, model files or private configuration. Each laptop needs its own installation and private credentials. Do not copy another person's `.env` or database folder.

After setup, open `http://localhost:5173` and create your own Teacher or Student account. `localhost` means your own laptop. Separate installations do **not** share accounts, uploaded PDFs, assessments or reference codes; this is not a hosted classroom server. GitHub hosts the source, not the FastAPI/PostgreSQL/Ollama application.

The development laptop has 8 GB RAM and has not passed real LLM generation validation. A teammate's laptop still needs hardware checks: installed RAM alone is not enough; at least 1.5 GiB must be available before inference. Start with 10 questions and inspect all answers. See [current limits](docs/local-ai-fix-verification.md).

## Accept a collaborator invitation

Give the repository owner your GitHub username, not your password or access token. After the owner invites you, sign in to your own GitHub account and accept the repository invitation. Until accepted, you may clone the public repository but cannot push to it.

Authenticate pushes using your own Git credential-manager browser login or your own SSH key. Never share the owner's account or commit credentials.

## Make a change

Start from an updated `main` branch. Commit or otherwise preserve your unfinished changes before switching branches.

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/describe-your-change
```

Make the change, run the relevant tests from the [setup guide](docs/github-setup.md#tests), and inspect the files you are about to upload:

```powershell
git status
git diff
git add path/to/changed-file
git diff --cached
git commit -m "Explain what changed"
git push -u origin feature/describe-your-change
```

Use a real changed path in place of the example. On GitHub, open a pull request from your branch into `main`. Explain what changed, which tests passed and any remaining limitations. Mention a teammate with `@their-github-username` in the pull request description or comment to request review. The owner can review and merge it. This is a recommended team workflow, not a claim that branch protection is configured.

If you are not a collaborator, fork the public repository and submit a pull request from your fork instead.

## Keep private data and evidence accurate

- Never commit `.env`, credentials/tokens, uploaded student PDFs, database contents, backups, local logs or private student information.
- Keep dependencies and model binaries out of Git; use the documented preparation steps.
- Do not force-push over teammates' changes. If a pull fails, inspect the conflicting work rather than resetting it away.
- Preserve teacher/student access checks, source ownership checks and the rule that mock questions cannot be published.
- Report test fixtures as fixtures. Do not claim real MCQ accuracy, learning gains or independently trained-model verification without evidence.

## Report an issue

Open a GitHub issue with the page/feature, steps to reproduce, expected behavior and a screenshot with private information removed. Include operating system, total/free RAM, whether the app is in mock/local-AI mode, and the visible error code. Never attach `.env`, tokens, passwords or database backups.

# Launch kit — Google Flow Skill 2.3.0

Social posts below are drafts. No X, Reddit, Hacker News or YouTube account was
available during preparation. The PyPI account and publisher setup are also
pending. GitHub publication is tracked separately from social distribution.

## Core message

Give your AI agent a script and let it generate/download the scenes in Google
Flow. Show the workflow and output before explaining the implementation.

Proof: the release includes an installable CLI, a complete agent manual,
ordered batch examples, automated package checks and a demo made from existing
Flow footage. Do not describe the demo as a fresh 2.3.0 live generation test.

## X — launch post

Google Flow Skill lets your AI agent run image/video scripts in Flow: ordered
batches, reusable references and credit checks.

Free, open-source code. Flow generation may cost credits.

Demo + install:
https://github.com/DiegoLopez0208/google-flow-skill

Attach `google-flow-demo-en.mp4`. Do not add unsupported speed, savings or
character-consistency claims.

## Reddit — r/ClaudeAI

Title: I made a Claude Code plugin to run image/video scripts in Google Flow

I maintain Google Flow Skill, an open-source CLI and Claude Code plugin for
generating and downloading images and videos in Google Flow.

The workflow is: give the agent a script, let it create an ordered JSON batch,
then inspect the downloaded files and batch report. Earlier image jobs can be
reused as ingredients or first frames for later video jobs. The CLI checks the
credit balance against a rough batch estimate and reads video price quotes
from Flow's UI when available.

Version 2.3.0 adds an installable Python package and fixes the plugin marketplace
setup. The attached demo uses existing real Flow footage, with edited waits
and captions. It does not claim a fresh generation test of this release.

The source code is free. You need Python 3.10+, Google Chrome and access to
Google Flow; generation can consume your account's credits. References help
continuity but do not guarantee identical characters. This is an unofficial
browser integration and some selectors currently expect Spanish UI labels.

Install, demo and examples:
https://github.com/DiegoLopez0208/google-flow-skill

The project started from BRPLia/google-flow-skill-v1 (MIT), with attribution
preserved. I maintain the browser port and distribution in this repository.

Before posting, check the community's current rules, flair and account karma
requirements. This is a plugin specifically for Claude Code; do not claim it
was built using Claude unless that is independently true.

## Show HN

Title: Show HN: Google Flow Skill — run image/video scripts from an AI agent

URL: https://github.com/DiegoLopez0208/google-flow-skill

First comment:

I maintain a CLI + agent skill for Google Flow. The agent turns a scene script
into ordered image/video jobs, runs them in one Flow project, and reads a batch
report with downloaded files or errors.

It supports image references, first/last frames, variants and credit checks.
Generation uses Chrome; downloads prefer Flow's internal HTTP endpoints with
a browser fallback. There is no API-only generation path here.

2.3.0 adds Python packaging, an executable CLI, bundled examples/manual,
a Claude Code marketplace and installed-package CI. The code is MIT-licensed;
Google Flow access and generation costs belong to the user's Google account.

Limits: unofficial integration, some Spanish UI selectors, no project resume,
and character continuity is not guaranteed. Packaging checks don't validate
the current live Flow UI. A short demo and versioned wheel are in Releases.

## YouTube Shorts

Title: Your AI agent can run Google Flow image and video scripts

Description:

Google Flow Skill gives an AI agent a CLI for ordered image/video jobs,
references, first/last frames and downloads.

This demo uses previously recorded Google Flow footage and generated output,
with edited waits and English captions. The code is free; Flow access and
generation may cost credits. Requires Python 3.10+ and Google Chrome.

Install and examples: https://github.com/DiegoLopez0208/google-flow-skill

#GoogleFlow #AIAgents #GenerativeVideo

## Optional creator-community post

Use a finished clip as the main post, with a workflow explanation. Check that
the chosen community allows tool links before posting. Do not drop the same
repository-only promotion across unrelated communities.

## Posting sequence

| Day | Action | Success signal |
|---|---|---|
| 1 | Publish GitHub release, demo and clear install instructions | Clean install completes |
| 2 | X demo post; respond to real install issues | First users complete a job |
| 3 | Claude Code workflow post on Reddit, if account/rules allow | Useful reproduction feedback |
| 4 | Fix reported setup problems; add answers to README | Fewer setup failures |
| 5 | Show HN with runnable instructions | Technical feedback and actual attempts |
| 6 | YouTube Short + a longer installation walkthrough | Viewers reach the install instructions |
| 7 | Review results and choose the next improvement | Successful installs/batches, not only stars |

Use the sequence relative to the day accounts become available; these posts
have not been scheduled. Prepare the longer tutorial with current install
screens before publishing it.

## Account setup still needed

- PyPI: create an account and configure the publisher in `docs/RELEASING.md`.
- Social channels: create/sign in to the desired accounts, then publish the
  drafts with the demo. Never paste credentials into source files or posts.
- skills.sh: the installer records eligible installation telemetry; there is
  no separate registry submission in this workflow. A tested install command
  does not guarantee an immediate listing or leaderboard position.

Sources used when preparing this kit:
- https://skills.sh/docs
- https://www.reddit.com/r/ClaudeAI/ (community rules)
- https://news.ycombinator.com/showhn.html
- Repository README, CLI, changelog, examples and recorded Flow footage.

# CI/CD style: pipelines you can trust

Bashou teaches CI on the two services players meet most: GitHub Actions (`.github/workflows/*.yml`)
and GitLab CI (`.gitlab-ci.yml`). Same ideas (jobs, order, conditions, secrets), different words.

This file is the checklist for every CI sample in Bashou: the lesson `pipeline`, the cicd adventure
questions, the fights of `bashou/challenges/cicd.py`, their hints and files. The `cicd-judge` agent
(`.claude/agents/cicd-judge.md`) applies it after each change, and `tests/test_cicd_style.py` checks
the text players read.

Each rule has an id, used in reviews. A sample that breaks a rule on purpose (a wrong choice, the
mistake a fight shows) is marked ✘ and followed by the right form. The right answer, its explanation
and the hints must follow the rules.

Facts are checked against the services' own docs (docs.github.com, docs.gitlab.com) and by parsing the
YAML (`python3 -c 'import yaml…'` or the fight's own parser), never from memory.

| Id | Rule | Why | Source |
|---|---|---|---|
| CI1 | YAML is indented with spaces, never tabs; a key's children are indented more than the key. Values that YAML would read as something else (`on`, `yes`, `no`, `1.10`) are quoted when they are data. | Most broken pipelines are broken YAML. | [YAML 1.2.2: indentation](https://yaml.org/spec/1.2.2/#61-indentation-spaces) |
| CI2 | GitHub Actions: jobs run in parallel unless `needs:` says otherwise; a job whose `needs` failed is skipped. Steps of one job run in order. | "Deploy ran although test failed." | [GitHub: jobs.<id>.needs](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds) |
| CI3 | GitLab: stages run in order, jobs of a stage in parallel; `needs:` starts a job earlier than its stage. Without `stages:` the default list is `.pre, build, test, deploy, .post`, and a job with no `stage:` is in `test`. | Players read both orders. | [GitLab: CI/CD YAML syntax](https://docs.gitlab.com/ci/yaml/) |
| CI4 | GitLab conditions use `rules:` (and `workflow:rules:` for the whole pipeline), not `only:`/`except:`, which GitLab has deprecated. `when: manual` inside `rules` blocks the pipeline until clicked (`allow_failure: false`); outside `rules` it doesn't. | Old tutorials, and a manual deploy that "doesn't stop" anything. | [GitLab: rules](https://docs.gitlab.com/ci/yaml/#rules), [GitLab: deprecated keywords](https://docs.gitlab.com/ci/yaml/deprecated_keywords/) |
| CI5 | Secrets never in the pipeline file: GitHub `${{ secrets.NAME }}`, GitLab CI/CD variables (protected, masked and hidden). A secret that was committed or printed is rotated, not only deleted. Masking is a help, not a guarantee: don't echo secrets. | The file and its history are read by everyone with access. | [GitHub: secure use](https://docs.github.com/en/actions/reference/security/secure-use), [GitLab: CI/CD variables](https://docs.gitlab.com/ci/variables/) |
| CI6 | Untrusted input (a PR title, a branch name: `github.event.*`, `github.head_ref`) is never written into `run:` with `${{ }}`: pass it through `env:` and use `"$VAR"`. | Script injection: the title becomes shell code. | [GitHub: secure use, script injection](https://docs.github.com/en/actions/reference/security/secure-use#use-an-intermediate-environment-variable) |
| CI7 | Least privilege: `permissions:` set to what the job needs (`contents: read` by default). No `pull_request_target` that checks out the PR's code. | Fork code would run with the repository's write token and secrets. | [GitHub: secure use](https://docs.github.com/en/actions/reference/security/secure-use), [GitHub: GITHUB_TOKEN permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token) |
| CI8 | Third-party actions are pinned: a full commit SHA, or a tag from a publisher you trust (a tag can be moved). GitLab: an image tag, not `latest`, for what must not change. | A moved tag runs someone else's code in your pipeline. | [GitHub: secure use, third-party actions](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions) |
| CI9 | A job's success is its script's exit status: a command that fails must make the job fail (`set -e` habits from bash-style, no `\|\| true` to make it green). | A green pipeline that tested nothing. | [GitLab: script](https://docs.gitlab.com/ci/yaml/#script), [GitHub: exit codes](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/set-exit-codes) |
| CI10 | Deploying to production is limited: a branch condition (`if: github.ref == 'refs/heads/main'`, `$CI_COMMIT_BRANCH == "main"`), and an environment with approval or a manual job. | A push on any branch must not ship. | [GitHub: environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments), [GitLab: environments](https://docs.gitlab.com/ci/environments/) |

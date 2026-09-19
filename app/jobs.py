"""
Jobs API helper for /pipelines — list the bundle's jobs, their recent runs,
and trigger new runs. The App's service principal has CAN_MANAGE_RUN on each
job (see resources/jobs/*.job.yml `permissions:`), never CAN_MANAGE: this can
monitor and re-run pipelines, not edit their definition.
"""

from databricks.sdk import WorkspaceClient

# Bundle jobs this App is allowed to see, in pipeline order — deliberately not
# "every job in the workspace" (jobs.list() would only return ones this SP has
# CAN_VIEW+ on anyway, but pinning the set keeps /pipelines' ordering stable
# and independent from what else might get deployed to this workspace later).
# Substring, not suffix: display names can carry a trailing annotation (e.g.
# "ocarina — graph build (GraphFrames)").
_JOB_NAME_MARKERS = (
    "ocarina — smoke test",
    "ocarina — bronze ingestion",
    "ocarina — silver transform",
    "ocarina — ops quality checks",
    "ocarina — gold transform",
    "ocarina — graph build",
)

_client = WorkspaceClient()


def _marker_in(name: str) -> str | None:
    return next((m for m in _JOB_NAME_MARKERS if m in name), None)


def list_pipeline_jobs() -> list[dict]:
    jobs = [j for j in _client.jobs.list() if j.settings and _marker_in(j.settings.name or "")]
    order = {m: i for i, m in enumerate(_JOB_NAME_MARKERS)}
    jobs.sort(key=lambda j: order[_marker_in(j.settings.name)])

    out = []
    for j in jobs:
        runs = list(_client.jobs.list_runs(job_id=j.job_id, limit=1))
        latest = runs[0] if runs else None
        out.append(
            {
                "job_id": j.job_id,
                "name": j.settings.name,
                "latest_run": _run_summary(latest) if latest else None,
            }
        )
    return out


def list_runs(job_id: int, limit: int = 10) -> list[dict]:
    runs = _client.jobs.list_runs(job_id=job_id, limit=limit)
    return [_run_summary(r) for r in runs]


def run_now(job_id: int) -> dict:
    waiter = _client.jobs.run_now(job_id=job_id)
    return {"run_id": waiter.run_id}


def _run_summary(run) -> dict:
    state = run.state
    return {
        "run_id": run.run_id,
        "life_cycle_state": state.life_cycle_state.value if state and state.life_cycle_state else None,
        "result_state": state.result_state.value if state and state.result_state else None,
        "state_message": state.state_message if state else None,
        "start_time": run.start_time,
        "run_page_url": run.run_page_url,
    }

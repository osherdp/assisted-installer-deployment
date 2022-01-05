#!/usr/bin/env python3
import os
import enum
import argparse
import collections
import datetime
import dataclasses
import itertools

import requests
import matplotlib.pyplot as plt


PROW_JOBS_STATUSES = "https://prow.ci.openshift.org/prowjobs.js?omit=annotations,labels,decoration_config,pod_spec"
SLACK_FILES_UPLOAD = "https://slack.com/api/files.upload"
TRACKED_REPOSITORIES = list(itertools.chain(
    itertools.product(
        ("openshift",), (
            "assisted-test-infra",
            "assisted-service",
            "assisted-image-service",
            "assisted-installer",
            "assisted-installer-agent",
        )),
    itertools.product(
        ("openshift-assisted",), (
            "assisted-installer-deployment",
            "assisted-events-scrape",
        )),
))


class State(enum.Enum):
    TRIGGERED = "triggered"  # job created but not yet scheduled
    PENDING = "pending"  # job is currently running
    SUCCESS = "success"  # job completed without any error
    FAILURE = "failure"  # job completed with errors
    ABORTED = "aborted"  # prow killed the job early (new commit pushed, perhaps)
    ERROR = "error"  # job could not schedule (bad config, perhaps)


class JobType(enum.Enum):
    PRESUBMIT = "presubmit"
    POSTSUBMIT = "postsubmit"
    PERIODIC = "periodic"
    BATCH = "batch"


STATE_TO_COLOR = {
    State.PENDING: "#FFD166",
    State.ABORTED: "#118AB2",
    State.FAILURE: "#EF476F",
    State.ERROR: "pink",
    State.SUCCESS: "#06D6A0",
}


@dataclasses.dataclass
class Job:
    type: JobType
    name: str
    organization: str
    repository: str
    base_ref: str
    state: State
    url: str
    start_time: datetime.datetime
    completion_time: datetime.datetime


def filter_jobs(response):
    for document in response.json()["items"]:
        all_refs = document["spec"].get("extra_refs", [])

        refs = document["spec"].get("refs")
        if refs is not None:
            all_refs.append(refs)

        for ref in all_refs:
            organization = ref["org"]
            repository = ref["repo"]
            base_ref = ref["base_ref"]
            if (organization, repository) in TRACKED_REPOSITORIES:
                break

        else:
            continue

        job = Job(
            type=JobType(document["spec"]["type"]),
            name=document["spec"]["job"],
            organization=organization,
            repository=repository,
            base_ref=base_ref,
            state=State(document["status"]["state"]),
            url=document["status"]["url"],
            start_time=document["status"]["startTime"],
            completion_time=document["status"].get("completionTime"),
        )

        if (job.organization, job.repository) in TRACKED_REPOSITORIES:
            yield job


def get_jobs_statistics():
    response = requests.get(PROW_JOBS_STATUSES)
    response.raise_for_status()

    status_counters = collections.defaultdict(collections.Counter)
    for job in filter_jobs(response):
        status_counters[job.name].update([job.state])

    # removing jobs that have no problems
    for job, counters in list(status_counters.items()):
        if counters[State.ERROR] == 0 and counters[State.FAILURE] == 0:
            del status_counters[job]

    return status_counters


def draw_figure(status_counters):
    _, ax = plt.subplots(figsize=(15,15))

    for state, color in STATE_TO_COLOR.items():
        ax.bar(
            status_counters.keys(),
            [counters[state] for counters in status_counters.values()],
            label=state,
            color=color,
        )

    ax.legend()
    plt.xticks(rotation='90')
    plt.subplots_adjust(bottom=0.6)
    return plt


def ci_status_report(channel, auth_bearer):
    status_counters = get_jobs_statistics()

    for job, states in status_counters.items():
        print(f"{job}:")
        print("\t", end="")
        for state, count in states.items():
            print(f"{state}: {count}", end="\t")

        print()

    plt = draw_figure(status_counters)
    plt.savefig("/tmp/jobs.png")

    if channel is None:
        plt.show()
    else:
        with open("/tmp/jobs.png", "rb") as image:
            response = requests.post(
                SLACK_FILES_UPLOAD,
                headers={"Authorization": f"Bearer {auth_bearer}"},
                files={
                    "file": (image.name, image),
                    "initial_comment": (None, "Daily jobs status"),
                    "channels": (None, channel),
                }
            )
            response.raise_for_status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default=os.environ.get("SLACK_CHANNEL"),
                        help="Slack channel for posting the information. Not specifying implies dry-run")
    parser.add_argument("--auth-bearer", default=os.environ.get("SLACK_AUTH_BEARER"),
                        help="Slack OAuth token of the bot/user.")
    args = parser.parse_args()

    ci_status_report(args.channel, args.auth_bearer)


if __name__ == "__main__":
    main()

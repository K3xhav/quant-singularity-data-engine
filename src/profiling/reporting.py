from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from src.profiling.models import ProfilingFinding, Severity


def write_findings_json(findings: list[ProfilingFinding], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [finding.model_dump(mode="json") for finding in findings]
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown_summary(findings: list[ProfilingFinding], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    severity_counts = Counter(finding.severity.value for finding in findings)
    dataset_counts = Counter(finding.dataset for finding in findings)
    rule_counts = Counter(finding.rule for finding in findings)
    grouped_by_severity = _group_by_severity(findings)
    grouped_by_dataset = _group_by_dataset(findings)
    affected_dataset_counts = _count_affected_datasets(findings)

    lines: list[str] = [
        "# Profiling Summary",
        "",
        f"Total findings: **{len(findings)}**",
        "",
        "## Findings by Severity",
    ]

    for severity in Severity:
        lines.append(f"- {severity.value}: {severity_counts.get(severity.value, 0)}")

    lines.extend(["", "## Findings by Dataset"])
    for dataset in sorted(dataset_counts):
        lines.append(f"- {dataset}: {dataset_counts[dataset]}")
    if not dataset_counts:
        lines.append("- none: 0")

    lines.extend(["", "## Top Recurring Anomaly Types"])
    if rule_counts:
        for rule, count in sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))[:5]:
            lines.append(f"- {rule}: {count}")
    else:
        lines.append("- none: 0")

    lines.extend(["", "## Affected Dataset Counts"])
    if affected_dataset_counts:
        for rule in sorted(affected_dataset_counts):
            lines.append(f"- {rule}: {affected_dataset_counts[rule]}")
    else:
        lines.append("- none: 0")

    lines.extend(["", "## Engineering Observations"])
    observations = _build_observations(findings)
    for observation in observations:
        lines.append(f"- {observation}")

    lines.extend(["", "## Severity Details"])
    for severity in Severity:
        lines.append(f"### {severity.value}")
        severity_findings = grouped_by_severity[severity.value]
        if not severity_findings:
            lines.append("- No findings.")
            continue
        for finding in severity_findings:
            lines.append(
                "- "
                f"`{finding.dataset}` / `{finding.file_name}` / `{finding.rule}`: "
                f"{finding.message} Affected rows: {finding.affected_rows}."
            )

    lines.extend(["", "## Dataset Details"])
    for dataset in sorted(grouped_by_dataset):
        lines.append(f"### {dataset}")
        for finding in grouped_by_dataset[dataset]:
            lines.append(
                "- "
                f"[{finding.severity.value}] `{finding.file_name}` / `{finding.rule}`: "
                f"{finding.message} Affected rows: {finding.affected_rows}."
            )
    if not grouped_by_dataset:
        lines.extend(["### none", "- No findings."])

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _group_by_severity(findings: list[ProfilingFinding]) -> dict[str, list[ProfilingFinding]]:
    grouped: dict[str, list[ProfilingFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.severity.value].append(finding)
    return grouped


def _group_by_dataset(findings: list[ProfilingFinding]) -> dict[str, list[ProfilingFinding]]:
    grouped: dict[str, list[ProfilingFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.dataset].append(finding)
    return grouped


def _count_affected_datasets(findings: list[ProfilingFinding]) -> dict[str, int]:
    rule_to_datasets: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        rule_to_datasets[finding.rule].add(finding.dataset)
    return {rule: len(rule_to_datasets[rule]) for rule in sorted(rule_to_datasets)}


def _build_observations(findings: list[ProfilingFinding]) -> list[str]:
    if not findings:
        return ["No anomalies detected in the scanned files."]

    observations: list[str] = []
    rule_counts = Counter(finding.rule for finding in findings)
    dataset_counts = Counter(finding.dataset for finding in findings)

    top_rule, top_rule_count = sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))[0]
    observations.append(f"Most frequent anomaly type: `{top_rule}` ({top_rule_count} findings).")

    top_dataset, top_dataset_count = sorted(
        dataset_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[0]
    observations.append(f"Highest anomaly concentration: `{top_dataset}` ({top_dataset_count} findings).")

    critical_count = sum(1 for finding in findings if finding.severity == Severity.CRITICAL)
    if critical_count > 0:
        observations.append(f"Critical issues remain concentrated in market data integrity checks ({critical_count} findings).")
    else:
        observations.append("No critical integrity findings were detected.")

    return observations

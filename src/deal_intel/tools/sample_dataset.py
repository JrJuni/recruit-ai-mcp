from __future__ import annotations

import json
from copy import deepcopy
from importlib import resources

from deal_intel.schema.recruiting_match import build_candidate_position_fit
from deal_intel.storage.recruiting_collections import (
    CANDIDATES,
    CLIENT_COMPANIES,
    FEEDBACK,
    INTERACTIONS,
    POSITIONS,
    SUBMISSIONS,
    recruiting_id_field,
)

DATASET_WEEKLY_PIPELINE = "weekly_pipeline_demo"
DATASET_RECRUITING_PIPELINE = "recruiting_pipeline_demo"
DEAL_DATASET_VERSION = "2026-06-14.v2"
RECRUITING_DATASET_VERSION = "2026-06-22.v6"
SAMPLE_BATCH_ID = f"{DATASET_WEEKLY_PIPELINE}:{DEAL_DATASET_VERSION}"
RECRUITING_SAMPLE_BATCH_ID = (
    f"{DATASET_RECRUITING_PIPELINE}:{RECRUITING_DATASET_VERSION}"
)
SUPPORTED_DATASETS = frozenset({DATASET_WEEKLY_PIPELINE, DATASET_RECRUITING_PIPELINE})

_RESOURCE_PACKAGE = "deal_intel.resources.sample_datasets"
_WEEKLY_PIPELINE_RESOURCE = "weekly_pipeline_demo.v2.json"


def build_sample_deals(*, loaded_at: str) -> list[dict]:
    """Return public fictional demo deals for Atlas demo-database seeding.

    This dataset is richer than the zero-config local fixture and is intended
    for `full`/MongoDB demos. It is still opt-in only: callers must use
    `create_sample_data`, which writes to a separate demo database by default.
    """

    deals = _load_dataset()
    for deal in deals:
        deal["updated_at"] = loaded_at
        deal["sample_loaded_at"] = loaded_at
        deal["is_sample"] = True
        deal["sample_batch_id"] = SAMPLE_BATCH_ID
        deal["sample_dataset"] = DATASET_WEEKLY_PIPELINE
        deal["sample_dataset_version"] = DEAL_DATASET_VERSION
        deal["sample_label"] = "Full Pipeline Review demo"
    return deepcopy(deals)


def build_sample_recruiting_records(*, loaded_at: str) -> dict[str, list[dict]]:
    """Return fictional recruiting demo records for Atlas demo-database seeding.

    Unlike deal demo rows, recruiting records intentionally do not store sample
    marker fields. The recruiting Pydantic models reject unknown keys, and the
    metrics/recommendation paths validate stored records on read. Sample
    cleanup therefore uses this dataset's stable fictional IDs.
    """

    records = _base_recruiting_records(loaded_at=loaded_at)
    feedback = records[FEEDBACK]
    candidates = {
        candidate["candidate_id"]: candidate
        for candidate in records[CANDIDATES]
    }
    positions = {
        position["position_id"]: position
        for position in records[POSITIONS]
    }
    for submission in records[SUBMISSIONS]:
        if submission["status"] == "submitted":
            continue
        fit = build_candidate_position_fit(
            candidate=candidates[submission["candidate_id"]],
            position=positions[submission["position_id"]],
            client_feedback=feedback,
        )
        submission["fit_snapshot"] = fit.snapshot.model_dump(mode="json")
    return deepcopy(records)


def sample_batch_id(dataset: str) -> str:
    if dataset == DATASET_RECRUITING_PIPELINE:
        return RECRUITING_SAMPLE_BATCH_ID
    return SAMPLE_BATCH_ID


def sample_preview(deals: list[dict], *, limit: int = 3) -> list[dict]:
    return [
        {
            "deal_id": deal["deal_id"],
            "company": deal["company"],
            "deal_stage": deal["deal_stage"],
            "industry": deal["industry"],
            "industry_tags": deal.get("industry_tags") or [],
            "customer_segment": deal.get("customer_segment"),
            "deal_size_amount": deal["deal_size_amount"],
            "deal_size_currency": deal["deal_size_currency"],
            "health_pct": deal["meddpicc_latest"].get("health_pct"),
        }
        for deal in deals[:limit]
    ]


def recruiting_sample_preview(records: dict[str, list[dict]]) -> dict[str, list[dict]]:
    return {
        CANDIDATES: [
            {
                "candidate_id": row["candidate_id"],
                "name": row["name"],
                "current_title": row.get("current_title", ""),
                "skills": row.get("skills", [])[:5],
            }
            for row in records.get(CANDIDATES, [])[:3]
        ],
        CLIENT_COMPANIES: [
            {
                "client_company_id": row["client_company_id"],
                "name": row["name"],
                "industry": row.get("industry", ""),
            }
            for row in records.get(CLIENT_COMPANIES, [])[:3]
        ],
        POSITIONS: [
            {
                "position_id": row["position_id"],
                "client_company_id": row["client_company_id"],
                "title": row["title"],
                "status": row["status"],
            }
            for row in records.get(POSITIONS, [])[:3]
        ],
        SUBMISSIONS: [
            {
                "submission_id": row["submission_id"],
                "candidate_id": row["candidate_id"],
                "position_id": row["position_id"],
                "status": row["status"],
            }
            for row in records.get(SUBMISSIONS, [])[:3]
        ],
    }


def recruiting_sample_ids(records: dict[str, list[dict]]) -> dict[str, list[str]]:
    return {
        collection: [row[recruiting_id_field(collection)] for row in rows]
        for collection, rows in records.items()
    }


def recruiting_record_counts(records: dict[str, list[dict]]) -> dict[str, int]:
    return {collection: len(rows) for collection, rows in records.items()}


def _load_dataset() -> list[dict]:
    resource = resources.files(_RESOURCE_PACKAGE).joinpath(_WEEKLY_PIPELINE_RESOURCE)
    with resource.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{_WEEKLY_PIPELINE_RESOURCE} must contain a JSON array")
    return data


def _base_recruiting_records(*, loaded_at: str) -> dict[str, list[dict]]:
    clients = [
        {
            "client_company_id": "client_northstar_health",
            "name": "Northstar Health",
            "industry": "healthcare technology",
            "stage": "growth",
            "locations": ["Boston", "Remote US"],
            "hiring_preferences": [
                "Prefers candidates who have scaled regulated data platforms.",
                "Values written architecture rationale over brand-name pedigree.",
            ],
            "feedback_patterns": [
                "Positive on backend leaders with healthcare data fluency.",
            ],
            "risk_notes": ["Needs compensation alignment before onsite loops."],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "client_company_id": "client_orbitpay",
            "name": "OrbitPay",
            "industry": "fintech",
            "stage": "series b",
            "locations": ["New York", "Remote US"],
            "hiring_preferences": [
                "Looks for payments domain evidence and pragmatic execution.",
                "Rejects candidates who need heavy role-shaping before interviews.",
            ],
            "feedback_patterns": [
                "Strong response to candidates with risk and compliance experience.",
            ],
            "risk_notes": [],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
    ]
    candidates = [
        {
            "candidate_id": "cand_avery_chen",
            "name": "Avery Chen",
            "headline": "Backend platform lead for regulated data products",
            "current_company": "Clearpath Systems",
            "current_title": "Staff Backend Engineer",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Kafka", "HIPAA"],
            "domains": ["healthcare", "data platforms", "workflow automation"],
            "seniority": "staff",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 185000,
                "target": 205000,
                "maximum": 225000,
                "period": "annual",
                "note": "Flexible for strong healthcare mission fit.",
            },
            "locations": ["Boston", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "30 days",
            "preferences": {
                "desired_titles": ["Staff Backend Engineer", "Backend Lead"],
                "preferred_domains": ["healthcare", "data platforms"],
                "preferred_locations": ["Boston", "Remote US"],
                "remote_preference": "hybrid or remote",
                "excluded_companies": [],
                "notes": "Prefers product teams with clear customer evidence.",
            },
            "risk_flags": [],
            "evidence": [
                {
                    "evidence_id": "ev_avery_profile",
                    "source_type": "profile",
                    "source_id": "cand_avery_chen",
                    "summary": "Built healthcare data ingestion and workflow systems.",
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_mateo_rivera",
            "name": "Mateo Rivera",
            "headline": "Payments product engineer with compliance depth",
            "current_company": "LedgerLane",
            "current_title": "Senior Software Engineer",
            "skills": ["Java", "Kotlin", "Kafka", "Payments", "Risk"],
            "domains": ["fintech", "payments", "risk operations"],
            "seniority": "senior",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 175000,
                "target": 190000,
                "maximum": 215000,
                "period": "annual",
                "note": "",
            },
            "locations": ["New York", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "45 days",
            "preferences": {
                "desired_titles": ["Senior Software Engineer", "Tech Lead"],
                "preferred_domains": ["fintech", "payments"],
                "preferred_locations": ["New York", "Remote US"],
                "remote_preference": "remote-first",
                "excluded_companies": [],
                "notes": "Wants customer-facing product impact.",
            },
            "risk_flags": [],
            "evidence": [
                {
                    "evidence_id": "ev_mateo_profile",
                    "source_type": "profile",
                    "source_id": "cand_mateo_rivera",
                    "summary": "Led payment risk workflow rebuild.",
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_priya_shah",
            "name": "Priya Shah",
            "headline": "Product analytics leader for growth-stage SaaS",
            "current_company": "Northlake AI",
            "current_title": "Analytics Lead",
            "skills": ["SQL", "dbt", "Looker", "Experimentation", "Python"],
            "domains": ["saas", "product analytics", "growth"],
            "seniority": "lead",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 165000,
                "target": 180000,
                "maximum": 200000,
                "period": "annual",
                "note": "",
            },
            "locations": ["Remote US", "Austin"],
            "work_authorization": "US authorized",
            "availability": "60 days",
            "preferences": {
                "desired_titles": ["Product Analytics Lead", "Analytics Manager"],
                "preferred_domains": ["saas", "healthcare"],
                "preferred_locations": ["Remote US"],
                "remote_preference": "remote",
                "excluded_companies": [],
                "notes": "Prefers teams with clear instrumentation maturity.",
            },
            "risk_flags": ["limited regulated healthcare experience"],
            "evidence": [
                {
                    "evidence_id": "ev_priya_profile",
                    "source_type": "profile",
                    "source_id": "cand_priya_shah",
                    "summary": "Owned product analytics and experimentation programs.",
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_lin_park",
            "name": "Lin Park",
            "headline": "Engineering manager for data platform teams",
            "current_company": "AtlasForge",
            "current_title": "Engineering Manager",
            "skills": ["Python", "Spark", "Airflow", "Team Leadership", "Data Platform"],
            "domains": ["data infrastructure", "enterprise software"],
            "seniority": "manager",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 210000,
                "target": 235000,
                "maximum": 260000,
                "period": "annual",
                "note": "Requires manager scope.",
            },
            "locations": ["Seattle", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "not actively looking",
            "preferences": {
                "desired_titles": ["Engineering Manager", "Head of Data Engineering"],
                "preferred_domains": ["data infrastructure", "healthcare"],
                "preferred_locations": ["Remote US", "Seattle"],
                "remote_preference": "remote or Seattle hybrid",
                "excluded_companies": [],
                "notes": "Open only for manager scope and strong platform mandate.",
            },
            "risk_flags": ["passive candidate", "requires manager scope"],
            "evidence": [
                {
                    "evidence_id": "ev_lin_profile",
                    "source_type": "profile",
                    "source_id": "cand_lin_park",
                    "summary": "Managed data platform team through scale-up.",
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_nora_weiss",
            "name": "Nora Weiss",
            "headline": "Healthcare platform architect with relocation constraints",
            "current_company": "MedLedger Labs",
            "current_title": "Principal Platform Engineer",
            "skills": ["Python", "Kafka", "HIPAA", "Data Platforms", "Healthcare"],
            "domains": ["healthcare", "data platforms", "regulated infrastructure"],
            "seniority": "principal",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 260000,
                "target": 290000,
                "maximum": 320000,
                "period": "annual",
                "note": "Requires premium package and relocation support.",
            },
            "locations": ["London"],
            "work_authorization": "UK authorized",
            "availability": "90 days",
            "preferences": {
                "desired_titles": ["Principal Platform Engineer", "Architect"],
                "preferred_domains": ["healthcare", "regulated infrastructure"],
                "preferred_locations": ["London", "Remote Europe"],
                "remote_preference": "remote Europe only",
                "excluded_companies": [],
                "notes": "Open only for architect scope with relocation support.",
            },
            "risk_flags": [
                "compensation above current budget",
                "requires UK remote exception",
                "late availability",
            ],
            "evidence": [
                {
                    "evidence_id": "ev_nora_profile",
                    "source_type": "profile",
                    "source_id": "cand_nora_weiss",
                    "summary": "Architected regulated healthcare event platforms.",
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_jordan_lee",
            "name": "Jordan Lee",
            "headline": "Healthcare workflow platform engineer from the Node ecosystem",
            "current_company": "ClinicFlow",
            "current_title": "Staff Software Engineer",
            "skills": ["TypeScript", "Node.js", "Kafka", "HIPAA", "Healthcare"],
            "domains": ["healthcare", "workflow automation"],
            "seniority": "staff",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 180000,
                "target": 198000,
                "maximum": 215000,
                "period": "annual",
                "note": "Aligned if the role can use healthcare workflow depth.",
            },
            "locations": ["Boston", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "30 days",
            "preferences": {
                "desired_titles": ["Staff Software Engineer", "Platform Engineer"],
                "preferred_domains": ["healthcare", "workflow automation"],
                "preferred_locations": ["Boston", "Remote US"],
                "remote_preference": "hybrid or remote",
                "excluded_companies": ["client_northstar_health"],
                "notes": (
                    "Needs confirmation on production Python and data platform "
                    "depth, and asked not to be resubmitted to Northstar."
                ),
            },
            "risk_flags": ["missing production Python evidence"],
            "evidence": [
                {
                    "evidence_id": "ev_jordan_profile",
                    "source_type": "profile",
                    "source_id": "cand_jordan_lee",
                    "summary": (
                        "Strong healthcare workflow background, but captured "
                        "backend evidence is TypeScript/Node rather than Python."
                    ),
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_eli_brooks",
            "name": "Eli Brooks",
            "headline": "Healthcare data platform manager seeking org ownership",
            "current_company": "CareGrid",
            "current_title": "Engineering Manager",
            "skills": ["Python", "Kafka", "HIPAA", "Data Platforms", "Healthcare"],
            "domains": ["healthcare", "data platforms", "regulated infrastructure"],
            "seniority": "manager",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 245000,
                "target": 270000,
                "maximum": 300000,
                "period": "annual",
                "note": "Only interested in manager scope with team ownership.",
            },
            "locations": ["Remote US"],
            "work_authorization": "US authorized",
            "availability": "not actively looking",
            "preferences": {
                "desired_titles": ["Engineering Manager", "Head of Platform"],
                "preferred_domains": ["healthcare", "data platforms"],
                "preferred_locations": ["Remote US"],
                "remote_preference": "remote",
                "excluded_companies": [],
                "notes": "Would decline a staff IC mandate without direct reports.",
            },
            "risk_flags": [
                "requires manager scope",
                "compensation above current budget",
                "passive candidate",
            ],
            "evidence": [
                {
                    "evidence_id": "ev_eli_profile",
                    "source_type": "profile",
                    "source_id": "cand_eli_brooks",
                    "summary": (
                        "Healthcare platform background is strong, but Eli wants "
                        "management ownership rather than a staff IC mandate."
                    ),
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_iris_kim",
            "name": "Iris Kim",
            "headline": "Payments engineer ready for larger ownership",
            "current_company": "CheckoutWorks",
            "current_title": "Junior Payments Engineer",
            "skills": ["Payments", "Kafka", "Risk", "Java", "Kotlin"],
            "domains": ["fintech", "payments", "risk operations"],
            "seniority": "junior",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 135000,
                "target": 150000,
                "maximum": 165000,
                "period": "annual",
                "note": "Compensation is flexible for a growth role.",
            },
            "locations": ["New York", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "immediate",
            "preferences": {
                "desired_titles": ["Payments Engineer", "Software Engineer"],
                "preferred_domains": ["fintech", "payments"],
                "preferred_locations": ["New York", "Remote US"],
                "remote_preference": "remote-first",
                "excluded_companies": [],
                "notes": "Wants mentorship before owning a full platform lead scope.",
            },
            "risk_flags": ["needs senior mentorship for platform lead scope"],
            "evidence": [
                {
                    "evidence_id": "ev_iris_profile",
                    "source_type": "profile",
                    "source_id": "cand_iris_kim",
                    "summary": "Built payments risk event consumers under senior guidance.",
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_sam_taylor",
            "name": "Sam Taylor",
            "headline": "Payments platform engineer who needs role shaping",
            "current_company": "RiskRail",
            "current_title": "Senior Payments Engineer",
            "skills": ["Payments", "Kafka", "Risk", "Java", "Kotlin"],
            "domains": ["fintech", "payments", "risk operations"],
            "seniority": "senior",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 175000,
                "target": 195000,
                "maximum": 215000,
                "period": "annual",
                "note": "Aligned with OrbitPay's current range.",
            },
            "locations": ["New York", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "30 days",
            "preferences": {
                "desired_titles": ["Payments Platform Lead", "Senior Payments Engineer"],
                "preferred_domains": ["fintech", "payments"],
                "preferred_locations": ["New York", "Remote US"],
                "remote_preference": "remote-first",
                "excluded_companies": [],
                "notes": "Needs heavy role shaping before client interviews.",
            },
            "risk_flags": ["needs heavy role shaping"],
            "evidence": [
                {
                    "evidence_id": "ev_sam_profile",
                    "source_type": "profile",
                    "source_id": "cand_sam_taylor",
                    "summary": (
                        "Sam has strong payments stack coverage but needs a "
                        "carefully shaped mandate before client interviews."
                    ),
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "candidate_id": "cand_riley_morgan",
            "name": "Riley Morgan",
            "headline": "Payments platform engineer with a fragile close plan",
            "current_company": "CardBridge",
            "current_title": "Senior Payments Engineer",
            "skills": ["Payments", "Kafka", "Risk", "Java", "Kotlin"],
            "domains": ["fintech", "payments", "risk operations"],
            "seniority": "senior",
            "compensation_expectation": {
                "currency": "USD",
                "minimum": 175000,
                "target": 190000,
                "maximum": 215000,
                "period": "annual",
                "note": "Aligned if the close plan is handled carefully.",
            },
            "locations": ["New York", "Remote US"],
            "work_authorization": "US authorized",
            "availability": "30 days",
            "preferences": {
                "desired_titles": ["Payments Platform Lead", "Senior Payments Engineer"],
                "preferred_domains": ["fintech", "payments"],
                "preferred_locations": ["New York", "Remote US"],
                "remote_preference": "remote-first",
                "excluded_companies": [],
                "notes": "Interested, but expects the recruiter to manage a counteroffer risk.",
            },
            "risk_flags": ["counteroffer likely after final interview"],
            "evidence": [
                {
                    "evidence_id": "ev_riley_profile",
                    "source_type": "profile",
                    "source_id": "cand_riley_morgan",
                    "summary": (
                        "Strong payments platform profile, but current employer "
                        "is expected to counter aggressively."
                    ),
                    "confidence": "candidate_stated",
                }
            ],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
    ]
    positions = [
        {
            "position_id": "pos_northstar_backend_lead",
            "client_company_id": "client_northstar_health",
            "title": "Senior Backend Platform Engineer",
            "status": "open",
            "seniority": "staff",
            "must_have": ["Python", "data platforms", "healthcare"],
            "nice_to_have": ["Kafka", "HIPAA", "workflow automation"],
            "target_compensation": {
                "currency": "USD",
                "minimum": 180000,
                "target": 205000,
                "maximum": 230000,
                "period": "annual",
                "note": "",
            },
            "locations": ["Boston", "Remote US"],
            "remote_policy": "remote-friendly",
            "ideal_candidate_examples": ["cand_avery_chen"],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "position_id": "pos_orbitpay_payments_lead",
            "client_company_id": "client_orbitpay",
            "title": "Payments Platform Lead",
            "status": "open",
            "seniority": "senior",
            "must_have": ["payments", "Kafka", "risk"],
            "nice_to_have": ["Java", "Kotlin", "compliance"],
            "target_compensation": {
                "currency": "USD",
                "minimum": 170000,
                "target": 195000,
                "maximum": 220000,
                "period": "annual",
                "note": "",
            },
            "locations": ["New York", "Remote US"],
            "remote_policy": "remote-first",
            "ideal_candidate_examples": ["cand_mateo_rivera"],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
        {
            "position_id": "pos_northstar_data_manager",
            "client_company_id": "client_northstar_health",
            "title": "Head of Data Engineering",
            "status": "paused",
            "seniority": "manager",
            "must_have": ["data platform", "team leadership", "Python"],
            "nice_to_have": ["healthcare", "Airflow", "Spark"],
            "target_compensation": {
                "currency": "USD",
                "minimum": 210000,
                "target": 235000,
                "maximum": 265000,
                "period": "annual",
                "note": "Paused while scope is being clarified.",
            },
            "locations": ["Remote US"],
            "remote_policy": "remote",
            "ideal_candidate_examples": ["cand_lin_park"],
            "created_at": loaded_at,
            "updated_at": loaded_at,
        },
    ]
    submissions = [
        {
            "submission_id": "sub_avery_northstar_backend",
            "candidate_id": "cand_avery_chen",
            "position_id": "pos_northstar_backend_lead",
            "status": "placed",
            "submitted_at": "2026-06-05T15:00:00+00:00",
            "client_feedback_ids": ["fb_avery_northstar_advance"],
            "next_step": "Finalize references and start date.",
        },
        {
            "submission_id": "sub_mateo_orbitpay_lead",
            "candidate_id": "cand_mateo_rivera",
            "position_id": "pos_orbitpay_payments_lead",
            "status": "interviewing",
            "submitted_at": "2026-06-11T14:00:00+00:00",
            "client_feedback_ids": ["fb_mateo_orbitpay_advance"],
            "next_step": "Schedule system-design interview.",
        },
        {
            "submission_id": "sub_priya_northstar_backend",
            "candidate_id": "cand_priya_shah",
            "position_id": "pos_northstar_backend_lead",
            "status": "rejected",
            "submitted_at": "2026-06-12T17:00:00+00:00",
            "client_feedback_ids": ["fb_priya_northstar_reject"],
            "next_step": "Keep warm for analytics mandates.",
        },
        {
            "submission_id": "sub_lin_northstar_data",
            "candidate_id": "cand_lin_park",
            "position_id": "pos_northstar_data_manager",
            "status": "submitted",
            "submitted_at": "2026-06-18T16:00:00+00:00",
            "client_feedback_ids": [],
            "next_step": "Wait for role scope confirmation.",
        },
    ]
    feedback = [
        {
            "feedback_id": "fb_avery_northstar_advance",
            "subject_type": "submission",
            "subject_id": "sub_avery_northstar_backend",
            "position_id": "pos_northstar_backend_lead",
            "candidate_id": "cand_avery_chen",
            "sentiment": "positive",
            "decision_signal": "advance",
            "rubric_deltas": {"domain_fit": 1, "client_preference_fit": 1},
            "preference_learning": [
                "Northstar strongly values healthcare workflow evidence.",
            ],
            "summary": "Hiring manager liked the healthcare data platform depth.",
            "created_at": "2026-06-13T13:00:00+00:00",
        },
        {
            "feedback_id": "fb_mateo_orbitpay_advance",
            "subject_type": "submission",
            "subject_id": "sub_mateo_orbitpay_lead",
            "position_id": "pos_orbitpay_payments_lead",
            "candidate_id": "cand_mateo_rivera",
            "sentiment": "positive",
            "decision_signal": "advance",
            "rubric_deltas": {"domain_fit": 1, "risk": -1},
            "preference_learning": [
                "OrbitPay responds well to risk operations examples.",
            ],
            "summary": "Client advanced Mateo for payments and risk depth.",
            "created_at": "2026-06-17T13:00:00+00:00",
        },
        {
            "feedback_id": "fb_priya_northstar_reject",
            "subject_type": "submission",
            "subject_id": "sub_priya_northstar_backend",
            "position_id": "pos_northstar_backend_lead",
            "candidate_id": "cand_priya_shah",
            "sentiment": "mixed",
            "decision_signal": "reject",
            "rubric_deltas": {"skill_fit": -2, "domain_fit": -1},
            "preference_learning": [
                "Northstar rejected analytics-first profiles for backend platform roles.",
            ],
            "summary": "Strong analytics profile, but not enough backend platform depth.",
            "created_at": "2026-06-18T12:30:00+00:00",
        },
        {
            "feedback_id": "fb_orbitpay_role_shaping_preference",
            "subject_type": "client_company",
            "subject_id": "client_orbitpay",
            "position_id": "pos_orbitpay_payments_lead",
            "sentiment": "neutral",
            "decision_signal": "preference_update",
            "rubric_deltas": {},
            "preference_learning": [
                "Rejects candidates who need heavy role-shaping before interviews.",
            ],
            "summary": (
                "OrbitPay wants candidates who can enter the process without "
                "heavy role shaping."
            ),
            "created_at": "2026-06-18T16:45:00+00:00",
        },
    ]
    interactions = [
        {
            "interaction_id": "int_avery_screen",
            "subject_type": "candidate",
            "subject_id": "cand_avery_chen",
            "interaction_type": "candidate_screen",
            "direction": "inbound",
            "source_confidence": "candidate_stated",
            "participants": ["Avery Chen", "Recruiter"],
            "occurred_at": "2026-06-04T18:00:00+00:00",
            "summary": "Avery wants staff-level backend platform work in healthcare.",
            "raw_content": "",
            "evidence_refs": [],
        },
        {
            "interaction_id": "int_northstar_intake",
            "subject_type": "position",
            "subject_id": "pos_northstar_backend_lead",
            "interaction_type": "client_intake",
            "direction": "inbound",
            "source_confidence": "client_stated",
            "participants": ["Northstar VP Engineering", "Recruiter"],
            "occurred_at": "2026-06-03T15:00:00+00:00",
            "summary": "Client needs healthcare data platform depth and practical delivery.",
            "raw_content": "",
            "evidence_refs": [],
        },
        {
            "interaction_id": "int_mateo_screen",
            "subject_type": "candidate",
            "subject_id": "cand_mateo_rivera",
            "interaction_type": "candidate_screen",
            "direction": "inbound",
            "source_confidence": "candidate_stated",
            "participants": ["Mateo Rivera", "Recruiter"],
            "occurred_at": "2026-06-10T19:00:00+00:00",
            "summary": "Mateo is strongest in payments, Kafka, and risk workflows.",
            "raw_content": "",
            "evidence_refs": [],
        },
        {
            "interaction_id": "int_nora_screen",
            "subject_type": "candidate",
            "subject_id": "cand_nora_weiss",
            "interaction_type": "candidate_screen",
            "direction": "inbound",
            "source_confidence": "candidate_stated",
            "participants": ["Nora Weiss", "Recruiter"],
            "occurred_at": "2026-06-19T17:00:00+00:00",
            "summary": (
                "Nora has deep healthcare platform experience but needs premium "
                "compensation, UK remote approval, and a later start date."
            ),
            "raw_content": "",
            "evidence_refs": [],
        },
        {
            "interaction_id": "int_jordan_screen",
            "subject_type": "candidate",
            "subject_id": "cand_jordan_lee",
            "interaction_type": "candidate_screen",
            "direction": "inbound",
            "source_confidence": "candidate_stated",
            "participants": ["Jordan Lee", "Recruiter"],
            "occurred_at": "2026-06-19T18:00:00+00:00",
            "summary": (
                "Jordan is strong in healthcare workflow systems but still needs "
                "production Python and data platform evidence confirmed."
            ),
            "raw_content": "",
            "evidence_refs": [],
        },
        {
            "interaction_id": "int_iris_screen",
            "subject_type": "candidate",
            "subject_id": "cand_iris_kim",
            "interaction_type": "candidate_screen",
            "direction": "inbound",
            "source_confidence": "candidate_stated",
            "participants": ["Iris Kim", "Recruiter"],
            "occurred_at": "2026-06-20T17:30:00+00:00",
            "summary": (
                "Iris matches OrbitPay's payments stack but is early-career "
                "for a platform lead mandate."
            ),
            "raw_content": "",
            "evidence_refs": [],
        },
        {
            "interaction_id": "int_sam_screen",
            "subject_type": "candidate",
            "subject_id": "cand_sam_taylor",
            "interaction_type": "candidate_screen",
            "direction": "inbound",
            "source_confidence": "candidate_stated",
            "participants": ["Sam Taylor", "Recruiter"],
            "occurred_at": "2026-06-21T17:00:00+00:00",
            "summary": (
                "Sam matches OrbitPay's stack but needs heavy role shaping "
                "before client interviews."
            ),
            "raw_content": "",
            "evidence_refs": [],
        },
    ]
    return {
        CANDIDATES: candidates,
        CLIENT_COMPANIES: clients,
        POSITIONS: positions,
        SUBMISSIONS: submissions,
        FEEDBACK: feedback,
        INTERACTIONS: interactions,
    }

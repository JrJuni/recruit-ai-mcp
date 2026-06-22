from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from deal_intel.storage.local_personal import LocalPersonalStore
from deal_intel.storage.local_sample_fixture import (
    ZERO_CONFIG_SAMPLE_DATASET,
    ZERO_CONFIG_SAMPLE_VERSION,
    build_zero_config_sample_summary,
    load_zero_config_sample_deals,
    load_zero_config_sample_snapshots,
    validate_zero_config_sample_fixture,
)
from deal_intel.storage.recruiting_collections import (
    CANDIDATES,
    CLIENT_COMPANIES,
    FEEDBACK,
    INTERACTIONS,
    POSITIONS,
    RECOMMENDATION_RUNS,
    SUBMISSIONS,
)
from deal_intel.storage.recruiting_records import normalize_recruiting_record


class LocalSampleClient:
    """Read-only storage backend for MongoDB-free zero-config sample mode."""

    def __init__(
        self,
        *,
        database: str = "local_sample",
        local_data_dir: str | Path | None = None,
    ) -> None:
        self._database_name = database
        self._fixture_deals = load_zero_config_sample_deals()
        self._fixture_deal_ids = {
            str(deal.get("deal_id") or "")
            for deal in self._fixture_deals
        }
        self._snapshots = load_zero_config_sample_snapshots()
        self._personal_store = (
            LocalPersonalStore(local_data_dir) if local_data_dir is not None else None
        )
        self._local_deals = (
            self._personal_store.load_deals() if self._personal_store else []
        )
        self._local_recruiting = (
            self._personal_store.load_recruiting_records()
            if self._personal_store
            else {}
        )
        validation = validate_zero_config_sample_fixture(
            deals=self._fixture_deals,
            snapshots=self._snapshots,
        )
        if not validation["ok"]:
            raise RuntimeError(f"invalid zero-config sample fixture: {validation['errors']}")

    @property
    def database_name(self) -> str:
        return self._database_name

    def ping(self) -> dict:
        fixture_summary = build_zero_config_sample_summary(
            deals=self._fixture_deals,
            snapshots=self._snapshots,
        )
        local_personal_active = self._local_personal_active()
        summary = build_zero_config_sample_summary(
            deals=self._active_deals(),
            snapshots=self._active_snapshots(),
        )
        payload = {
            "status": "ok",
            "storage_backend": "local_sample",
            "database": self._database_name,
            "data_mode": "local_personal" if local_personal_active else "fixture",
            "sample_dataset": (
                "local_personal" if local_personal_active else ZERO_CONFIG_SAMPLE_DATASET
            ),
            "sample_dataset_version": (
                None if local_personal_active else ZERO_CONFIG_SAMPLE_VERSION
            ),
            "deal_count": summary["deal_count"],
            "snapshot_count": summary["snapshot_count"],
            "local_deal_count": len(self._local_deals),
            "local_recruiting_record_count": sum(
                len(rows) for rows in self._local_recruiting.values()
            ),
            "fixture_archived": local_personal_active,
            "fixture_archive": {
                "dataset": ZERO_CONFIG_SAMPLE_DATASET,
                "version": ZERO_CONFIG_SAMPLE_VERSION,
                "deal_count": fixture_summary["deal_count"],
                "snapshot_count": fixture_summary["snapshot_count"],
            },
        }
        if self._personal_store is not None:
            payload["local_data_dir"] = str(self._personal_store.data_dir)
            payload["local_deals_path"] = str(self._personal_store.deals_path)
        return payload

    def get_deal(self, deal_id: str) -> dict | None:
        for deal in self._active_deals(include_archived=True):
            if deal.get("deal_id") == deal_id:
                return deepcopy(deal)
        return None

    def list_deals(self, *, stage: str | None = None, limit: int = 50) -> list[dict]:
        deals = [
            deal
            for deal in self._active_deals()
            if stage is None or deal.get("deal_stage") == stage
        ]
        deals.sort(
            key=lambda deal: (
                str(deal.get("updated_at") or ""),
                str(deal.get("company") or ""),
            ),
            reverse=True,
        )
        if limit > 0:
            deals = deals[:limit]
        return _restricted_deals(deals)

    def list_deals_for_metrics(self) -> list[dict]:
        return _restricted_deals(self._active_deals())

    def list_deals_for_qualification_reextract(self, *, limit: int = 0) -> list[dict]:
        deals = _maintenance_deals(self._active_deals())
        if limit > 0:
            deals = deals[:limit]
        return deals

    def list_analytics_snapshots(
        self,
        *,
        start_date: str,
        end_date: str,
        stage: str | None = None,
        industry: str | None = None,
    ) -> list[dict]:
        snapshots = [
            snapshot
            for snapshot in self._active_snapshots()
            if start_date <= str(snapshot.get("as_of") or "") <= end_date
            and (stage is None or snapshot.get("deal_stage") == stage)
            and (industry is None or snapshot.get("industry") == industry)
        ]
        snapshots.sort(
            key=lambda snapshot: (
                str(snapshot.get("as_of") or ""),
                str(snapshot.get("occurred_at") or snapshot.get("created_at") or ""),
                str(snapshot.get("deal_id") or ""),
            )
        )
        return deepcopy(snapshots)

    def upsert_deal(self, deal: dict) -> None:
        self._raise_if_fixture_deal(deal.get("deal_id"))
        store = self._ensure_personal_store()
        store.upsert_deal(deal)
        self._local_deals = store.load_deals()

    def update_deal_qualification_snapshots(
        self,
        deal_id: str,
        *,
        meddpicc_latest: dict,
        qualification_latest: dict,
        updated_at: str,
    ) -> bool:
        self._raise_if_fixture_deal(deal_id)
        store = self._ensure_personal_store()
        updated = store.update_deal_fields(
            deal_id,
            {
                "meddpicc_latest": meddpicc_latest,
                "qualification_latest": qualification_latest,
                "updated_at": updated_at,
            },
        )
        self._local_deals = store.load_deals()
        return updated

    def update_deal_qualification_reextraction(
        self,
        deal_id: str,
        *,
        interactions: list[dict],
        meddpicc_latest: dict,
        qualification_latest: dict,
        updated_at: str,
    ) -> bool:
        self._raise_if_fixture_deal(deal_id)
        store = self._ensure_personal_store()
        updated = store.update_deal_interactions_and_snapshots(
            deal_id,
            interactions=interactions,
            meddpicc_latest=meddpicc_latest,
            qualification_latest=qualification_latest,
            updated_at=updated_at,
        )
        self._local_deals = store.load_deals()
        return updated

    def insert_delete_audit_log(self, entry: dict) -> None:
        store = self._ensure_personal_store()
        store.insert_delete_audit_log(entry)

    def hard_delete_deal(self, deal_id: str) -> int:
        self._raise_if_fixture_deal(deal_id)
        store = self._ensure_personal_store()
        deleted_count = store.hard_delete_deal(deal_id)
        self._local_deals = store.load_deals()
        return deleted_count

    def local_personal_summary(self) -> dict:
        return self._ensure_personal_store().summary()

    def export_local_personal_data(self, *, output_path: str | Path | None = None) -> dict:
        return self._ensure_personal_store().export_data(output_path=output_path)

    def reset_local_personal_deals(self, *, force: bool = False) -> dict:
        store = self._ensure_personal_store()
        result = store.reset_deals(force=force)
        self._local_deals = store.load_deals()
        self._local_recruiting = store.load_recruiting_records()
        return result

    # --- local personal recruiting collections ---

    def upsert_recruiting_record(self, collection: str, record: object) -> bool:
        normalized = normalize_recruiting_record(collection, record)
        store = self._ensure_personal_store()
        result = store.upsert_recruiting_record(collection, normalized)
        self._local_recruiting = store.load_recruiting_records()
        return result

    def upsert_recruiting_records(self, records_by_collection: dict[str, list[dict]]) -> int:
        store = self._ensure_personal_store()
        count = store.upsert_recruiting_records(records_by_collection)
        self._local_recruiting = store.load_recruiting_records()
        return count

    def count_recruiting_records_by_ids(self, ids_by_collection: dict[str, list[str]]) -> int:
        return self._ensure_personal_store().count_recruiting_records_by_ids(
            ids_by_collection
        )

    def delete_recruiting_record(self, collection: str, record_id: str) -> bool:
        store = self._ensure_personal_store()
        deleted = store.delete_recruiting_record(collection, record_id)
        self._local_recruiting = store.load_recruiting_records()
        return deleted

    def delete_recruiting_records_by_ids(self, ids_by_collection: dict[str, list[str]]) -> int:
        store = self._ensure_personal_store()
        deleted = store.delete_recruiting_records_by_ids(ids_by_collection)
        self._local_recruiting = store.load_recruiting_records()
        return deleted

    def get_recruiting_record(
        self,
        collection: str,
        record_id: str,
        *,
        include_raw: bool = False,
    ) -> dict | None:
        del include_raw
        return self._ensure_personal_store().get_recruiting_record(collection, record_id)

    def list_recruiting_records(
        self,
        collection: str,
        *,
        query: dict | None = None,
        limit: int = 50,
        include_raw: bool = False,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        del include_raw, sort
        return self._ensure_personal_store().list_recruiting_records(
            collection,
            query=query,
            limit=limit,
        )

    def upsert_candidate(self, candidate: object) -> bool:
        return self.upsert_recruiting_record(CANDIDATES, candidate)

    def get_candidate(self, candidate_id: str, *, include_raw: bool = False) -> dict | None:
        return self.get_recruiting_record(
            CANDIDATES,
            candidate_id,
            include_raw=include_raw,
        )

    def list_candidates(self, *, query: dict | None = None, limit: int = 50) -> list[dict]:
        return self.list_recruiting_records(CANDIDATES, query=query, limit=limit)

    def upsert_client_company(self, client_company: object) -> bool:
        return self.upsert_recruiting_record(CLIENT_COMPANIES, client_company)

    def get_client_company(
        self,
        client_company_id: str,
        *,
        include_raw: bool = False,
    ) -> dict | None:
        return self.get_recruiting_record(
            CLIENT_COMPANIES,
            client_company_id,
            include_raw=include_raw,
        )

    def list_client_companies(
        self,
        *,
        query: dict | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self.list_recruiting_records(CLIENT_COMPANIES, query=query, limit=limit)

    def upsert_position(self, position: object) -> bool:
        return self.upsert_recruiting_record(POSITIONS, position)

    def get_position(self, position_id: str, *, include_raw: bool = False) -> dict | None:
        return self.get_recruiting_record(
            POSITIONS,
            position_id,
            include_raw=include_raw,
        )

    def list_positions(
        self,
        *,
        client_company_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self.list_recruiting_records(
            POSITIONS,
            query=_without_none(
                {
                    "client_company_id": client_company_id,
                    "status": status,
                }
            ),
            limit=limit,
        )

    def upsert_submission(self, submission: object) -> bool:
        return self.upsert_recruiting_record(SUBMISSIONS, submission)

    def get_submission(self, submission_id: str, *, include_raw: bool = False) -> dict | None:
        return self.get_recruiting_record(
            SUBMISSIONS,
            submission_id,
            include_raw=include_raw,
        )

    def list_submissions(
        self,
        *,
        candidate_id: str | None = None,
        position_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self.list_recruiting_records(
            SUBMISSIONS,
            query=_without_none(
                {
                    "candidate_id": candidate_id,
                    "position_id": position_id,
                    "status": status,
                }
            ),
            limit=limit,
        )

    def add_client_feedback(self, feedback: object) -> bool:
        return self.upsert_recruiting_record(FEEDBACK, feedback)

    def get_feedback(self, feedback_id: str, *, include_raw: bool = False) -> dict | None:
        return self.get_recruiting_record(
            FEEDBACK,
            feedback_id,
            include_raw=include_raw,
        )

    def list_feedback(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        position_id: str | None = None,
        candidate_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self.list_recruiting_records(
            FEEDBACK,
            query=_without_none(
                {
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "position_id": position_id,
                    "candidate_id": candidate_id,
                }
            ),
            limit=limit,
        )

    def append_recruiting_interaction(self, interaction: object) -> bool:
        return self.upsert_recruiting_record(INTERACTIONS, interaction)

    def get_recruiting_interaction(
        self,
        interaction_id: str,
        *,
        include_raw: bool = False,
    ) -> dict | None:
        return self.get_recruiting_record(
            INTERACTIONS,
            interaction_id,
            include_raw=include_raw,
        )

    def list_recruiting_interactions(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 50,
        include_raw: bool = False,
    ) -> list[dict]:
        return self.list_recruiting_records(
            INTERACTIONS,
            query=_without_none(
                {
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                }
            ),
            limit=limit,
            include_raw=include_raw,
        )

    def save_recommendation_run(self, recommendation_run: object) -> bool:
        return self.upsert_recruiting_record(RECOMMENDATION_RUNS, recommendation_run)

    def get_recommendation_run(
        self,
        recommendation_run_id: str,
        *,
        include_raw: bool = False,
    ) -> dict | None:
        return self.get_recruiting_record(
            RECOMMENDATION_RUNS,
            recommendation_run_id,
            include_raw=include_raw,
        )

    def list_recommendation_runs(
        self,
        *,
        anchor_type: str | None = None,
        anchor_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self.list_recruiting_records(
            RECOMMENDATION_RUNS,
            query=_without_none(
                {
                    "anchor_type": anchor_type,
                    "anchor_id": anchor_id,
                }
            ),
            limit=limit,
        )

    def _active_deals(self, *, include_archived: bool = False) -> list[dict]:
        source = self._local_deals if self._local_personal_active() else self._fixture_deals
        if include_archived:
            return source
        return [deal for deal in source if deal.get("archived") is not True]

    def _active_snapshots(self) -> list[dict]:
        if self._local_personal_active():
            return []
        return self._snapshots

    def _ensure_personal_store(self) -> LocalPersonalStore:
        if self._personal_store is None:
            self._personal_store = LocalPersonalStore()
        return self._personal_store

    def _local_personal_active(self) -> bool:
        return (
            self._personal_store is not None
            and self._personal_store.deals_path.exists()
        )

    def _raise_if_fixture_deal(self, deal_id: object) -> None:
        if str(deal_id or "") in self._fixture_deal_ids:
            raise ValueError("bundled fixture deals are read-only in local_sample")


def _restricted_deals(deals: list[dict]) -> list[dict]:
    restricted = deepcopy(deals)
    for deal in restricted:
        if not isinstance(deal, dict):
            continue
        deal.pop("contacts", None)
        deal.pop("summary_embedding", None)
        meetings = deal.get("meetings")
        if isinstance(meetings, list):
            for meeting in meetings:
                if isinstance(meeting, dict):
                    meeting.pop("raw_notes", None)
        interactions = deal.get("interactions")
        if isinstance(interactions, list):
            for interaction in interactions:
                if isinstance(interaction, dict):
                    interaction.pop("raw_content", None)
    return restricted


def _without_none(query: dict) -> dict:
    return {key: value for key, value in query.items() if value is not None}


def _maintenance_deals(deals: list[dict]) -> list[dict]:
    maintained = deepcopy(deals)
    for deal in maintained:
        if not isinstance(deal, dict):
            continue
        deal.pop("contacts", None)
        deal.pop("summary_embedding", None)
        meetings = deal.get("meetings")
        if isinstance(meetings, list):
            for meeting in meetings:
                if isinstance(meeting, dict):
                    meeting.pop("raw_notes", None)
    return maintained

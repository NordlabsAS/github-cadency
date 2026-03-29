"""Developer relationship management: CRUD and org tree building."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, DeveloperRelationship
from app.schemas.schemas import (
    DeveloperRelationshipResponse,
    DeveloperRelationshipsResponse,
    OrgTreeNode,
    OrgTreeResponse,
)


def _rel_to_response(rel: DeveloperRelationship) -> DeveloperRelationshipResponse:
    return DeveloperRelationshipResponse(
        id=rel.id,
        source_id=rel.source_id,
        target_id=rel.target_id,
        relationship_type=rel.relationship_type,
        source_name=rel.source.display_name,
        target_name=rel.target.display_name,
        source_avatar_url=rel.source.avatar_url,
        target_avatar_url=rel.target.avatar_url,
        created_at=rel.created_at,
    )


async def get_developer_relationships(
    db: AsyncSession, developer_id: int
) -> DeveloperRelationshipsResponse:
    """Get all relationships for a developer."""
    # Relationships where this dev is the source (they report to / are led by)
    src_result = await db.execute(
        select(DeveloperRelationship)
        .where(DeveloperRelationship.source_id == developer_id)
    )
    src_rels = src_result.scalars().all()

    # Relationships where this dev is the target (others report to / are led by them)
    tgt_result = await db.execute(
        select(DeveloperRelationship)
        .where(DeveloperRelationship.target_id == developer_id)
    )
    tgt_rels = tgt_result.scalars().all()

    # Eager-load the related developers
    for rel in [*src_rels, *tgt_rels]:
        if not rel.source:
            await db.refresh(rel, ["source"])
        if not rel.target:
            await db.refresh(rel, ["target"])

    reports_to = None
    tech_lead = None
    team_lead = None
    for rel in src_rels:
        resp = _rel_to_response(rel)
        if rel.relationship_type == "reports_to":
            reports_to = resp
        elif rel.relationship_type == "tech_lead_of":
            tech_lead = resp
        elif rel.relationship_type == "team_lead_of":
            team_lead = resp

    direct_reports = []
    tech_leads_for = []
    team_leads_for = []
    for rel in tgt_rels:
        resp = _rel_to_response(rel)
        if rel.relationship_type == "reports_to":
            direct_reports.append(resp)
        elif rel.relationship_type == "tech_lead_of":
            tech_leads_for.append(resp)
        elif rel.relationship_type == "team_lead_of":
            team_leads_for.append(resp)

    return DeveloperRelationshipsResponse(
        reports_to=reports_to,
        tech_lead=tech_lead,
        team_lead=team_lead,
        direct_reports=direct_reports,
        tech_leads_for=tech_leads_for,
        team_leads_for=team_leads_for,
    )


async def set_relationship(
    db: AsyncSession,
    source_id: int,
    target_id: int,
    relationship_type: str,
    created_by: str | None = None,
) -> DeveloperRelationship:
    """Create or update a relationship."""
    result = await db.execute(
        select(DeveloperRelationship).where(
            DeveloperRelationship.source_id == source_id,
            DeveloperRelationship.target_id == target_id,
            DeveloperRelationship.relationship_type == relationship_type,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.created_by = created_by
        return existing

    rel = DeveloperRelationship(
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type,
        created_by=created_by,
    )
    db.add(rel)
    await db.flush()
    await db.refresh(rel, ["source", "target"])
    return rel


async def remove_relationship(
    db: AsyncSession,
    source_id: int,
    target_id: int,
    relationship_type: str,
) -> bool:
    """Remove a relationship. Returns True if it existed."""
    result = await db.execute(
        select(DeveloperRelationship).where(
            DeveloperRelationship.source_id == source_id,
            DeveloperRelationship.target_id == target_id,
            DeveloperRelationship.relationship_type == relationship_type,
        )
    )
    rel = result.scalar_one_or_none()
    if rel:
        await db.delete(rel)
        return True
    return False


async def get_org_tree(
    db: AsyncSession, team: str | None = None
) -> OrgTreeResponse:
    """Build the org hierarchy from reports_to relationships."""
    # Load all active developers
    query = select(Developer).where(Developer.is_active.is_(True))
    if team:
        query = query.where(Developer.team == team)
    result = await db.execute(query)
    devs = {d.id: d for d in result.scalars().all()}

    # Load all reports_to relationships
    rel_result = await db.execute(
        select(DeveloperRelationship).where(
            DeveloperRelationship.relationship_type == "reports_to"
        )
    )
    rels = rel_result.scalars().all()

    # Build parent->children mapping
    children_map: dict[int, list[int]] = {}
    has_parent: set[int] = set()
    for rel in rels:
        if rel.source_id in devs and rel.target_id in devs:
            children_map.setdefault(rel.target_id, []).append(rel.source_id)
            has_parent.add(rel.source_id)

    def _build_node(dev_id: int) -> OrgTreeNode:
        dev = devs[dev_id]
        child_ids = children_map.get(dev_id, [])
        children = sorted(
            [_build_node(cid) for cid in child_ids],
            key=lambda n: n.display_name,
        )
        return OrgTreeNode(
            developer_id=dev.id,
            display_name=dev.display_name,
            github_username=dev.github_username,
            avatar_url=dev.avatar_url,
            role=dev.role,
            team=dev.team,
            office=dev.office,
            children=children,
        )

    # Roots = devs that are targets (managers) but not sources (don't report to anyone)
    # OR devs that have children but no parent
    root_ids = set()
    for dev_id in devs:
        if dev_id not in has_parent and dev_id in children_map:
            root_ids.add(dev_id)

    roots = sorted(
        [_build_node(rid) for rid in root_ids],
        key=lambda n: n.display_name,
    )

    # Unassigned = not in any hierarchy (no parent and no children)
    assigned = has_parent | root_ids
    # Also include all descendants
    def _collect_ids(node: OrgTreeNode, ids: set[int]) -> None:
        ids.add(node.developer_id)
        for child in node.children:
            _collect_ids(child, ids)

    all_in_tree: set[int] = set()
    for root in roots:
        _collect_ids(root, all_in_tree)

    unassigned_devs = [
        devs[did] for did in sorted(devs.keys()) if did not in all_in_tree
    ]
    unassigned = [
        OrgTreeNode(
            developer_id=d.id,
            display_name=d.display_name,
            github_username=d.github_username,
            avatar_url=d.avatar_url,
            role=d.role,
            team=d.team,
            office=d.office,
        )
        for d in sorted(unassigned_devs, key=lambda d: d.display_name)
    ]

    return OrgTreeResponse(roots=roots, unassigned=unassigned)

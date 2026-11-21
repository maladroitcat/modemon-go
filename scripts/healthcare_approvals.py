"""Exact owner approvals for outdoor associations at existing Healthcare POIs.

Keep analytical data and the base-world seed intact. These are owner decisions,
not claims of a field survey, verified building access or mapped sidewalk points.
"""
import copy
import hashlib
from datetime import date

import yaml

CONFIG = 'mobile/web/config/healthcare_approvals.yaml'
OVERRIDABLE = {
    'public_approach_not_established', 'unclassified_or_habitat_review',
    'sensitive_or_age_restricted_facility', 'human_curation_exclusion',
    'human_curation_rejected',
}


def apply_healthcare_approvals(root, anchors):
    source = (root / CONFIG).read_bytes()
    config = yaml.safe_load(source)
    if (config['scope'] != 'outdoor_public_association_only'
            or not config['version'] or not config['approval_source'].strip()
            or not config['approval_instruction'].strip() or not config['association_note'].strip()):
        raise ValueError('Missing explicit outdoor Healthcare approval')
    date.fromisoformat(config['approval_date'])
    result = copy.deepcopy(anchors)
    by_id = {p['id']: p for p in result}
    excluded = set(config['excluded_poi_ids'])
    approved = set()
    for entry in config['locations']:
        poi_id = entry['poi_id']
        if poi_id in approved or poi_id in excluded or poi_id not in by_id:
            raise ValueError(f'Duplicate, excluded or unknown Healthcare approval: {poi_id}')
        p = by_id[poi_id]
        reasons = set(entry['override_exclusions'])
        if (p['name'] != entry['name'] or p['primary'] != 'healthcare'
                or not reasons or not reasons <= OVERRIDABLE
                or reasons != set(p['exclusion_reasons']) or p['eligible']
                or p['special_destination'] or p['current_status'] in ('closed', 'unknown')):
            raise ValueError(f'Healthcare approval does not match source exclusions: {poi_id}')
        # An explicit decision can clear only the recorded reasons. New private,
        # closed, restricted or adult-only flags fail the build rather than being
        # silently cleared by a general Healthcare exception.
        p['public_approach_approval'] = dict(
            version=config['version'], effective_date=config['approval_date'],
            previous_exclusions=p['exclusion_reasons'],
            previous_association_note=p['association_note'], previous_access_status=p['access_status'])
        p['eligible'] = True
        p['exclusion_reasons'] = []
        p['access_status'] = 'owner_approved_outdoor_association'
        p['association_note'] = config['association_note']
        if entry.get('source_note'):
            p['association_note'] += ' ' + entry['source_note']
        approved.add(poi_id)
    if source != (root / CONFIG).read_bytes():
        raise ValueError('Healthcare approvals changed during build')
    return result, dict(version=config['version'], approval_date=config['approval_date'],
                        scope=config['scope'], approved_poi_ids=sorted(approved),
                        source_hashes={CONFIG: hashlib.sha256(source).hexdigest()})

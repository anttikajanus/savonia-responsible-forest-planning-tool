"""Credits for the configured analysis datasets, independent of QGIS and widgets.

Terms checked 2026-10-26; see docs/architecture/distribution.md
in the source repository. Original provider/dataset names stay intact in both
languages. Retrieved source identities and dates remain in run metadata.
"""

CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/"
FOREST_TERMS = "https://www.metsakeskus.fi/fi/avoin-metsa-ja-luontotieto/avoimen-metsa-ja-luontotiedon-tuotteet"
SYKE_DATASETS = "https://ckan.ymparisto.fi/dataset/"

_DATASETS = {
    "forest_centre_stand": (
        "Metsävarakuviot", "Suomen metsäkeskus", FOREST_TERMS,
    ),
    "forest_centre_habitat": (
        "Erityisen tärkeät elinympäristöt", "Suomen metsäkeskus", FOREST_TERMS,
    ),
    "forest_centre_gridcell": (
        "Metsävarahila", "Suomen metsäkeskus", FOREST_TERMS,
    ),
    "syke_protected_areas_state_owned": (
        "Luonnonsuojelu- ja erämaa-alueet: valtion maiden luonnonsuojelualueet",
        "Metsähallitus", SYKE_DATASETS + "luonnonsuojelu-ja-eramaa-alueet",
    ),
    "syke_protected_areas_private_land": (
        "Luonnonsuojelu- ja erämaa-alueet: yksityismaiden luonnonsuojelualueet",
        "Metsähallitus", SYKE_DATASETS + "luonnonsuojelu-ja-eramaa-alueet",
    ),
    "syke_protected_areas_wilderness": (
        "Luonnonsuojelu- ja erämaa-alueet: erämaa-alueet",
        "Metsähallitus", SYKE_DATASETS + "luonnonsuojelu-ja-eramaa-alueet",
    ),
    "syke_nature_conservation_programme_areas": (
        "Luonnonsuojeluohjelma-alueet", "Syke",
        SYKE_DATASETS + "luonnonsuojeluohjelma-alueet",
    ),
    "syke_groundwater_areas": (
        "Vesipuitedirektiivin mukaiset vesimuodostumat: VHS2022_Pohjavesi",
        "Syke, Lupa- ja valvontavirasto (rantaviiva-aineisto: MML)",
        SYKE_DATASETS + "vesipuitedirektiivin-mukaiset-vesimuodostumat",
    ),
}

def data_attribution(source_ids, changes_notice):
    """Return independent, serializable credits for the analysis sources used.

    Basemaps are not copied to analysis outputs. Keep their attribution in the
    map containing them. Unknown source IDs fail explicitly rather than receive
    an invented licence. The analysis currently validates these eight sources.
    """
    credits = {}
    for source_id in source_ids:
        dataset, provider, terms_url = _DATASETS[source_id]
        credits[source_id] = {
            "dataset": dataset,
            "attribution": "{0} / Lähde: {1}".format(dataset, provider),
            "license": "CC-BY-4.0",
            "license_url": CC_BY_URL,
            "terms_url": terms_url,
            "modifications": changes_notice,
        }
    return credits

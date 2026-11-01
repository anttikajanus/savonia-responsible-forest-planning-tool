# Open questions and tasks

Concrete changes to make and questions to resolve for this prototype. Remove an
item when it is resolved and update the affected documentation at that time.

## To do

- Fix the XSD parser so saved properties belong only to the selected feature
  type, rather than every XML element in the schema.
- Investigate the reported minute-long setup stall and identify whether the
  delay comes from source initialization or map rendering.
- Carry the source, licence, provider/dataset credit and delivery date of an
  externally supplied analysis boundary into shared outputs.
- Use the prescribed Ranta10 joint credit and direct dataset metadata link in
  portable output attribution.
- Add visible source credits to maps and screenshots, including MML dataset and
  delivery date and the OpenStreetMap contributor credit and licence route.
- Download the authenticated MML WMTS capabilities reference into the local
  cache when an API key is available.

## Questions to resolve

- Should a qualifying Section 10 habitat make the whole clipped stand sensitive,
  or only its mapped footprint? For example, should a 0.2 ha habitat make all of
  a 10 ha stand sensitive? Agree the spatial rule and how to explain
  `section10_stand_promoted` to planners.
- What does the Metsäkeskus growth measure represent: current or periodic growth,
  gross or net growth, and which volume/date supplies its denominator?
- What geographic coverage and observation/update dates do the stand, grid and
  Ranta10 products represent? How can an empty response be distinguished from
  an area outside the dataset's coverage?
- Which habitat codes, protected-area statuses/categories, programme classes and
  null formats do the live sources return, and what do they mean?
- What are the field meanings and identifier/null conventions for the configured
  `VHS2022_Pohjavesi` groundwater product?
- What schemas and identifier formats do the live MML parcel and identifier
  collections return?
- Which paging, query-size and geometry-filter limits apply to the configured
  services, especially multipart or malformed AOIs and water near the AOI edge?
- What practical analysis-area size can the current in-memory workflow handle?
- Which current Ranta10 metadata record corresponds to the older pointer
  advertised by the WFS service?
- What permission or statutory basis covers republication of the Savonia
  procurement PDFs and any independent works within them?
- Does the QGIS OSM tile client need application-specific identification or cache
  configuration to meet the tile-service policy?
- Should merges to `main` require the CI checks, and is the repository ruleset
  enabled if that is the intended policy?

"""Auditable English credential aliases, grouped by normalized level."""
from __future__ import annotations

from .models import EducationLevel

EDUCATION_ALIASES: dict[EducationLevel, list[str]] = {
    # High-school mentions are retained as evidence but normalize to UNKNOWN;
    # they are not a qualifying technology tier.
    EducationLevel.UNKNOWN: ["high school diploma", "high-school diploma", "high school degree", "secondary school diploma", "secondary education", "ged", "general educational development", "a-levels", "a levels", "higher secondary", "matriculation", "school leaving certificate"],
    EducationLevel.ASSOCIATE: ["associate degree", "associate's degree", "associates degree", "associate of science", "associate of arts", "a.s. degree", "a.a. degree", "hnd", "higher national diploma", "foundation degree", "two-year degree", "2-year degree", "bts", "dut", "deust", "vocational diploma", "professional diploma", "diplôme professionnel"],
    EducationLevel.BACHELOR: ["bachelor's degree", "bachelors degree", "bachelor's", "bachelors", "bachelor of science", "bachelor of arts", "bachelor of engineering", "bsc", "b.sc", "b.s", "bs", "ba", "b.a", "beng", "b.eng", "b.e", "undergraduate degree", "four-year degree", "4-year degree", "college degree"],
    EducationLevel.MASTER_OR_HIGHER: ["master's degree", "masters degree", "master's", "masters", "master of science", "master of arts", "master of engineering", "master of business administration", "msc", "m.sc", "m.s", "ms", "ma", "m.a", "meng", "m.eng", "mba", "m.b.a", "postgraduate degree", "post-graduate degree", "phd", "ph.d", "ph.d.", "doctorate", "doctoral degree", "doctor of philosophy", "scd", "sc.d", "doctorate in", "postdoctoral", "engineering degree", "engineering diploma", "diplôme d'ingénieur", "diplome d'ingenieur", "cycle ingénieur", "cycle ingenieur", "ingénieur d'état", "ingenieur d'etat", "formation ingénieur", "formation ingenieur", "école d'ingénieurs", "ecole d'ingenieurs", "école d'ingénieur", "engineering school", "formation supérieure", "formation superieure", "higher education degree", "higher education", "bac+5", "bac + 5", "bac +5", "bac+4/5"],
}

NON_DEGREE_CREDENTIALS: dict[str, list[str]] = {"non_degree": ["professional certification", "certification", "certificate", "diploma", "bootcamp", "boot camp", "coding bootcamp", "nanodegree", "professional license", "licensure", "accreditation"]}
NO_REQUIREMENT = [
    "no degree required",
    "no degree needed",
    "no-degree-required",
    "degree not required",
    "degree not necessary",
    "no college degree required",
    "no formal education required",
    "no formal education requirements",
    "no formal education requirement",
    "education not required",
    "without a degree",
    "without degree",
    "we don't care about degrees",
    "degree optional",
]
JURISDICTION_ALIASES: dict[str, dict[EducationLevel, list[str]]] = {
    "UK": {EducationLevel.ASSOCIATE: ["hnd"], EducationLevel.UNKNOWN: ["a-levels", "a levels"]},
    "IN": {EducationLevel.UNKNOWN: ["higher secondary"]},
    "DE": {EducationLevel.UNKNOWN: ["abitur"]},
}

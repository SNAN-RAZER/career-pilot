from app.matching.skill_ontology import SkillOntology
from app.models.skill import SkillRelation


def test_qdrant_is_vector_database():

    result = SkillOntology.match(
        "Qdrant",
        "Vector Databases",
    )

    assert result is not None

    assert (
        result.relation
        == SkillRelation.SPECIALIZATION
    )

    assert result.confidence >= 0.9


def test_vxworks_is_rtos():

    result = SkillOntology.match(
        "VxWorks",
        "RTOS",
    )

    assert result is not None

    assert (
        result.relation
        == SkillRelation.SPECIALIZATION
    )


def test_python_is_not_tensorflow():

    result = SkillOntology.match(
        "Python",
        "TensorFlow",
    )

    assert result is None


def test_qdrant_is_not_exact_match():

    result = SkillOntology.match(
        "Qdrant",
        "Vector Databases",
    )

    assert result.relation != SkillRelation.EXACT
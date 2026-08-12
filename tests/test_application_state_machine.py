import pytest

from app.models.application_status import (
    ApplicationStatus,
)
from app.services.application_state_machine import (
    ApplicationStateMachine,
    InvalidApplicationTransition,
)


def test_pending_can_become_applied():

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.PENDING,
        ApplicationStatus.APPLIED,
    )


def test_pending_can_become_rejected():

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.PENDING,
        ApplicationStatus.REJECTED,
    )


def test_applied_can_become_interview():

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.APPLIED,
        ApplicationStatus.INTERVIEW,
    )


def test_interview_can_become_offer():

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
    )


def test_applied_can_become_rejected():

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.APPLIED,
        ApplicationStatus.REJECTED,
    )


def test_interview_can_become_rejected():

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
    )


def test_offer_has_no_outgoing_transition():

    assert not ApplicationStateMachine.can_transition(
        ApplicationStatus.OFFER,
        ApplicationStatus.APPLIED,
    )

    assert not ApplicationStateMachine.can_transition(
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
    )


def test_rejected_has_no_outgoing_transition():

    assert not ApplicationStateMachine.can_transition(
        ApplicationStatus.REJECTED,
        ApplicationStatus.APPLIED,
    )


def test_invalid_transition_raises():

    with pytest.raises(
        InvalidApplicationTransition
    ):

        ApplicationStateMachine.transition(
            ApplicationStatus.REJECTED,
            ApplicationStatus.APPLIED,
        )


def test_valid_transition_returns_new_status():

    result = ApplicationStateMachine.transition(
        ApplicationStatus.PENDING,
        ApplicationStatus.APPLIED,
    )

    assert (
        result
        == ApplicationStatus.APPLIED
    )